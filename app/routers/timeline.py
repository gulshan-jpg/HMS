"""Availability Timeline / Gantt API."""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import FolioItem, Payment, Reservation, Room, User
from app.schemas import TimelineReservationItem, TimelineResponse, TimelineRoomItem
from app.routers.cancellation import get_current_business_date

router = APIRouter(prefix="/api/timeline", tags=["Timeline"])


@router.get("", response_model=TimelineResponse)
def get_timeline(
    start_date: Optional[date] = Query(None, description="Start date of the 30-day timeline view"),
    days: int = Query(30, ge=7, le=60, description="Window duration in days (default 30)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve 30-day room availability and booking timeline for Gantt visualization."""
    if not start_date:
        start_date = get_current_business_date(db)

    end_date = start_date + timedelta(days=days)

    # 1. Fetch all rooms
    rooms = db.query(Room).join(Room.room_type).order_by(Room.floor.asc(), Room.number.asc()).all()

    # 2. Fetch all reservations overlapping this timeline window
    reservations = (
        db.query(Reservation)
        .filter(
            Reservation.status.in_(["booked", "checked_in"]),
            Reservation.check_in_date < end_date,
            Reservation.check_out_date > start_date,
        )
        .all()
    )

    # Map room_id -> list of reservations
    res_by_room = {}
    for r in reservations:
        res_by_room.setdefault(r.room_id, []).append(r)

    timeline_rooms: List[TimelineRoomItem] = []

    for r in rooms:
        res_items: List[TimelineReservationItem] = []
        room_res_list = res_by_room.get(r.id, [])

        for b in room_res_list:
            # Calculate live balance
            charges = (
                db.query(func.coalesce(func.sum(FolioItem.amount), 0))
                .filter(FolioItem.reservation_id == b.id)
                .scalar()
            ) or Decimal("0.00")
            payments = (
                db.query(func.coalesce(func.sum(Payment.amount), 0))
                .filter(Payment.reservation_id == b.id)
                .scalar()
            ) or Decimal("0.00")
            balance = Decimal(str(charges)) - Decimal(str(payments))

            guest_name = b.guest.full_name if b.guest else "Guest"
            initials = "".join([part[0].upper() for part in guest_name.split() if part])[:2] or "G"

            res_items.append(
                TimelineReservationItem(
                    id=b.id,
                    confirmation_number=b.confirmation_number,
                    guest_name=guest_name,
                    guest_initials=initials,
                    check_in_date=b.check_in_date.isoformat(),
                    check_out_date=b.check_out_date.isoformat(),
                    nights=b.nights,
                    nightly_rate=Decimal(str(b.nightly_rate)),
                    status=b.status,
                    adults=b.adults,
                    children=b.children,
                    balance=balance,
                )
            )

        timeline_rooms.append(
            TimelineRoomItem(
                id=r.id,
                number=r.number,
                floor=r.floor,
                room_type_name=r.room_type.name if r.room_type else "Standard Room",
                room_type_code=r.room_type.code if r.room_type else "STD",
                status=r.status,
                reservations=res_items,
            )
        )

    return TimelineResponse(
        start_date=start_date.isoformat(),
        days_count=days,
        rooms=timeline_rooms,
    )
