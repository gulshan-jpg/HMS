"""Night Audit, End-of-Day Processing, and Business Date Transition Engine."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import (
    ActivityLog,
    BusinessDate,
    DailySnapshot,
    Folio,
    FolioItem,
    Payment,
    Reservation,
    Room,
    User,
)
from app.schemas import (
    BusinessDateResponse,
    DailySnapshotResponse,
    NightAuditPreviewResponse,
    NightAuditRunRequest,
    NightAuditRunResponse,
)
from app.routers.cancellation import compute_cancellation_details, get_current_business_date
from app.routers.reservations import get_or_create_primary_folio
from app.routers.taxes import compute_tax_breakdown

router = APIRouter(prefix="/api/night-audit", tags=["Night Audit"])


def ensure_open_business_date(db: Session) -> BusinessDate:
    """Ensures an open business date exists in the system."""
    bd = db.query(BusinessDate).filter(BusinessDate.status == "open").first()
    if not bd:
        bd = BusinessDate(
            date=date.today(),
            status="open",
        )
        db.add(bd)
        db.commit()
        db.refresh(bd)
    return bd


@router.get("/business-date", response_model=BusinessDateResponse)
def get_business_date(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the current active hotel business date."""
    bd = ensure_open_business_date(db)
    return bd


@router.get("/preview", response_model=NightAuditPreviewResponse)
def preview_night_audit(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dry-run preview of night audit actions (charges to post, no-shows to mark, and departure warnings)."""
    curr_date = get_current_business_date(db)
    next_date = curr_date + timedelta(days=1)

    # 1. Checked-in reservations spanning current business date
    checked_in = (
        db.query(Reservation)
        .filter(
            Reservation.status == "checked_in",
            Reservation.check_in_date <= curr_date,
            Reservation.check_out_date > curr_date,
        )
        .all()
    )

    room_charges_to_post = 0
    room_charges_estimated = Decimal("0.00")

    for r in checked_in:
        posted_for_date = (
            db.query(FolioItem)
            .filter(
                FolioItem.reservation_id == r.id,
                FolioItem.date == curr_date,
                FolioItem.category == "room",
            )
            .first()
        )
        total_room_posted = (
            db.query(func.coalesce(func.sum(FolioItem.subtotal), 0))
            .filter(FolioItem.reservation_id == r.id, FolioItem.category == "room")
            .scalar()
        ) or Decimal("0.00")
        total_stay_expected = Decimal(str(r.nightly_rate)) * Decimal(str(max(r.nights, 1)))

        if not posted_for_date and (Decimal(str(total_room_posted)) < total_stay_expected):
            room_charges_to_post += 1
            room_charges_estimated += Decimal(str(r.nightly_rate))

    # 2. No-shows: 'booked' reservations with check-in on or before curr_date
    no_shows = (
        db.query(Reservation)
        .filter(
            Reservation.status == "booked",
            Reservation.check_in_date <= curr_date,
        )
        .all()
    )
    no_show_count = len(no_shows)
    no_show_penalties = sum(Decimal(str(r.nightly_rate)) for r in no_shows)

    # 3. Unresolved departures: checked_in reservations with check_out_date <= curr_date
    departures_due = (
        db.query(Reservation)
        .filter(
            Reservation.status == "checked_in",
            Reservation.check_out_date <= curr_date,
        )
        .all()
    )
    unresolved_departures_count = len(departures_due)

    can_run = unresolved_departures_count == 0
    warning = None
    if unresolved_departures_count > 0:
        warning = (
            f"There are {unresolved_departures_count} guest(s) due to depart on or before "
            f"{curr_date.isoformat()} who have not checked out. Check them out, extend stay, or check 'Force Close'."
        )

    return NightAuditPreviewResponse(
        business_date=curr_date,
        next_business_date=next_date,
        checked_in_reservations_count=len(checked_in),
        room_charges_to_post_count=room_charges_to_post,
        room_charges_estimated_total=room_charges_estimated,
        no_shows_count=no_show_count,
        no_show_estimated_penalties=no_show_penalties,
        unresolved_departures_count=unresolved_departures_count,
        can_run_without_force=can_run,
        warning_message=warning,
    )


@router.post("/run", response_model=NightAuditRunResponse)
def run_night_audit(
    payload: NightAuditRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Execute the End-of-Day Night Audit in an atomic transaction."""
    curr_bd = ensure_open_business_date(db)
    curr_date = curr_bd.date
    next_date = curr_date + timedelta(days=1)

    # Check unresolved departures if not force
    departures_due = (
        db.query(Reservation)
        .filter(
            Reservation.status == "checked_in",
            Reservation.check_out_date <= curr_date,
        )
        .all()
    )
    if departures_due and not payload.force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot close day: {len(departures_due)} reservation(s) due for checkout remain checked in. "
                "Resolve departures or enable 'Force Close' to proceed."
            ),
        )

    # 1. Post nightly room charges & taxes for in-house guests
    checked_in = (
        db.query(Reservation)
        .filter(
            Reservation.status == "checked_in",
            Reservation.check_in_date <= curr_date,
            Reservation.check_out_date > curr_date,
        )
        .all()
    )

    posted_charges_count = 0
    posted_charges_total = Decimal("0.00")

    for r in checked_in:
        posted_for_date = (
            db.query(FolioItem)
            .filter(
                FolioItem.reservation_id == r.id,
                FolioItem.date == curr_date,
                FolioItem.category == "room",
            )
            .first()
        )
        total_room_posted = (
            db.query(func.coalesce(func.sum(FolioItem.subtotal), 0))
            .filter(FolioItem.reservation_id == r.id, FolioItem.category == "room")
            .scalar()
        ) or Decimal("0.00")
        total_stay_expected = Decimal(str(r.nightly_rate)) * Decimal(str(max(r.nights, 1)))

        if not posted_for_date and (Decimal(str(total_room_posted)) < total_stay_expected):
            primary_folio = get_or_create_primary_folio(r.id, db)
            tax_res = compute_tax_breakdown(
                amount=r.nightly_rate,
                category="room",
                nights=1,
                adults=r.adults,
                db=db,
            )

            folio_room = FolioItem(
                reservation_id=r.id,
                folio_id=primary_folio.id,
                date=curr_date,
                description=f"Night Audit Room Charge: Night of {curr_date.isoformat()} (Room {r.room.number})",
                category="room",
                amount=tax_res["subtotal"],
                subtotal=tax_res["subtotal"],
                tax_total=tax_res["tax_total"],
                tax_breakdown=json.dumps(tax_res["breakdown"]),
            )
            db.add(folio_room)
            posted_charges_count += 1
            posted_charges_total += tax_res["subtotal"]

            for t in tax_res["breakdown"]:
                if t["amount"] > 0:
                    folio_tax = FolioItem(
                        reservation_id=r.id,
                        folio_id=primary_folio.id,
                        date=curr_date,
                        description=f"{t['name']} ({t.get('rate', 0)}%)",
                        category="tax",
                        amount=Decimal(str(t["amount"])),
                        subtotal=Decimal(str(t["amount"])),
                        tax_total=Decimal("0.00"),
                    )
                    db.add(folio_tax)

    # 2. Mark No-Shows & apply penalty
    no_shows = (
        db.query(Reservation)
        .filter(
            Reservation.status == "booked",
            Reservation.check_in_date <= curr_date,
        )
        .all()
    )

    marked_no_shows_count = 0
    no_show_penalties_total = Decimal("0.00")

    for ns in no_shows:
        ns.status = "no_show"
        marked_no_shows_count += 1
        details = compute_cancellation_details(ns, db)
        penalty = details.get("penalty_amount", ns.nightly_rate)
        if penalty > Decimal("0.00"):
            primary_folio = get_or_create_primary_folio(ns.id, db)
            fee_item = FolioItem(
                reservation_id=ns.id,
                folio_id=primary_folio.id,
                date=curr_date,
                description="No-Show Penalty Charge",
                category="cancellation_fee",
                amount=penalty,
                subtotal=penalty,
                tax_total=Decimal("0.00"),
            )
            db.add(fee_item)
            no_show_penalties_total += penalty

    # 3. Compute Day Analytics for Daily Snapshot
    total_rooms = db.query(Room).count()
    occupied_count = len(checked_in)
    occ_rate = round((occupied_count / total_rooms * 100.0), 2) if total_rooms > 0 else Decimal("0.00")

    # Room Revenue for curr_date
    room_rev = (
        db.query(func.coalesce(func.sum(FolioItem.amount), 0))
        .filter(FolioItem.date == curr_date, FolioItem.category == "room")
        .scalar()
    ) or Decimal("0.00")
    room_rev = Decimal(str(room_rev))

    # Total Revenue (room + extras + penalties)
    total_rev = (
        db.query(func.coalesce(func.sum(FolioItem.amount), 0))
        .filter(FolioItem.date == curr_date, FolioItem.category != "deposit_applied")
        .scalar()
    ) or Decimal("0.00")
    total_rev = Decimal(str(total_rev))

    # Tax collected
    tax_col = (
        db.query(func.coalesce(func.sum(FolioItem.amount), 0))
        .filter(FolioItem.date == curr_date, FolioItem.category == "tax")
        .scalar()
    ) or Decimal("0.00")
    tax_col = Decimal(str(tax_col))

    adr = (room_rev / Decimal(str(occupied_count))).quantize(Decimal("0.01")) if occupied_count > 0 else Decimal("0.00")
    revpar = (room_rev / Decimal(str(total_rooms))).quantize(Decimal("0.01")) if total_rooms > 0 else Decimal("0.00")

    arrivals_count = db.query(Reservation).filter(Reservation.check_in_date == curr_date).count()
    departures_count = db.query(Reservation).filter(Reservation.check_out_date == curr_date).count()

    snapshot = DailySnapshot(
        business_date=curr_date,
        occupancy_rate=Decimal(str(occ_rate)),
        adr=adr,
        revpar=revpar,
        arrivals=arrivals_count,
        departures=departures_count,
        room_revenue=room_rev,
        total_revenue=total_rev,
        tax_collected=tax_col,
    )
    db.add(snapshot)

    # 4. Close current business date and open next
    curr_bd.status = "closed"
    curr_bd.closed_at = datetime.now(timezone.utc)
    curr_bd.closed_by_user_id = current_user.id

    new_bd = BusinessDate(
        date=next_date,
        status="open",
    )
    db.add(new_bd)

    # 5. Log activity
    log = ActivityLog(
        event_type="night_audit_completed",
        description=f"Night audit completed. Closed {curr_date.isoformat()}, opened {next_date.isoformat()}.",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(snapshot)

    return NightAuditRunResponse(
        success=True,
        previous_business_date=curr_date,
        new_business_date=next_date,
        room_charges_posted=posted_charges_count,
        room_charges_total=posted_charges_total,
        no_shows_marked=marked_no_shows_count,
        no_show_penalties_total=no_show_penalties_total,
        snapshot=DailySnapshotResponse.model_validate(snapshot),
    )


@router.get("/history", response_model=List[DailySnapshotResponse])
def list_audit_history(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve historical daily end-of-day audit snapshots."""
    records = (
        db.query(DailySnapshot)
        .order_by(DailySnapshot.business_date.desc())
        .limit(limit)
        .all()
    )
    return records
