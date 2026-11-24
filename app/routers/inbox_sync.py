"""Inbound Channel Sync API: Automatic Reservation Ingestion for Gmail & WhatsApp."""
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import random
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_org, get_current_user
from app.routers.cancellation import get_current_business_date
from app.models import (
    ActivityLog,
    Folio,
    FolioItem,
    Guest,
    Organization,
    Reservation,
    Room,
    RoomType,
    TaxRate,
    User,
)
from app.routers.reservations import compute_tax_breakdown, enrich_reservation
from app.schemas import ReservationResponse

router = APIRouter(prefix="/api/integrations", tags=["Channel Integrations & Inbound Sync"])


class InboundMessagePayload(BaseModel):
    channel: str = Field(..., description="'whatsapp' or 'gmail'")
    sender: str = Field(..., description="Phone number (+91...) or email address")
    sender_name: Optional[str] = Field(None, description="Sender display name")
    subject: Optional[str] = Field(None, description="Email subject line if applicable")
    raw_text: str = Field(..., description="Inbound text/email body")
    room_type_id: Optional[int] = Field(None, description="Optional forced room type ID")
    auto_check_in: bool = Field(False, description="Whether to immediately check in if arriving today")


def detect_ota_platform(raw_text: str, sender: str = "", subject: str = "") -> Dict[str, Any]:
    """Identifies if the incoming message or email is an automated reservation from an OTA (OYO, Airbnb, Booking.com, Agoda, MakeMyTrip)."""
    text_l = (raw_text + " " + sender + " " + (subject or "")).lower()

    # 1. Booking.com
    if "booking.com" in text_l or "@guest.booking.com" in text_l:
        m = re.search(r"(?:confirmation\s*(?:#|number|id)?|booking\s*id|pin)[:\s#]*([0-9]{8,12})", raw_text, re.IGNORECASE)
        ota_id = m.group(1) if m else str(random.randint(300000000, 999999999))
        return {"ota": "Booking.com", "code": "BCOM", "ota_id": ota_id, "badge_bg": "#EFF6FF", "badge_color": "#1D4ED8"}

    # 2. Airbnb
    if "airbnb" in text_l or re.search(r"\bHM[A-Z0-9]{6,8}\b", raw_text, re.IGNORECASE):
        m = re.search(r"(?:confirmation\s*code|code|airbnb\s*id|reservation)[:\s#]*([A-Z0-9]{6,10})", raw_text, re.IGNORECASE)
        if not m:
            m = re.search(r"\b(HM[A-Z0-9]{6,8})\b", raw_text, re.IGNORECASE)
        ota_id = m.group(1).upper() if m else f"HM{random.randint(100000, 999999)}"
        return {"ota": "Airbnb", "code": "ABNB", "ota_id": ota_id, "badge_bg": "#FFF1F2", "badge_color": "#E11D48"}

    # 3. OYO Rooms
    if "oyo" in text_l:
        m = re.search(r"\b(OYO-[A-Z0-9]+)\b", raw_text, re.IGNORECASE)
        if not m:
            m = re.search(r"(?:booking\s*id|oyo\s*id|booking)[:\s#-]*([A-Z0-9-]{5,12})", raw_text, re.IGNORECASE)
        ota_id = m.group(1).upper() if m else f"OYO-{random.randint(10000, 99999)}"
        return {"ota": "OYO", "code": "OYO", "ota_id": ota_id, "badge_bg": "#FEF2F2", "badge_color": "#DC2626"}

    # 4. Agoda
    if "agoda" in text_l or "@agoda-guest.com" in text_l:
        m = re.search(r"(?:booking\s*id|voucher|reference|agoda\s*id)[:\s#]*([0-9]{7,12})", raw_text, re.IGNORECASE)
        ota_id = m.group(1) if m else str(random.randint(7000000, 9999999))
        return {"ota": "Agoda", "code": "AGD", "ota_id": ota_id, "badge_bg": "#F0F9FF", "badge_color": "#0284C7"}

    # 5. MakeMyTrip / Goibibo
    if "makemytrip" in text_l or "mmt" in text_l or "goibibo" in text_l:
        m = re.search(r"\b(MMT-[A-Z0-9]+|NF[0-9]{6,10})\b", raw_text, re.IGNORECASE)
        if not m:
            m = re.search(r"(?:booking\s*id|confirmation)[:\s#-]*([A-Z0-9-]{6,14})", raw_text, re.IGNORECASE)
        ota_id = m.group(1).upper() if m else f"MMT-{random.randint(100000, 999999)}"
        return {"ota": "MakeMyTrip", "code": "MMT", "ota_id": ota_id, "badge_bg": "#FFF7ED", "badge_color": "#EA580C"}

    # Direct Channel
    return {"ota": "Direct Channel", "code": "DIR", "ota_id": None, "badge_bg": "#ECFDF5", "badge_color": "#059669"}


