"""Rate Calendar and Dynamic Rate Overrides API."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import ActivityLog, RateOverride, Reservation, Room, RoomType, User
from app.schemas import (
    RateCalendarDayItem,
    RateCalendarResponse,
    RateCalendarRoomTypeItem,
    RateOverrideBulkCreate,
    RateOverrideCreate,
    RateOverrideResponse,
)
from app.routers.cancellation import get_current_business_date

router = APIRouter(prefix="", tags=["Rate Calendar"])


@router.get("/api/rate-calendar", response_model=RateCalendarResponse)
def get_rate_calendar(
    start_date: Optional[date] = Query(None, description="Start date of 30-day window (defaults to business date)"),
    days: int = Query(30, ge=1, le=90, description="Number of days to display (default 30)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Retrieve high-performance 30-day matrix of nightly rates, occupancy % and room availability per room type."""
    if not start_date:
        start_date = get_current_business_date(db)

    end_date = start_date + timedelta(days=days)

    # 1. Fetch Room Types and Rooms
    room_types = db.query(RoomType).order_by(RoomType.id.asc()).all()
    rooms = db.query(Room).all()

    # Map room_type_id -> total room count & room ids
    room_count_by_type: Dict[int, int] = {}
    room_ids_by_type: Dict[int, List[int]] = {}
    room_to_type: Dict[int, int] = {}

    for rt in room_types:
        room_count_by_type[rt.id] = 0
        room_ids_by_type[rt.id] = []

    for r in rooms:
        if r.room_type_id in room_count_by_type:
            room_count_by_type[r.room_type_id] += 1
            room_ids_by_type[r.room_type_id].append(r.id)
            room_to_type[r.id] = r.room_type_id

    # 2. Fetch all Overrides in Window
    overrides = (
        db.query(RateOverride)
        .filter(RateOverride.date >= start_date, RateOverride.date < end_date)
        .all()
    )
    overrides_map: Dict[Tuple[int, date], RateOverride] = {
        (o.room_type_id, o.date): o for o in overrides
    }

    # 3. Fetch all active reservations overlapping the window
    active_reservations = (
        db.query(Reservation.room_id, Reservation.check_in_date, Reservation.check_out_date)
        .filter(
            Reservation.status.in_(["booked", "checked_in"]),
            Reservation.check_in_date < end_date,
            Reservation.check_out_date > start_date,
        )
        .all()
    )

    # Pre-index occupancy: (room_type_id, date) -> occupied room count
    occupancy_map: Dict[Tuple[int, date], int] = {}
    for res_room_id, cin, cout in active_reservations:
        rt_id = room_to_type.get(res_room_id)
        if not rt_id:
            continue
        cur_d = max(start_date, cin)
        limit_d = min(end_date, cout)
        while cur_d < limit_d:
            key = (rt_id, cur_d)
            occupancy_map[key] = occupancy_map.get(key, 0) + 1
            cur_d += timedelta(days=1)

    # 4. Assemble matrix
    rt_items: List[RateCalendarRoomTypeItem] = []
    for rt in room_types:
        total_rooms = room_count_by_type.get(rt.id, 0)
        day_items: List[RateCalendarDayItem] = []

        cur = start_date
        while cur < end_date:
            override = overrides_map.get((rt.id, cur))
            occupied = occupancy_map.get((rt.id, cur), 0)
            available = max(0, total_rooms - occupied)
            occ_pct = round((occupied / total_rooms * 100.0), 1) if total_rooms > 0 else 0.0

            rate = override.rate if override else rt.base_rate

            day_items.append(
                RateCalendarDayItem(
                    date=cur.isoformat(),
                    rate=Decimal(str(rate)).quantize(Decimal("0.01")),
                    base_rate=Decimal(str(rt.base_rate)).quantize(Decimal("0.01")),
                    occupancy_pct=occ_pct,
                    occupied_count=occupied,
                    available_count=available,
                    total_rooms=total_rooms,
                    override_id=override.id if override else None,
                    closed=override.closed if override else False,
                    closed_to_arrival=override.closed_to_arrival if override else False,
                    closed_to_departure=override.closed_to_departure if override else False,
                    min_stay=override.min_stay if override else None,
                )
            )
            cur += timedelta(days=1)

        rt_items.append(
            RateCalendarRoomTypeItem(
                id=rt.id,
                name=rt.name,
                code=rt.code,
                room_count=total_rooms,
                base_rate=Decimal(str(rt.base_rate)).quantize(Decimal("0.01")),
                days=day_items,
            )
        )

    return RateCalendarResponse(
        start_date=start_date.isoformat(),
        days_count=days,
        room_types=rt_items,
    )


