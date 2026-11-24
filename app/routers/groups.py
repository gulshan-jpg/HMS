"""Group Bookings and Room Block Management API."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import (
    ActivityLog,
    BookingGroup,
    Folio,
    FolioItem,
    GroupBlock,
    Guest,
    Payment,
    Reservation,
    Room,
    RoomType,
    User,
)
from app.schemas import (
    BookingGroupCreate,
    BookingGroupResponse,
    BookingGroupUpdate,
    GroupBlockResponse,
    GroupDetailResponse,
    ReservationResponse,
)
from app.routers.cancellation import get_current_business_date
from app.routers.reservations import create_reservation, enrich_reservation, generate_confirmation_number

router = APIRouter(prefix="/api/groups", tags=["Group Bookings"])


def enrich_group_response(group: BookingGroup, db: Session) -> BookingGroupResponse:
    """Enriches BookingGroup with pickup stats per block."""
    blocks = (
        db.query(GroupBlock)
        .filter(GroupBlock.group_id == group.id)
        .all()
    )

    # Count picked up reservations by room type
    res_list = (
        db.query(Reservation)
        .filter(Reservation.group_id == group.id, Reservation.status != "cancelled")
        .all()
    )

    room_ids = [r.room_id for r in res_list]
    rooms = db.query(Room).filter(Room.id.in_(room_ids)).all() if room_ids else []
    room_to_type = {rm.id: rm.room_type_id for rm in rooms}

    picked_by_type = {}
    for r in res_list:
        rt_id = room_to_type.get(r.room_id)
        if rt_id:
            picked_by_type[rt_id] = picked_by_type.get(rt_id, 0) + 1

    block_responses: List[GroupBlockResponse] = []
    total_blocked = 0
    total_picked = len(res_list)

    for b in blocks:
        total_blocked += b.count
        picked = picked_by_type.get(b.room_type_id, 0)
        avail = max(0, b.count - picked)
        block_responses.append(
            GroupBlockResponse(
                id=b.id,
                group_id=b.group_id,
                room_type_id=b.room_type_id,
                room_type_name=b.room_type.name if b.room_type else "Room Type",
                count=b.count,
                rate=Decimal(str(b.rate)),
                picked_up_count=picked,
                available_to_pick=avail,
            )
        )

    # Check cutoff date auto-release
    today = get_current_business_date(db)
    current_status = group.status
    if today > group.cutoff_date and group.status == "tentative":
        current_status = "cutoff_passed"

    resp = BookingGroupResponse(
        id=group.id,
        hotel_id=group.hotel_id,
        name=group.name,
        contact_name=group.contact_name,
        contact_email=group.contact_email,
        contact_phone=group.contact_phone,
        check_in=group.check_in,
        check_out=group.check_out,
        cutoff_date=group.cutoff_date,
        status=current_status,
        notes=group.notes,
        created_at=group.created_at,
        rooms_blocked_total=total_blocked,
        rooms_picked_up_total=total_picked,
        room_blocks=block_responses,
    )
    return resp


@router.get("", response_model=List[BookingGroupResponse])
def list_groups(
    status_filter: Optional[str] = Query(None, description="Filter by status (tentative, confirmed, cancelled)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all corporate, event, or wedding booking groups."""
    query = db.query(BookingGroup)
    if status_filter and status_filter.lower() != "all":
        query = query.filter(BookingGroup.status == status_filter.lower())

    groups = query.order_by(BookingGroup.check_in.desc(), BookingGroup.id.desc()).all()
    return [enrich_group_response(g, db) for g in groups]


@router.post("", response_model=BookingGroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: BookingGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Create a new group booking with room allocations/blocks."""
    group = BookingGroup(
        name=payload.name.strip(),
        contact_name=payload.contact_name.strip(),
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone.strip(),
        check_in=payload.check_in,
        check_out=payload.check_out,
        cutoff_date=payload.cutoff_date,
        status="confirmed",
        notes=payload.notes,
    )
    db.add(group)
    db.flush()

    for blk in payload.room_blocks:
        rt = db.query(RoomType).filter(RoomType.id == blk.room_type_id).first()
        if not rt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room type with ID {blk.room_type_id} does not exist",
            )
        group_block = GroupBlock(
            group_id=group.id,
            room_type_id=blk.room_type_id,
            count=blk.count,
            rate=blk.rate,
        )
        db.add(group_block)

    log = ActivityLog(
        event_type="group_created",
        description=f"Group booking '{group.name}' created ({group.check_in} to {group.check_out})",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(group)

    return enrich_group_response(group, db)


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full details of a booking group including all picked up reservations and master billing balance."""
    group = db.query(BookingGroup).filter(BookingGroup.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking group with ID {group_id} not found",
        )

    base_resp = enrich_group_response(group, db)

    # Fetch member reservations
    res_list = (
        db.query(Reservation)
        .filter(Reservation.group_id == group.id)
        .order_by(Reservation.check_in_date.asc(), Reservation.id.asc())
        .all()
    )

    # Aggregate master folio totals across group reservations
    master_total = Decimal("0.00")
    master_paid = Decimal("0.00")

    enriched_res: List[ReservationResponse] = []
    for r in res_list:
        e = enrich_reservation(r, db)
        enriched_res.append(e)
        master_total += e.total_charges
        master_paid += e.total_payments

    master_balance = master_total - master_paid

    detail = GroupDetailResponse(
        **base_resp.model_dump(),
        reservations=enriched_res,
        master_folio_total=master_total,
        master_folio_paid=master_paid,
        master_folio_balance=master_balance,
    )
    return detail


@router.put("/{group_id}", response_model=BookingGroupResponse)
def update_group(
    group_id: int,
    payload: BookingGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Update booking group parameters, dates, or contact info."""
    group = db.query(BookingGroup).filter(BookingGroup.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking group with ID {group_id} not found",
        )

    if payload.name is not None:
        group.name = payload.name.strip()
    if payload.contact_name is not None:
        group.contact_name = payload.contact_name.strip()
    if payload.contact_email is not None:
        group.contact_email = payload.contact_email
    if payload.contact_phone is not None:
        group.contact_phone = payload.contact_phone.strip()
    if payload.check_in is not None:
        group.check_in = payload.check_in
    if payload.check_out is not None:
        group.check_out = payload.check_out
    if payload.cutoff_date is not None:
        group.cutoff_date = payload.cutoff_date
    if payload.status is not None:
        group.status = payload.status
    if payload.notes is not None:
        group.notes = payload.notes

    db.commit()
    db.refresh(group)
    return enrich_group_response(group, db)


@router.post("/{group_id}/cancel", response_model=BookingGroupResponse)
def cancel_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Cancel a booking group and release all unfulfilled room blocks."""
    group = db.query(BookingGroup).filter(BookingGroup.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking group with ID {group_id} not found",
        )

    group.status = "cancelled"

    log = ActivityLog(
        event_type="group_cancelled",
        description=f"Group booking '{group.name}' was cancelled. Room blocks released.",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(group)
    return enrich_group_response(group, db)


@router.delete("/{group_id}/reservations/{reservation_id}")
def detach_group_reservation(
    group_id: int,
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detach a reservation from this group booking."""
    res = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id, Reservation.group_id == group_id)
        .first()
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation {reservation_id} is not attached to Group {group_id}",
        )

    res.group_id = None
    res.is_group_master = False
    db.commit()
    return {"message": f"Reservation #{res.confirmation_number} detached from group."}