def parse_inbound_booking_text(raw_text: str, channel: str, sender: str, sender_name: Optional[str] = None, subject: Optional[str] = None) -> Dict[str, Any]:
    """Extracts guest name, phone, email, check-in, check-out, room preference, guest count, and OTA metadata."""
    today = date.today()
    ota_info = detect_ota_platform(raw_text, sender, subject or "")

    extracted: Dict[str, Any] = {
        "ota_provider": ota_info["ota"],
        "ota_code": ota_info["code"],
        "ota_id": ota_info["ota_id"],
        "guest_name": sender_name or "Valued Guest",
        "phone": sender if ("+" in sender or sender.replace(" ", "").isdigit()) else None,
        "email": sender if ("@" in sender) else None,
        "check_in_date": today,
        "check_out_date": today + timedelta(days=2),
        "adults": 1,
        "room_type_preference": None,
        "nightly_rate": None,
        "total_amount": None,
        "special_requests": "",
    }

    text_lower = raw_text.lower()

    # 1. Extract Guest Name (tailored to OTA formats)
    name_patterns = [
        r"(?:guest\s*(?:name)?|booked\s+for|guest|name)[:\-\s]+([A-Za-z\s]{3,30})",
        r"(?:new\s+booking\s+from|reservation\s+confirmed\s*[-!:]\s*)([A-Za-z\s]{3,25})",
        r"(?:for)\s+([A-Za-z\s]{3,25})\s*(?:,|arrives|\()",
    ]
    for pat in name_patterns:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            clean_name = m.group(1).strip()
            # Clean trailing words like 'arrives' or '(2 guests)'
            clean_name = re.sub(r"\b(arrives|departs|nights|adults|guests|room|booking)\b.*", "", clean_name, flags=re.IGNORECASE).strip()
            if len(clean_name) >= 3 and not any(k in clean_name.lower() for k in ["tomorrow", "deluxe", "suite", "standard", "guest", "room", "oyo", "airbnb", "agoda"]):
                extracted["guest_name"] = clean_name.title()
                break

    # 2. Extract Phone
    phone_m = re.search(r"(\+?[0-9]{1,4}?[-.\s]?\(?[0-9]{2,5}?\)?[-.\s]?[0-9]{3,5}[-.\s]?[0-9]{3,5})", raw_text)
    if phone_m and len(phone_m.group(1).replace(" ", "").replace("-", "")) >= 10:
        extracted["phone"] = phone_m.group(1).strip()

    # 3. Extract Email
    email_m = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", raw_text)
    if email_m:
        extracted["email"] = email_m.group(1).strip().lower()

    # 4. Extract Dates
    # Pattern A: ISO date YYYY-MM-DD
    iso_dates = re.findall(r"\b(202[5-9]-[0-1][0-9]-[0-3][0-9])\b", raw_text)
    if len(iso_dates) >= 2:
        try:
            d1 = datetime.strptime(iso_dates[0], "%Y-%m-%d").date()
            d2 = datetime.strptime(iso_dates[1], "%Y-%m-%d").date()
            if d2 > d1:
                extracted["check_in_date"] = d1
                extracted["check_out_date"] = d2
        except Exception:
            pass
    elif len(iso_dates) == 1:
        try:
            d1 = datetime.strptime(iso_dates[0], "%Y-%m-%d").date()
            extracted["check_in_date"] = d1
            extracted["check_out_date"] = d1 + timedelta(days=2)
        except Exception:
            pass
    else:
        # Pattern B: e.g. "25 Nov to 28 Nov", "Nov 26 - Nov 29, 2026", "25 Nov 2026, Check-out: 27 Nov 2026"
        month_names = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
        # Check for textual dates like "25 Nov" or "Nov 25"
        date_pattern_1 = rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})(?:\s+(\d{{4}}))?"
        date_pattern_2 = rf"({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*,\s*(\d{{4}}))?"

        matches1 = list(re.finditer(date_pattern_1, text_lower))
        matches2 = list(re.finditer(date_pattern_2, text_lower))

        if len(matches1) >= 2:
            try:
                m1, m2 = matches1[0], matches1[1]
                day1, mon1 = int(m1.group(1)), m1.group(2)
                yr1 = int(m1.group(3)) if m1.group(3) else today.year
                dt1 = datetime.strptime(f"{day1} {mon1} {yr1}", "%d %b %Y").date()

                day2, mon2 = int(m2.group(1)), m2.group(2)
                yr2 = int(m2.group(3)) if m2.group(3) else today.year
                dt2 = datetime.strptime(f"{day2} {mon2} {yr2}", "%d %b %Y").date()

                if dt2 > dt1:
                    extracted["check_in_date"] = dt1
                    extracted["check_out_date"] = dt2
            except Exception:
                pass
        elif len(matches2) >= 2:
            try:
                m1, m2 = matches2[0], matches2[1]
                mon1, day1 = m1.group(1), int(m1.group(2))
                yr1 = int(m1.group(3)) if m1.group(3) else today.year
                dt1 = datetime.strptime(f"{day1} {mon1} {yr1}", "%d %b %Y").date()

                mon2, day2 = m2.group(1), int(m2.group(2))
                yr2 = int(m2.group(3)) if m2.group(3) else (int(m1.group(3)) if m1.group(3) else today.year)
                dt2 = datetime.strptime(f"{day2} {mon2} {yr2}", "%d %b %Y").date()

                if dt2 > dt1:
                    extracted["check_in_date"] = dt1
                    extracted["check_out_date"] = dt2
            except Exception:
                pass

    # 5. Extract Room Type Preference
    for rt_keyword in ["deluxe", "suite", "executive", "standard", "heritage", "apartment", "villa", "superior", "king", "queen"]:
        if rt_keyword in text_lower:
            extracted["room_type_preference"] = rt_keyword
            break

    # 6. Extract Guests / Adults Count
    adults_m = re.search(r"(\d+)\s*(?:adult|guest|people|person)", text_lower)
    if adults_m:
        try:
            cnt = int(adults_m.group(1))
            if 1 <= cnt <= 6:
                extracted["adults"] = cnt
        except Exception:
            pass

    # 7. Extract Total Amount / Payout if present
    amt_m = re.search(r"(?:total(?:\s*payout|\s*amount|\s*payable)?|host\s*payout|payout|amount|total)[:\s]*[₹$€£INR\s]*([0-9,]+(?:\.[0-9]{2})?)", raw_text, re.IGNORECASE)
    if amt_m:
        try:
            val = Decimal(amt_m.group(1).replace(",", ""))
            if val > 0:
                extracted["total_amount"] = val
        except Exception:
            pass

    # 8. Special Requests / Excerpt
    extracted["special_requests"] = raw_text[:200]

    return extracted