@router.put("/api/rate-overrides", response_model=RateOverrideResponse)
def upsert_rate_override(
    payload: RateOverrideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Upsert a single daily rate override (Admin/Manager only)."""
    room_type = db.query(RoomType).filter(RoomType.id == payload.room_type_id).first()
    if not room_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room type with ID {payload.room_type_id} not found",
        )

    override = (
        db.query(RateOverride)
        .filter(
            RateOverride.room_type_id == payload.room_type_id,
            RateOverride.date == payload.date,
        )
        .first()
    )

    if not override:
        override = RateOverride(
            room_type_id=payload.room_type_id,
            date=payload.date,
            rate=payload.rate,
            min_stay=payload.min_stay,
            closed=payload.closed,
            closed_to_arrival=payload.closed_to_arrival,
            closed_to_departure=payload.closed_to_departure,
        )
        db.add(override)
    else:
        override.rate = payload.rate
        override.min_stay = payload.min_stay
        override.closed = payload.closed
        override.closed_to_arrival = payload.closed_to_arrival
        override.closed_to_departure = payload.closed_to_departure

    log = ActivityLog(
        event_type="rate_override",
        description=f"Rate override set for {room_type.name} on {payload.date.isoformat()} (₹{payload.rate})",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(override)

    return override


@router.post("/api/rate-overrides/bulk")
def bulk_rate_overrides(
    payload: RateOverrideBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Apply rate adjustments, minimum stay, or closures to multiple room types across date ranges."""
    if not payload.room_type_ids or not payload.dates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one room type and one date must be specified for bulk override.",
        )

    updated_count = 0
    for rt_id in payload.room_type_ids:
        for d in payload.dates:
            override = (
                db.query(RateOverride)
                .filter(RateOverride.room_type_id == rt_id, RateOverride.date == d)
                .first()
            )
            if not override:
                override = RateOverride(
                    room_type_id=rt_id,
                    date=d,
                    rate=payload.rate if payload.rate is not None else Decimal("100.00"),
                    min_stay=payload.min_stay,
                    closed=payload.closed if payload.closed is not None else False,
                    closed_to_arrival=payload.closed_to_arrival if payload.closed_to_arrival is not None else False,
                    closed_to_departure=payload.closed_to_departure if payload.closed_to_departure is not None else False,
                )
                db.add(override)
            else:
                if payload.rate is not None:
                    override.rate = payload.rate
                if payload.min_stay is not None:
                    override.min_stay = payload.min_stay
                if payload.closed is not None:
                    override.closed = payload.closed
                if payload.closed_to_arrival is not None:
                    override.closed_to_arrival = payload.closed_to_arrival
                if payload.closed_to_departure is not None:
                    override.closed_to_departure = payload.closed_to_departure
            updated_count += 1

    log = ActivityLog(
        event_type="rate_override_bulk",
        description=f"Bulk rate overrides applied to {len(payload.room_type_ids)} room types across {len(payload.dates)} dates ({updated_count} cells)",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return {"message": "Bulk overrides successfully applied", "cells_updated": updated_count}


@router.delete("/api/rate-overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rate_override(
    override_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Delete a rate override, returning that date to the standard base rate."""
    override = db.query(RateOverride).filter(RateOverride.id == override_id).first()
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate override with ID {override_id} not found",
        )

    db.delete(override)
    db.commit()
    return None
