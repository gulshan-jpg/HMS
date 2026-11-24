"""Reservations API Endpoints with Overlap Guard, Check-in, Checkout, Rate Plans, Deposits, and Move Workflows."""
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import random
import string
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import get_current_org, get_current_user, require_role
from app.models import (
    ActivityLog,
    BusinessDate,
    CancellationPolicy,
    Folio,
    FolioItem,
    Guest,
    HousekeepingTask,
    Organization,
    Payment,
    RateOverride,
    RatePlan,
    Reservation,
    Room,
    User,
)
from app.services.pdf import build_reservation_invoice_pdf, build_daily_run_sheet_pdf
from app.services.audit import log_audit
from app.schemas import (
    CancellationQuoteResponse,
    CheckOutRequest,
    DepositRecordRequest,
    DepositStatusResponse,
    PaginatedResponse,
    ReservationCreate,
    ReservationMoveRequest,
    ReservationResponse,
    ReservationUpdate,
    WalkInCheckInRequest,
)
from app.routers.cancellation import compute_cancellation_details, get_current_business_date
from app.routers.taxes import compute_tax_breakdown

router = APIRouter(prefix="/api/reservations", tags=["Reservations"])


def generate_confirmation_number() -> str:
    """Generate a unique professional PMS confirmation identifier."""
    digits = "".join(random.choices(string.digits, k=5))
    return f"HTL-{digits}"


def get_or_create_primary_folio(reservation_id: int, db: Session) -> Folio:
    """Retrieve or create the primary master folio for a reservation."""
    folio = (
        db.query(Folio)
        .filter(Folio.reservation_id == reservation_id, Folio.is_master.is_(True))
        .first()
    )
    if not folio:
        res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
        org_id = res.organization_id if res else 1
        folio = Folio(
            organization_id=org_id,
            reservation_id=reservation_id,
            name="Primary",
            is_master=True,
        )
        db.add(folio)
        db.flush()
    return folio


def ensure_room_charges_posted(r: Reservation, db: Session):
    """Ensure in-house or departing guests have their room stay charges posted to folio."""
    if r.status in ("checked_in", "checked_out") and r.nightly_rate and r.nightly_rate > 0:
        existing = (
            db.query(FolioItem)
            .filter(FolioItem.reservation_id == r.id, FolioItem.category == "room")
            .first()
        )
        if not existing:
            primary_folio = get_or_create_primary_folio(r.id, db)
            nights = max(r.nights, 1)
            room_subtotal = Decimal(str(r.nightly_rate)) * Decimal(str(nights))

            tax_res = compute_tax_breakdown(
                amount=room_subtotal,
                category="room",
                nights=nights,
                adults=r.adults,
                db=db,
            )

            folio_room = FolioItem(
                organization_id=r.organization_id,
                reservation_id=r.id,
                folio_id=primary_folio.id,
                date=r.check_in_date,
                description=f"Room Charge: {nights} night(s) @ ₹{r.nightly_rate:.2f}/night",
                category="room",
                amount=tax_res["subtotal"],
                subtotal=tax_res["subtotal"],
                tax_total=tax_res["tax_total"],
                tax_breakdown=json.dumps(tax_res["breakdown"]),
            )
            db.add(folio_room)

            for t in tax_res["breakdown"]:
                if t["amount"] > 0:
                    folio_tax = FolioItem(
                        organization_id=r.organization_id,
                        reservation_id=r.id,
                        folio_id=primary_folio.id,
                        date=r.check_in_date,
                        description=f"{t['name']} ({t.get('rate', 0)}%)",
                        category="tax",
                        amount=Decimal(str(t["amount"])),
                        subtotal=Decimal(str(t["amount"])),
                        tax_total=Decimal("0.00"),
                    )
                    db.add(folio_tax)
            db.commit()


def enrich_reservation(r: Reservation, db: Session, org_name: Optional[str] = None) -> ReservationResponse:
    """Calculates live folio totals and balance for a reservation."""
    from app.database import current_org_id
    prev_org = current_org_id.get()
    try:
        current_org_id.set(r.organization_id)
        # Ensure room charges exist for in-house reservations
        ensure_room_charges_posted(r, db)

        charges = (
            db.query(func.coalesce(func.sum(FolioItem.amount), 0))
            .filter(FolioItem.reservation_id == r.id)
            .scalar()
        ) or Decimal("0.00")

        payments = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.reservation_id == r.id)
            .scalar()
        ) or Decimal("0.00")

        balance = Decimal(str(charges)) - Decimal(str(payments))

        resp = ReservationResponse.model_validate(r)
        resp.total_charges = Decimal(str(charges))
        resp.total_payments = Decimal(str(payments))
        resp.balance = balance
        resp.organization_id = r.organization_id
        if org_name:
            resp.hotel_name = org_name
        else:
            org = db.query(Organization).filter(Organization.id == r.organization_id).first()
            resp.hotel_name = org.name if org else None
        return resp
    finally:
        current_org_id.set(prev_org)