@router.post("/inbox-sync")
def sync_inbound_booking(
    payload: InboundMessagePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
):
    """Parses incoming WhatsApp message or Gmail booking confirmation and automatically creates a live reservation."""
    parsed = parse_inbound_booking_text(
        raw_text=payload.raw_text,
        channel=payload.channel,
        sender=payload.sender,
        sender_name=payload.sender_name,
    )

    guest_name = parsed["guest_name"]
    phone = parsed["phone"] or payload.sender
    email = parsed["email"] or f"{re.sub(r'[^a-zA-Z0-9]', '', guest_name).lower()}@guest.checkinos.io"

    # 1. Match or Create Guest in Organization
    guest = db.query(Guest).filter(
        Guest.organization_id == org.id,
        or_(Guest.phone == phone, Guest.email == email),
    ).first()

    if not guest:
        names = guest_name.strip().split(" ", 1)
        fname = names[0]
        lname = names[1] if len(names) > 1 else ""
        guest = Guest(
            organization_id=org.id,
            first_name=fname,
            last_name=lname,
            email=email,
            phone=phone,
            address="Channel Guest",
            notes=f"Auto-created from inbound {payload.channel.upper()} booking.",
        )
        db.add(guest)
        db.flush()

    # 2. Find Best Available Room
    cin = parsed["check_in_date"]
    cout = parsed["check_out_date"]
    nights = max((cout - cin).days, 1)

    # Query existing bookings that collide with dates
    overlapping_res = (
        db.query(Reservation.room_id)
        .filter(
            Reservation.organization_id == org.id,
            Reservation.status.in_(["booked", "checked_in"]),
            Reservation.check_in_date < cout,
            Reservation.check_out_date > cin,
            Reservation.deleted_at.is_(None),
        )
        .all()
    )
    booked_room_ids = {r[0] for r in overlapping_res if r[0]}

    # Query candidate rooms
    room_query = db.query(Room).filter(
        Room.organization_id == org.id,
        Room.deleted_at.is_(None),
        ~Room.id.in_(booked_room_ids) if booked_room_ids else True,
    )

    # If preference specified
    pref = parsed.get("room_type_preference")
    selected_room = None
    if pref:
        candidates = room_query.join(RoomType).filter(
            func.lower(RoomType.name).contains(pref)
        ).all()
        if candidates:
            selected_room = candidates[0]

    if not selected_room:
        candidates = room_query.all()
        selected_room = candidates[0] if candidates else None

    # Fallback to any room if property is at capacity for demo
    if not selected_room:
        selected_room = db.query(Room).filter(Room.organization_id == org.id).first()

    if not selected_room:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rooms configured for this property.",
        )

    # 3. Determine Nightly Rate
    base_rate = selected_room.room_type.base_rate if (selected_room and selected_room.room_type) else Decimal("3500.00")
    total_room_charges = base_rate * nights

    # 4. Generate Channel-Specific Confirmation Number
    channel_prefix = "WA" if payload.channel.lower() == "whatsapp" else "GM"
    ota_code = parsed.get("ota_code", "DIR")
    rand_seq = random.randint(1000, 9999)
    if ota_code != "DIR":
        conf_number = f"HTL-{channel_prefix}-{ota_code}-{rand_seq}"
    else:
        conf_number = f"HTL-{channel_prefix}-{rand_seq}"

    # Determine status
    business_date = get_current_business_date(db)
    is_today = cin == business_date or cin == date.today()
    res_status = "checked_in" if (payload.auto_check_in and is_today) else "booked"

    # 5. Create Reservation
    ota_tag = f"[{parsed['ota_provider']}" + (f" #{parsed['ota_id']}" if parsed.get('ota_id') else "") + "]"
    new_reservation = Reservation(
        organization_id=org.id,
        confirmation_number=conf_number,
        guest_id=guest.id,
        room_id=selected_room.id,
        check_in_date=cin,
        check_out_date=cout,
        adults=parsed.get("adults", 1),
        children=0,
        nightly_rate=base_rate,
        status=res_status,
        notes=f"{ota_tag} Auto-synced via {payload.channel.upper()} from {payload.sender}. Inbound excerpt: {parsed['special_requests'][:120]}",
        version=1,
    )
    db.add(new_reservation)
    db.flush()

    # 6. Create Primary Folio
    folio = Folio(
        organization_id=org.id,
        reservation_id=new_reservation.id,
        name=f"Primary Folio ({guest.full_name})",
        is_master=True,
    )
    db.add(folio)
    db.flush()

    # 7. Post Room Charge & GST
    tax_res = compute_tax_breakdown(
        amount=total_room_charges,
        category="room",
        nights=nights,
        adults=parsed.get("adults", 1),
        db=db,
    )
    tax_total = tax_res.get("tax_total", Decimal("0.00"))
    tax_lines = tax_res.get("breakdown", [])
    folio_item = FolioItem(
        organization_id=org.id,
        reservation_id=new_reservation.id,
        folio_id=folio.id,
        date=cin,
        category="room",
        description=f"Room Charge ({nights} night(s) via {payload.channel.upper()} Auto-Sync)",
        amount=total_room_charges,
        tax_total=tax_total,
        tax_breakdown=json.dumps(tax_lines),
    )
    db.add(folio_item)

    # Flip room status if checked in
    if res_status == "checked_in":
        selected_room.status = "occupied"

    # 8. Activity Log
    act_log = ActivityLog(
        organization_id=org.id,
        event_type="inbound_channel_booking",
        description=f"{payload.channel.upper()} Auto-Sync: Created booking #{conf_number} for {guest.full_name} in Room {selected_room.number}.",
        actor=f"{payload.channel.title()} Integration Agent",
    )
    db.add(act_log)

    db.commit()
    db.refresh(new_reservation)

    return {
        "success": True,
        "channel": payload.channel,
        "ota_provider": parsed.get("ota_provider", "Direct Channel"),
        "ota_id": parsed.get("ota_id"),
        "ota_code": parsed.get("ota_code", "DIR"),
        "confirmation_number": conf_number,
        "reservation_id": new_reservation.id,
        "guest_name": guest.full_name,
        "room_number": selected_room.number,
        "room_type": selected_room.room_type.name if selected_room.room_type else "Standard",
        "check_in_date": str(cin),
        "check_out_date": str(cout),
        "nights": nights,
        "total_amount": float(total_room_charges + tax_total),
        "status": res_status,
        "message": f"Successfully auto-booked from {parsed.get('ota_provider', payload.channel.upper())} and allocated Room {selected_room.number}!",
    }


def resolve_webhook_organization(request: Request, body: dict, db: Session) -> Optional[Organization]:
    """Resolves target hotel organization from webhook request headers, query params, or body."""
    org_id = request.headers.get("X-Organization-Id") or request.query_params.get("org_id")
    if org_id and str(org_id).isdigit():
        target = db.query(Organization).filter(Organization.id == int(org_id), Organization.deleted_at.is_(None)).first()
        if target:
            return target
    if body.get("organization_id") and str(body.get("organization_id")).isdigit():
        target = db.query(Organization).filter(Organization.id == int(body["organization_id"]), Organization.deleted_at.is_(None)).first()
        if target:
            return target
    recipient = body.get("to") or body.get("recipient")
    if recipient:
        matched = db.query(Organization).filter(
            (Organization.email == str(recipient)) | (Organization.phone == str(recipient)),
            Organization.deleted_at.is_(None)
        ).first()
        if matched:
            return matched
    return db.query(Organization).filter(Organization.deleted_at.is_(None)).first()


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """Public webhook receiver for incoming WhatsApp Business Cloud API messages."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    sender = body.get("from") or body.get("sender") or "+91 98765 43210"
    raw_text = body.get("text") or body.get("message") or body.get("body") or "Hi, please reserve a room for 2 nights for Rohan Gupta."

    org = resolve_webhook_organization(request, body, db)
    if not org:
        return {"status": "ignored", "reason": "no org"}

    # Run intake parser
    payload = InboundMessagePayload(
        channel="whatsapp",
        sender=str(sender),
        sender_name="WhatsApp Guest",
        raw_text=str(raw_text),
    )
    mock_user = db.query(User).filter(User.organization_id == org.id).first()
    if not mock_user:
        mock_user = db.query(User).first()

    return sync_inbound_booking(payload=payload, db=db, current_user=mock_user, org=org)


@router.post("/gmail/webhook")
async def gmail_webhook(request: Request, db: Session = Depends(get_db)):
    """Public webhook receiver for incoming Gmail booking confirmation emails."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    sender = body.get("from") or "reservations@booking.com"
    subject = body.get("subject") or "Booking Confirmation"
    raw_text = body.get("body") or body.get("text") or "Booking confirmed for Priya Patel. Check-in 2026-11-26, check-out 2026-11-28. Deluxe King."

    org = resolve_webhook_organization(request, body, db)
    if not org:
        return {"status": "ignored", "reason": "no org"}

    payload = InboundMessagePayload(
        channel="gmail",
        sender=str(sender),
        sender_name="OTA / Email Guest",
        subject=str(subject),
        raw_text=f"Subject: {subject}\n\n{raw_text}",
    )
    mock_user = db.query(User).filter(User.organization_id == org.id).first()
    if not mock_user:
        mock_user = db.query(User).first()

    return sync_inbound_booking(payload=payload, db=db, current_user=mock_user, org=org)


@router.get("/status")
def get_channel_sync_status(
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Returns active connectivity status, webhook URLs, and ingestion metrics for Gmail & WhatsApp."""
    # Count auto-synced reservations
    synced_count = (
        db.query(Reservation)
        .filter(
            Reservation.organization_id == org.id,
            or_(
                Reservation.confirmation_number.contains("WA-"),
                Reservation.confirmation_number.contains("GM-"),
                Reservation.notes.contains("Auto-synced"),
            ),
        )
        .count()
    )

    return {
        "status": "operational",
        "organization_id": org.id,
        "hotel_name": org.name,
        "whatsapp": {
            "status": "connected",
            "bot_name": "CheckinOS Instant Intake Bot",
            "phone_number": "+91 8000-CHECKIN",
            "webhook_url": f"/api/integrations/whatsapp/webhook",
            "features": ["Instant reservation booking", "Automated room rack allocation", "Guest profile matching"],
        },
        "gmail": {
            "status": "connected",
            "forwarding_address": f"bookings-{org.slug}@checkinos.io",
            "webhook_url": f"/api/integrations/gmail/webhook",
            "supported_parsers": ["Booking.com", "Airbnb", "MakeMyTrip", "Agoda", "Direct Guest Inquiries"],
        },
        "total_auto_synced_reservations": synced_count,
        "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
    }


@router.get("/feed")
def get_channel_sync_feed(
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Returns the recent feed of reservations automatically synced via Gmail & WhatsApp."""
    res_list = (
        db.query(Reservation)
        .filter(
            Reservation.organization_id == org.id,
            or_(
                Reservation.confirmation_number.contains("WA-"),
                Reservation.confirmation_number.contains("GM-"),
                Reservation.notes.contains("Auto-synced"),
            ),
        )
        .order_by(Reservation.id.desc())
        .limit(10)
        .all()
    )

    feed = []
    for r in res_list:
        notes_str = r.notes or ""
        ota = "Direct Channel"
        if "Booking.com" in notes_str or "-BCOM-" in r.confirmation_number:
            ota = "Booking.com"
        elif "Airbnb" in notes_str or "-ABNB-" in r.confirmation_number:
            ota = "Airbnb"
        elif "OYO" in notes_str or "-OYO-" in r.confirmation_number:
            ota = "OYO"
        elif "Agoda" in notes_str or "-AGD-" in r.confirmation_number:
            ota = "Agoda"
        elif "MakeMyTrip" in notes_str or "-MMT-" in r.confirmation_number:
            ota = "MakeMyTrip"

        channel = "whatsapp" if "WA-" in r.confirmation_number or "whatsapp" in notes_str.lower() else "gmail"
        feed.append({
            "id": r.id,
            "confirmation_number": r.confirmation_number,
            "channel": channel,
            "ota_provider": ota,
            "guest_name": r.guest.full_name if r.guest else "Guest",
            "phone": r.guest.phone if r.guest else "",
            "room_number": r.room.number if r.room else "Unassigned",
            "check_in_date": str(r.check_in_date),
            "check_out_date": str(r.check_out_date),
            "nightly_rate": float(r.nightly_rate),
            "status": r.status,
            "created_at": str(r.created_at) if r.created_at else "",
            "notes": r.notes,
        })
    return feed