@router.get("", response_model=PaginatedResponse[ReservationResponse])
def list_reservations(
    status: Optional[str] = Query(None, description="Filter by status (booked, checked_in, checked_out, cancelled, no_show)"),
    date_filter: Optional[str] = Query(None, description="'today', 'upcoming', 'past'"),
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Search confirmation #, guest name, or room number"),
    group_id: Optional[int] = Query(None, description="Filter by booking group ID"),
    property_id: Optional[int] = Query(None, description="Filter by property / organization ID"),
    all_properties: bool = Query(False, description="When true, show bookings from all properties for owner/admin"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List reservations with rich multi-criteria filters.
    Includes all bookings across properties by default with outer join support so no bookings are dropped."""
    org_map = {o.id: o.name for o in db.query(Organization).all()}

    # Query with outer joins so unassigned rooms or external guests are never dropped
    if all_properties and current_user.role in ("owner", "admin", "manager"):
        query = db.query(Reservation).execution_options(ignore_tenant=True).outerjoin(Reservation.guest).outerjoin(Reservation.room)
        if property_id:
            query = query.filter(Reservation.organization_id == property_id)
    else:
        query = db.query(Reservation).outerjoin(Reservation.guest).outerjoin(Reservation.room)

    today = get_current_business_date(db)

    if status and status.lower() != "all":
        query = query.filter(Reservation.status == status.lower())

    if group_id:
        query = query.filter(Reservation.group_id == group_id)

    if date_filter == "today":
        query = query.filter(
            or_(
                Reservation.check_in_date == today,
                Reservation.check_out_date == today,
                (Reservation.check_in_date <= today) & (Reservation.check_out_date >= today) & (Reservation.status == "checked_in"),
            )
        )
    elif date_filter == "upcoming":
        query = query.filter(Reservation.check_in_date >= today, Reservation.status == "booked")
    elif date_filter == "past":
        query = query.filter(Reservation.check_out_date < today)

    if from_date:
        query = query.filter(Reservation.check_in_date >= from_date)
    if to_date:
        query = query.filter(Reservation.check_out_date <= to_date)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Reservation.confirmation_number.ilike(s),
                Guest.first_name.ilike(s),
                Guest.last_name.ilike(s),
                Room.number.ilike(s),
            )
        )

    total = query.count()
    reservations = (
        query.options(joinedload(Reservation.guest), joinedload(Reservation.room))
        .order_by(Reservation.check_in_date.desc(), Reservation.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    res_ids = [r.id for r in reservations]
    charges_map = {}
    payments_map = {}
    if res_ids:
        folio_sums = (
            db.query(FolioItem.reservation_id, func.sum(FolioItem.amount))
            .execution_options(ignore_tenant=True)
            .filter(FolioItem.reservation_id.in_(res_ids))
            .group_by(FolioItem.reservation_id)
            .all()
        )
        charges_map = {r_id: Decimal(str(amt or 0)) for r_id, amt in folio_sums}

        payment_sums = (
            db.query(Payment.reservation_id, func.sum(Payment.amount))
            .execution_options(ignore_tenant=True)
            .filter(Payment.reservation_id.in_(res_ids))
            .group_by(Payment.reservation_id)
            .all()
        )
        payments_map = {r_id: Decimal(str(amt or 0)) for r_id, amt in payment_sums}

    items = []
    for r in reservations:
        chg = charges_map.get(r.id, Decimal("0.00"))
        if chg == 0 and r.status in ("checked_in", "checked_out") and r.nightly_rate:
            chg = Decimal(str(r.nightly_rate)) * Decimal(str(max(r.nights, 1)))
        pmt = payments_map.get(r.id, Decimal("0.00"))
        bal = chg - pmt

        resp = ReservationResponse.model_validate(r)
        resp.total_charges = chg
        resp.total_payments = pmt
        resp.balance = bal
        resp.organization_id = r.organization_id
        resp.hotel_name = org_map.get(r.organization_id)
        items.append(resp)

    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full details of a single reservation."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res and current_user.role in ("owner", "superadmin"):
        res = db.query(Reservation).execution_options(ignore_tenant=True).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )
    return enrich_reservation(res, db)


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new reservation with strict overlap detection, rate plan calculation, and deposit tracking."""
    # 1. Validate Guest
    guest = db.query(Guest).filter(Guest.id == payload.guest_id).first()
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guest with ID {payload.guest_id} does not exist",
        )

    # 2. Validate Room
    room = db.query(Room).filter(Room.id == payload.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {payload.room_id} does not exist",
        )

    # 2b. Validate Adults Limit (Max 2 adults allowed per room)
    if payload.adults > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 2 adults allowed per room.",
        )

    # 3. Check for Overlapping Active Reservations or Occupied Status (Double-Booking Guard)
    bdate = get_current_business_date(db)
    if payload.check_in_date <= bdate and room.status == "occupied":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Room {room.number} is currently OCCUPIED by another guest. Same room cannot be booked by two people for the same day.",
        )

    overlap = (
        db.query(Reservation)
        .execution_options(ignore_tenant=True)
        .filter(
            Reservation.room_id == payload.room_id,
            Reservation.status.in_(["booked", "checked_in"]),
            Reservation.check_in_date < payload.check_out_date,
            Reservation.check_out_date > payload.check_in_date,
        )
        .first()
    )

    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Room {room.number} is already booked from "
                f"{overlap.check_in_date.isoformat()} to {overlap.check_out_date.isoformat()} "
                f"(Confirmation #{overlap.confirmation_number}). Same room cannot be booked by two people for the same day."
            ),
        )

    # 4. Validate & Apply Rate Plan
    rate_plan = None
    if payload.rate_plan_id:
        rate_plan = db.query(RatePlan).filter(RatePlan.id == payload.rate_plan_id).first()
        if not rate_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rate plan with ID {payload.rate_plan_id} not found",
            )
        nights = (payload.check_out_date - payload.check_in_date).days
        if nights < rate_plan.min_stay:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rate plan '{rate_plan.name}' requires a minimum stay of {rate_plan.min_stay} night(s). (Stay is {nights} night(s))",
            )
        if rate_plan.max_stay and nights > rate_plan.max_stay:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rate plan '{rate_plan.name}' allows a maximum stay of {rate_plan.max_stay} night(s).",
            )

    # 5. Resolve Nightly Rate
    nightly_rate = payload.nightly_rate
    if nightly_rate is None:
        base_rate = room.room_type.base_rate if room.room_type else Decimal("150.00")
        if rate_plan:
            if rate_plan.modifier_type == "fixed":
                nightly_rate = rate_plan.modifier_value
            elif rate_plan.modifier_type == "percent":
                nightly_rate = base_rate * (Decimal("1.00") + (rate_plan.modifier_value / Decimal("100.00")))
            elif rate_plan.modifier_type == "absolute":
                nightly_rate = base_rate + rate_plan.modifier_value
            else:
                nightly_rate = base_rate
        else:
            nightly_rate = base_rate

    nightly_rate = max(Decimal("0.00"), Decimal(str(nightly_rate)).quantize(Decimal("0.01")))

    # 6. Calculate Required Deposit
    deposit_required = payload.deposit_required
    if deposit_required is None:
        if rate_plan and rate_plan.requires_deposit:
            nights = max(1, (payload.check_out_date - payload.check_in_date).days)
            stay_total = nightly_rate * Decimal(str(nights))
            if rate_plan.deposit_fixed_amount and rate_plan.deposit_fixed_amount > 0:
                deposit_required = rate_plan.deposit_fixed_amount
            elif rate_plan.deposit_percent and rate_plan.deposit_percent > 0:
                deposit_required = (stay_total * (rate_plan.deposit_percent / Decimal("100.00"))).quantize(Decimal("0.01"))
            else:
                deposit_required = nightly_rate  # Default 1 night
        else:
            deposit_required = Decimal("0.00")

    # 7. Generate unique confirmation number
    conf_num = generate_confirmation_number()
    while db.query(Reservation).filter(Reservation.confirmation_number == conf_num).first():
        conf_num = generate_confirmation_number()

    reservation = Reservation(
        confirmation_number=conf_num,
        guest_id=payload.guest_id,
        room_id=payload.room_id,
        rate_plan_id=payload.rate_plan_id,
        group_id=payload.group_id,
        check_in_date=payload.check_in_date,
        check_out_date=payload.check_out_date,
        adults=payload.adults,
        children=payload.children,
        nightly_rate=nightly_rate,
        deposit_required=deposit_required,
        deposit_paid=Decimal("0.00"),
        deposit_due_at=payload.check_in_date,
        status="booked",
        notes=payload.notes,
    )
    db.add(reservation)
    db.flush()

    # 8. Create Primary Folio
    primary_folio = Folio(
        reservation_id=reservation.id,
        name="Primary",
        is_master=True,
    )
    db.add(primary_folio)
    db.flush()

    # 8b. Record Advance Payment if provided
    if payload.advance_amount and payload.advance_amount > Decimal("0.00"):
        adv_amt = payload.advance_amount.quantize(Decimal("0.01"))
        adv_method = (payload.advance_payment_method or "cash").strip().lower()
        adv_ref = payload.advance_payment_reference or "Advance Deposit at Booking"
        payment = Payment(
            organization_id=reservation.organization_id,
            reservation_id=reservation.id,
            folio_id=primary_folio.id,
            date=payload.check_in_date,
            amount=adv_amt,
            method=adv_method,
            reference=adv_ref,
            is_deposit=True,
        )
        db.add(payment)
        reservation.deposit_paid = (reservation.deposit_paid or Decimal("0.00")) + adv_amt

    # 9. Log activity
    log = ActivityLog(
        event_type="reservation_created",
        description=f"Reservation #{conf_num} created for {guest.full_name} (Room {room.number})",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(reservation)

    return enrich_reservation(reservation, db)


@router.post("/walk-in", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_walk_in_reservation(
    payload: WalkInCheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Direct front-desk walk-in guest check-in from dashboard.
    Automatically creates or matches guest, validates room, books reservation,
    and if auto_check_in=True: marks reservation checked_in, flips room status to 'occupied',
    posts first night room charges & taxes to primary folio, and updates activity log."""
    org_id = current_user.organization_id

    # 1. Resolve or Create Guest
    guest = None
    clean_email = payload.email.strip().lower() if payload.email and payload.email.strip() else None
    clean_phone = payload.phone.strip() if payload.phone and payload.phone.strip() else None

    if clean_email:
        guest = db.query(Guest).filter(Guest.organization_id == org_id, Guest.email == clean_email).first()
    elif clean_phone:
        guest = db.query(Guest).filter(Guest.organization_id == org_id, Guest.phone == clean_phone).first()

    if not guest:
        import secrets
        auto_email = clean_email or f"{payload.first_name.lower().strip()}_{payload.last_name.lower().strip()}_{secrets.token_hex(2)}@guest.pms"
        guest = Guest(
            organization_id=org_id,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            email=auto_email,
            phone=clean_phone or "+910000000000",
            address=payload.address or "Walk-in Guest, India",
            notes=f"ID: {payload.id_type or 'Govt ID'} - {payload.id_number or 'Verified'}" if payload.id_number else None,
        )
        db.add(guest)
        db.flush()

    # 2. Validate Room
    room = db.query(Room).filter(Room.id == payload.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {payload.room_id} does not exist",
        )

    # 2b. Validate Adults Limit (Max 2 adults allowed per room)
    if payload.adults > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 2 adults allowed per room.",
        )

    # Effective check-in date
    bdate = get_current_business_date(db)
    cin = payload.check_in_date or bdate or date.today()
    cout = payload.check_out_date

    if cout <= cin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-out date must be strictly after check-in date.",
        )

    # 3. Check for Overlapping Active Reservations or Occupied Status (Double-Booking Guard)
    if payload.auto_check_in and room.status == "occupied":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Room {room.number} is currently OCCUPIED by another guest. Same room cannot be checked in by two people for the same day.",
        )

    overlap = (
        db.query(Reservation)
        .execution_options(ignore_tenant=True)
        .filter(
            Reservation.room_id == payload.room_id,
            Reservation.status.in_(["booked", "checked_in"]),
            Reservation.check_in_date < cout,
            Reservation.check_out_date > cin,
        )
        .first()
    )
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Room {room.number} is already occupied/booked from "
                f"{overlap.check_in_date.isoformat()} to {overlap.check_out_date.isoformat()} "
                f"(Confirmation #{overlap.confirmation_number}). Same room cannot be booked by two people for the same day."
            ),
        )

    # 4. Resolve Rate Plan & Nightly Rate
    rate_plan = None
    if payload.rate_plan_id:
        rate_plan = db.query(RatePlan).filter(RatePlan.id == payload.rate_plan_id).first()

    nightly_rate = payload.nightly_rate
    if nightly_rate is None:
        base_rate = room.room_type.base_rate if room.room_type else Decimal("3500.00")
        if rate_plan:
            if rate_plan.modifier_type == "fixed":
                nightly_rate = rate_plan.modifier_value
            elif rate_plan.modifier_type == "percent":
                nightly_rate = base_rate * (Decimal("1.00") + (rate_plan.modifier_value / Decimal("100.00")))
            elif rate_plan.modifier_type == "absolute":
                nightly_rate = base_rate + rate_plan.modifier_value
            else:
                nightly_rate = base_rate
        else:
            nightly_rate = base_rate

    nightly_rate = max(Decimal("0.00"), Decimal(str(nightly_rate)).quantize(Decimal("0.01")))

    # 5. Create Reservation
    conf_num = generate_confirmation_number()
    while db.query(Reservation).filter(Reservation.confirmation_number == conf_num).first():
        conf_num = generate_confirmation_number()

    reservation_status = "checked_in" if payload.auto_check_in else "booked"

    reservation = Reservation(
        organization_id=org_id,
        confirmation_number=conf_num,
        guest_id=guest.id,
        room_id=room.id,
        rate_plan_id=rate_plan.id if rate_plan else None,
        check_in_date=cin,
        check_out_date=cout,
        adults=payload.adults,
        children=payload.children,
        nightly_rate=nightly_rate,
        deposit_required=Decimal("0.00"),
        deposit_paid=Decimal("0.00"),
        status=reservation_status,
        notes=payload.notes,
    )
    db.add(reservation)
    db.flush()

    # 6. Create Primary Folio
    primary_folio = Folio(
        organization_id=org_id,
        reservation_id=reservation.id,
        name="Primary",
        is_master=True,
    )
    db.add(primary_folio)
    db.flush()

    # 7. If Auto Check-In: flip room status to occupied and post first night room charge & taxes
    if payload.auto_check_in:
        room.status = "occupied"
        nights = max(reservation.nights, 1)
        room_subtotal = nightly_rate * Decimal(str(nights))

        # Dynamic taxes
        tax_res = compute_tax_breakdown(
            amount=room_subtotal,
            category="room",
            nights=nights,
            adults=reservation.adults,
            db=db,
        )
        tax_total = tax_res.get("tax_total", Decimal("0.00"))
        tax_lines = tax_res.get("breakdown", [])

        item = FolioItem(
            organization_id=org_id,
            reservation_id=reservation.id,
            folio_id=primary_folio.id,
            date=cin,
            description=f"Room Charge: {reservation.check_in_date} to {reservation.check_out_date} (Room {room.number})",
            category="room",
            amount=room_subtotal + tax_total,
            subtotal=room_subtotal,
            tax_total=tax_total,
            tax_breakdown=json.dumps(tax_lines) if tax_lines else None,
        )
        db.add(item)

    # 7b. Record Advance Payment if provided
    if payload.advance_amount and payload.advance_amount > Decimal("0.00"):
        adv_amt = payload.advance_amount.quantize(Decimal("0.01"))
        adv_method = (payload.advance_payment_method or "cash").strip().lower()
        adv_ref = payload.advance_payment_reference or "Advance Payment at Walk-in"
        payment = Payment(
            organization_id=org_id,
            reservation_id=reservation.id,
            folio_id=primary_folio.id,
            date=cin,
            amount=adv_amt,
            method=adv_method,
            reference=adv_ref,
            is_deposit=True,
        )
        db.add(payment)
        reservation.deposit_paid = (reservation.deposit_paid or Decimal("0.00")) + adv_amt

    # 8. Activity Log
    act_desc = (
        f"Walk-in Check-in: Guest {guest.full_name} checked into Room {room.number} (#{conf_num})"
        if payload.auto_check_in
        else f"Direct Reservation #{conf_num} created for {guest.full_name} (Room {room.number})"
    )
    log = ActivityLog(
        organization_id=org_id,
        event_type="guest_walkin_checkin" if payload.auto_check_in else "reservation_created",
        description=act_desc,
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(reservation)

    return enrich_reservation(reservation, db)


@router.get("/run-sheet.pdf")
def download_run_sheet_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
):
    """Download branded A4 PDF daily run sheet & arrivals report."""
    bdate = get_current_business_date(db)
    target_date = bdate or date.today()

    pdf_bytes = build_daily_run_sheet_pdf(
        org=org,
        db=db,
        target_date=target_date,
        generated_by=current_user.full_name,
    )

    filename = f"RunSheet_{org.slug}_{target_date.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.post("/{reservation_id}/check-in", response_model=ReservationResponse)
def check_in_guest(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Check in a guest: marks reservation checked_in, flips room to occupied, posts room charge & taxes, and auto-applies paid deposits."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res and current_user.role in ("owner", "superadmin"):
        res = db.query(Reservation).execution_options(ignore_tenant=True).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    if res.status != "booked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check in reservation with status '{res.status}'. Must be 'booked'.",
        )

    primary_folio = get_or_create_primary_folio(res.id, db)

    # Update reservation status
    res.status = "checked_in"

    # Flip room status to occupied
    room = res.room
    if room:
        room.status = "occupied"

    # Automatically post room charge & taxes to primary folio if not already posted
    existing_room_charge = (
        db.query(FolioItem)
        .filter(FolioItem.reservation_id == res.id, FolioItem.category == "room")
        .first()
    )
    if not existing_room_charge:
        nights = max(res.nights, 1)
        room_subtotal = Decimal(str(res.nightly_rate)) * Decimal(str(nights))

        # Dynamic tax calculation
        tax_res = compute_tax_breakdown(
            amount=room_subtotal,
            category="room",
            nights=nights,
            adults=res.adults,
            db=db,
        )

        folio_room = FolioItem(
            reservation_id=res.id,
            folio_id=primary_folio.id,
            date=res.check_in_date,
            description=f"Room Charge: {nights} night(s) @ ₹{res.nightly_rate:.2f}/night",
            category="room",
            amount=tax_res["subtotal"],
            subtotal=tax_res["subtotal"],
            tax_total=tax_res["tax_total"],
            tax_breakdown=json.dumps(tax_res["breakdown"]),
        )
        db.add(folio_room)

        # Post each tax line
        for t in tax_res["breakdown"]:
            if t["amount"] > 0:
                folio_tax = FolioItem(
                    reservation_id=res.id,
                    folio_id=primary_folio.id,
                    date=res.check_in_date,
                    description=f"{t['name']} ({t.get('rate', 0)}%)",
                    category="tax",
                    amount=Decimal(str(t["amount"])),
                    subtotal=Decimal(str(t["amount"])),
                    tax_total=Decimal("0.00"),
                )
                db.add(folio_tax)

    # Ensure advance deposit is properly reflected as a Payment and negative FolioItem on the primary folio
    if res.deposit_paid and res.deposit_paid > 0:
        existing_deposit_payment = (
            db.query(Payment)
            .filter(Payment.reservation_id == res.id, Payment.is_deposit.is_(True))
            .first()
        )
        if not existing_deposit_payment:
            dep_payment = Payment(
                organization_id=res.organization_id,
                reservation_id=res.id,
                folio_id=primary_folio.id,
                date=res.check_in_date,
                amount=Decimal(str(res.deposit_paid)),
                method="advance_deposit",
                reference=f"Advance Deposit for #{res.confirmation_number}",
                is_deposit=True,
                is_refund=False,
            )
            db.add(dep_payment)

        existing_deposit_item = (
            db.query(FolioItem)
            .filter(FolioItem.reservation_id == res.id, FolioItem.category == "deposit_applied")
            .first()
        )
        if not existing_deposit_item:
            dep_folio_item = FolioItem(
                organization_id=res.organization_id,
                reservation_id=res.id,
                folio_id=primary_folio.id,
                date=res.check_in_date,
                description="Deposit Applied: Advance payment",
                category="deposit_applied",
                amount=-Decimal(str(res.deposit_paid)),
                subtotal=-Decimal(str(res.deposit_paid)),
                tax_total=Decimal("0.00"),
            )
            db.add(dep_folio_item)

    # Log activity
    log = ActivityLog(
        event_type="check_in",
        description=f"{res.guest.full_name} checked into Room {room.number if room else 'N/A'}",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(res)

    return enrich_reservation(res, db)


@router.post("/{reservation_id}/check-out", response_model=ReservationResponse)
def check_out_guest(
    reservation_id: int,
    payload: Optional[CheckOutRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Check out a guest: validates zero balance, flips room to dirty, spawns housekeeping turnover."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res and current_user.role in ("owner", "superadmin"):
        res = db.query(Reservation).execution_options(ignore_tenant=True).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    if res.status != "checked_in":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check out reservation with status '{res.status}'. Guest must be checked in.",
        )

    # Ensure room charges are posted to folio
    ensure_room_charges_posted(res, db)

    # Check Folio Balance Due across all folios
    charges = (
        db.query(func.coalesce(func.sum(FolioItem.amount), 0))
        .filter(FolioItem.reservation_id == res.id)
        .scalar()
    ) or Decimal("0.00")

    payments = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.reservation_id == res.id)
        .scalar()
    ) or Decimal("0.00")

    balance = Decimal(str(charges)) - Decimal(str(payments))

    # Auto-settle payment if requested
    if payload and payload.settle_payment and balance > Decimal("0.00"):
        pay_amount = payload.amount if (payload.amount and payload.amount > 0) else balance
        primary_folio = get_or_create_primary_folio(res.id, db)
        settlement_payment = Payment(
            organization_id=res.organization_id,
            reservation_id=res.id,
            folio_id=primary_folio.id,
            date=date.today(),
            amount=pay_amount,
            method=payload.payment_method or "cash",
            reference=payload.reference or "Settled at check-out",
        )
        db.add(settlement_payment)
        db.commit()

        # Log payment activity
        pay_log = ActivityLog(
            organization_id=res.organization_id,
            event_type="payment",
            description=f"Collected checkout payment of ₹{pay_amount:.2f} ({settlement_payment.method}) for Res #{res.confirmation_number}",
            actor=current_user.full_name,
        )
        db.add(pay_log)
        db.commit()

        # Recompute balance
        payments = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.reservation_id == res.id)
            .scalar()
        ) or Decimal("0.00")
        balance = Decimal(str(charges)) - Decimal(str(payments))

    if balance > Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Checkout blocked: Outstanding folio balance of ₹{balance:.2f}. "
                "Settle all pending charges before departure."
            ),
        )

    # Advance reservation status
    res.status = "checked_out"

    # Flip room status to dirty and create housekeeping turnover task
    room = res.room
    if room:
        room.status = "dirty"
        task = HousekeepingTask(
            organization_id=res.organization_id,
            room_id=room.id,
            task_type="checkout_clean",
            status="pending",
            priority="high",
            notes=f"Turnover clean for Room {room.number} following departure of {res.guest.full_name} (#{res.confirmation_number})",
        )
        db.add(task)

    # Log activity
    log = ActivityLog(
        organization_id=res.organization_id,
        event_type="check_out",
        description=f"{res.guest.full_name} checked out of Room {room.number if room else 'N/A'}",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(res)

    return enrich_reservation(res, db)


@router.get("/{reservation_id}/cancellation-quote", response_model=CancellationQuoteResponse)
def get_cancellation_quote(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Computes real-time cancellation penalty, deposit refund, and policy explanation."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    details = compute_cancellation_details(res, db)
    policy = details["policy"]

    return CancellationQuoteResponse(
        reservation_id=res.id,
        policy_name=policy.name if policy else "Standard Policy",
        free_cancel_until=details["free_cancel_until"],
        can_cancel_free=details["can_cancel_free"],
        penalty_amount=details["penalty_amount"],
        deposit_paid=details["deposit_paid"],
        refund_amount=details["refund_amount"],
        reason=details["reason"],
    )


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Cancel a booking, post cancellation penalties to folio, execute refunds, and release room allocation."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    if res.status in ["checked_out", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a reservation already marked as '{res.status}'",
        )

    # Calculate penalty & refund
    details = compute_cancellation_details(res, db)
    primary_folio = get_or_create_primary_folio(res.id, db)
    curr_date = get_current_business_date(db)

    # 1. Post cancellation fee if penalty > 0
    if details["penalty_amount"] > Decimal("0.00"):
        fee_item = FolioItem(
            reservation_id=res.id,
            folio_id=primary_folio.id,
            date=curr_date,
            description=f"Cancellation Fee: {details['reason']}",
            category="cancellation_fee",
            amount=details["penalty_amount"],
            subtotal=details["penalty_amount"],
            tax_total=Decimal("0.00"),
        )
        db.add(fee_item)

    # 2. Issue refund payment if refund > 0
    if details["refund_amount"] > Decimal("0.00"):
        refund_payment = Payment(
            reservation_id=res.id,
            folio_id=primary_folio.id,
            date=curr_date,
            amount=-details["refund_amount"],
            method="refund",
            reference=f"Refund for cancelled reservation #{res.confirmation_number}",
            is_deposit=False,
            is_refund=True,
        )
        db.add(refund_payment)
        res.deposit_paid = max(Decimal("0.00"), Decimal(str(res.deposit_paid)) - details["refund_amount"])

    res.status = "cancelled"

    # If room was marked occupied by this reservation, guest checked in: mark room dirty and spawn turnover housekeeping task
    if res.room and res.room.status == "occupied":
        res.room.status = "dirty"
        task = HousekeepingTask(
            organization_id=res.organization_id,
            room_id=res.room.id,
            task_type="turnover_clean",
            priority="high",
            status="pending",
            notes=f"Auto-generated: Cancellation turnover clean for Room {res.room.number} (#{res.confirmation_number})",
        )
        db.add(task)

    log = ActivityLog(
        event_type="reservation_cancelled",
        description=f"Reservation #{res.confirmation_number} cancelled for {res.guest.full_name} (Penalty: ₹{details['penalty_amount']}, Refund: ₹{details['refund_amount']})",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(res)

    return enrich_reservation(res, db)


@router.get("/{reservation_id}/deposit-status", response_model=DepositStatusResponse)
def get_deposit_status(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check deposit requirement, paid amount, and outstanding balance."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    req = res.deposit_required or Decimal("0.00")
    paid = res.deposit_paid or Decimal("0.00")
    bal = max(Decimal("0.00"), req - paid)
    return DepositStatusResponse(
        reservation_id=res.id,
        deposit_required=req,
        deposit_paid=paid,
        deposit_due_at=res.deposit_due_at,
        is_satisfied=paid >= req,
        balance_due=bal,
    )


@router.post("/{reservation_id}/deposit", response_model=DepositStatusResponse)
def record_deposit(
    reservation_id: int,
    payload: DepositRecordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Record an advance deposit payment for a reservation."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    primary_folio = get_or_create_primary_folio(res.id, db)
    curr_date = get_current_business_date(db)

    payment = Payment(
        reservation_id=res.id,
        folio_id=primary_folio.id,
        date=curr_date,
        amount=payload.amount,
        method=payload.payment_method,
        reference=payload.reference or f"Advance deposit for #{res.confirmation_number}",
        is_deposit=True,
        is_refund=False,
    )
    db.add(payment)

    res.deposit_paid = (res.deposit_paid or Decimal("0.00")) + payload.amount

    log = ActivityLog(
        event_type="payment",
        description=f"Deposit of ₹{payload.amount:.2f} received for reservation #{res.confirmation_number} ({payload.payment_method})",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(res)

    req = res.deposit_required or Decimal("0.00")
    paid = res.deposit_paid or Decimal("0.00")
    bal = max(Decimal("0.00"), req - paid)

    return DepositStatusResponse(
        reservation_id=res.id,
        deposit_required=req,
        deposit_paid=paid,
        deposit_due_at=res.deposit_due_at,
        is_satisfied=paid >= req,
        balance_due=bal,
    )


@router.patch("/{reservation_id}/move", response_model=ReservationResponse)
def move_reservation(
    reservation_id: int,
    payload: ReservationMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move a reservation to another room or change dates with strict overlap detection (Availability Timeline / Gantt)."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    if res.status not in ["booked", "checked_in"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move reservation with status '{res.status}'. Only booked or checked-in bookings can be moved.",
        )

    # Optimistic locking check
    if payload.version is not None and payload.version != res.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "conflict", "message": "This reservation was modified by another user. Please refresh and try again."}},
        )

    target_room_id = payload.room_id if payload.room_id is not None else res.room_id
    target_check_in = payload.check_in_date if payload.check_in_date is not None else res.check_in_date
    target_check_out = payload.check_out_date if payload.check_out_date is not None else res.check_out_date

    if target_check_out <= target_check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-out date must be strictly after check-in date.",
        )

    # Validate target room exists
    target_room = db.query(Room).filter(Room.id == target_room_id).first()
    if not target_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target room with ID {target_room_id} not found.",
        )

    # Check for conflicts on target room & date window excluding this reservation itself
    overlap = (
        db.query(Reservation)
        .filter(
            Reservation.id != res.id,
            Reservation.room_id == target_room_id,
            Reservation.status.in_(["booked", "checked_in"]),
            Reservation.check_in_date < target_check_out,
            Reservation.check_out_date > target_check_in,
        )
        .first()
    )

    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Room {target_room.number} is unavailable from "
                f"{overlap.check_in_date.isoformat()} to {overlap.check_out_date.isoformat()} "
                f"(Booked by {overlap.guest.full_name} #{overlap.confirmation_number})."
            ),
        )

    # If guest is already checked in and room is changing, update room statuses
    old_room = res.room
    if res.status == "checked_in" and target_room_id != res.room_id:
        if old_room:
            old_room.status = "dirty"
            task = HousekeepingTask(
                room_id=old_room.id,
                task_type="stayover_clean",
                status="pending",
                priority="high",
                notes=f"Turnover clean for Room {old_room.number} after guest #{res.confirmation_number} relocated to Room {target_room.number}",
            )
            db.add(task)
        target_room.status = "occupied"

    before_state = {
        "room_id": res.room_id,
        "check_in_date": str(res.check_in_date),
        "check_out_date": str(res.check_out_date),
        "version": res.version,
    }

    res.room_id = target_room_id
    res.check_in_date = target_check_in
    res.check_out_date = target_check_out
    res.version = (res.version or 1) + 1

    after_state = {
        "room_id": res.room_id,
        "check_in_date": str(res.check_in_date),
        "check_out_date": str(res.check_out_date),
        "version": res.version,
    }

    log_audit(
        db=db,
        org_id=res.organization_id,
        user_id=current_user.id,
        action="reservation_moved",
        entity_type="reservation",
        entity_id=res.id,
        before_state=before_state,
        after_state=after_state,
    )

    log = ActivityLog(
        organization_id=res.organization_id,
        event_type="reservation_moved",
        description=f"Reservation #{res.confirmation_number} moved to Room {target_room.number} ({target_check_in} to {target_check_out})",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(res)

    return enrich_reservation(res, db)


@router.put("/{reservation_id}", response_model=ReservationResponse)
def update_reservation(
    reservation_id: int,
    payload: ReservationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update reservation details with optimistic concurrency protection and audit tracking."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Optimistic locking check
    if payload.version is not None and payload.version != res.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "conflict", "message": "This reservation was modified by another user. Please refresh and try again."}},
        )

    before_state = {
        "room_id": res.room_id,
        "check_in_date": str(res.check_in_date),
        "check_out_date": str(res.check_out_date),
        "nightly_rate": float(res.nightly_rate),
        "adults": res.adults,
        "children": res.children,
        "notes": res.notes,
        "version": res.version,
    }

    target_room_id = payload.room_id if payload.room_id is not None else res.room_id
    target_cin = payload.check_in_date if payload.check_in_date is not None else res.check_in_date
    target_cout = payload.check_out_date if payload.check_out_date is not None else res.check_out_date

    if target_cout <= target_cin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Check-out must be after check-in")

    # If room or dates changed, check for overlap with other active reservations
    if (payload.room_id is not None and payload.room_id != res.room_id) or \
       (payload.check_in_date is not None and payload.check_in_date != res.check_in_date) or \
       (payload.check_out_date is not None and payload.check_out_date != res.check_out_date):

        target_room = db.query(Room).filter(Room.id == target_room_id).first()
        if not target_room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Room {target_room_id} not found")

        overlap = (
            db.query(Reservation)
            .execution_options(ignore_tenant=True)
            .filter(
                Reservation.id != res.id,
                Reservation.room_id == target_room_id,
                Reservation.status.in_(["booked", "checked_in"]),
                Reservation.check_in_date < target_cout,
                Reservation.check_out_date > target_cin,
            )
            .first()
        )
        if overlap:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room {target_room.number} is unavailable from {overlap.check_in_date.isoformat()} to {overlap.check_out_date.isoformat()} (Booked by {overlap.guest.full_name if overlap.guest else 'Guest'} #{overlap.confirmation_number}). Same room cannot be booked by two people for the same day.",
            )

        # If guest is currently checked in and room changed, sync room statuses
        if res.status == "checked_in" and payload.room_id is not None and payload.room_id != res.room_id:
            old_room = res.room
            if old_room:
                old_room.status = "dirty"
                task = HousekeepingTask(
                    organization_id=res.organization_id,
                    room_id=old_room.id,
                    task_type="turnover_clean",
                    priority="high",
                    status="pending",
                    notes=f"Auto-generated: Room move from {old_room.number} to {target_room.number} for {res.guest.full_name if res.guest else 'Guest'}",
                )
                db.add(task)
            target_room.status = "occupied"

        res.room_id = target_room_id
        res.check_in_date = target_cin
        res.check_out_date = target_cout

    if payload.nightly_rate is not None:
        res.nightly_rate = Decimal(str(payload.nightly_rate))
    if payload.adults is not None:
        if payload.adults > 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 2 adults allowed per room.")
        res.adults = payload.adults
    if payload.children is not None:
        res.children = payload.children
    if payload.notes is not None:
        res.notes = payload.notes
    if payload.rate_plan_id is not None:
        res.rate_plan_id = payload.rate_plan_id
    if payload.group_id is not None:
        res.group_id = payload.group_id

    res.version = (res.version or 1) + 1

    after_state = {
        "room_id": res.room_id,
        "check_in_date": str(res.check_in_date),
        "check_out_date": str(res.check_out_date),
        "nightly_rate": float(res.nightly_rate),
        "adults": res.adults,
        "children": res.children,
        "notes": res.notes,
        "version": res.version,
    }

    log_audit(
        db=db,
        org_id=res.organization_id,
        user_id=current_user.id,
        action="reservation_updated",
        entity_type="reservation",
        entity_id=res.id,
        before_state=before_state,
        after_state=after_state,
    )

    db.commit()
    db.refresh(res)
    return enrich_reservation(res, db)


@router.get("/{reservation_id}/invoice.pdf")
def download_invoice_pdf(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
):
    """Download branded A4 PDF tax invoice with sequential invoice numbering."""
    from app.database import current_org_id

    # Allow lookup ignoring tenant isolation so cross-tenant/super-admin or demo reservations don't 404
    res = (
        db.query(Reservation)
        .execution_options(ignore_tenant=True)
        .filter(Reservation.id == reservation_id)
        .first()
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Enforce tenant isolation for regular users
    if res.organization_id != current_user.organization_id and current_user.role not in ("owner", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Set context to reservation's tenant organization so folios, payments, guest load properly
    prev_org_id = current_org_id.get()
    try:
        current_org_id.set(res.organization_id)
        ensure_room_charges_posted(res, db)
        res_org = db.query(Organization).filter(Organization.id == res.organization_id).first()
        active_org = res_org or org

        pdf_bytes, invoice_number = build_reservation_invoice_pdf(
            reservation=res,
            org=active_org,
            db=db,
            generated_by=current_user.full_name,
        )
    finally:
        current_org_id.set(prev_org_id)

    filename = f"Invoice_{invoice_number}_{res.confirmation_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )

