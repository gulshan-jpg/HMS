"""Rooms and Room Types API Endpoints."""
from datetime import date
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import check_plan_limits, check_subscription_state, get_current_org, get_current_user, require_role
from app.models import ActivityLog, FolioItem, Guest, Organization, Payment, Reservation, Room, RoomType, User
from app.routers.reservations import ensure_room_charges_posted
from app.schemas import (
    PaginatedResponse,
    RoomCreate,
    RoomDetailResponse,
    RoomResponse,
    RoomTypeResponse,
    RoomUpdate,
    RoomUpdateStatus,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/api/rooms", tags=["Rooms"])


@router.get("/types", response_model=List[RoomTypeResponse])
def list_room_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all available room types and their configurations."""
    return db.query(RoomType).order_by(RoomType.base_rate.asc()).all()


@router.get("", response_model=PaginatedResponse[RoomResponse])
def list_rooms(
    status: Optional[str] = Query(None, description="Filter by room status"),
    floor: Optional[int] = Query(None, description="Filter by floor number"),
    room_type_id: Optional[int] = Query(None, description="Filter by room type ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List hotel rooms with optional status, floor, and type filters."""
    query = db.query(Room)

    if status:
        query = query.filter(Room.status == status)
    if floor is not None:
        query = query.filter(Room.floor == floor)
    if room_type_id is not None:
        query = query.filter(Room.room_type_id == room_type_id)

    total = query.count()
    rooms = query.order_by(Room.number.asc()).offset(offset).limit(limit).all()

    return PaginatedResponse(
        items=[RoomResponse.model_validate(r) for r in rooms],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{room_id}", response_model=RoomDetailResponse)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed room status, including current occupant and next arrival."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found",
        )

    today = date.today()
    # Find active in-house reservation
    active_res = (
        db.query(Reservation)
        .filter(
            Reservation.room_id == room.id,
            Reservation.status == "checked_in",
        )
        .first()
    )

    current_guest = None
    current_reservation_id = None
    current_reservation_confirmation = None
    current_balance = None
    current_total_charges = None
    current_total_payments = None
    current_check_in_date = None
    current_check_out_date = None

    if active_res:
        ensure_room_charges_posted(active_res, db)
        charges = (
            db.query(func.coalesce(func.sum(FolioItem.amount), 0))
            .filter(FolioItem.reservation_id == active_res.id)
            .scalar()
        ) or Decimal("0.00")
        payments = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.reservation_id == active_res.id)
            .scalar()
        ) or Decimal("0.00")
        current_total_charges = Decimal(str(charges))
        current_total_payments = Decimal(str(payments))
        current_balance = current_total_charges - current_total_payments
        current_reservation_id = active_res.id
        current_reservation_confirmation = active_res.confirmation_number
        current_check_in_date = active_res.check_in_date
        current_check_out_date = active_res.check_out_date
        if active_res.guest:
            current_guest = active_res.guest.full_name

    # Find next upcoming arrival
    next_res = (
        db.query(Reservation)
        .filter(
            Reservation.room_id == room.id,
            Reservation.status == "booked",
            Reservation.check_in_date >= today,
        )
        .order_by(Reservation.check_in_date.asc())
        .first()
    )

    next_arrival = None
    next_arrival_date = None
    if next_res and next_res.guest:
        next_arrival = next_res.guest.full_name
        next_arrival_date = next_res.check_in_date

    room_resp = RoomResponse.model_validate(room)
    return RoomDetailResponse(
        **room_resp.model_dump(),
        current_guest=current_guest,
        current_reservation_id=current_reservation_id,
        current_reservation_confirmation=current_reservation_confirmation,
        current_balance=current_balance,
        current_total_charges=current_total_charges,
        current_total_payments=current_total_payments,
        current_check_in_date=current_check_in_date,
        current_check_out_date=current_check_out_date,
        next_arrival=next_arrival,
        next_arrival_date=next_arrival_date,
    )


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreate,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Add a new room to inventory."""
    # Enforce tier limits
    check_plan_limits(org, "rooms", db)

    existing = db.query(Room).filter(
        Room.number == payload.number.strip(),
        Room.organization_id == org.id,
        Room.deleted_at.is_(None),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room number {payload.number} already exists",
        )

    room_type = db.query(RoomType).filter(
        RoomType.id == payload.room_type_id,
        RoomType.organization_id == org.id,
    ).first()
    if not room_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room type with ID {payload.room_type_id} does not exist",
        )

    room = Room(
        organization_id=org.id,
        number=payload.number.strip(),
        floor=payload.floor,
        room_type_id=payload.room_type_id,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    # Log activity
    log = ActivityLog(
        organization_id=org.id,
        event_type="room_created",
        description=f"Room {room.number} added ({room_type.name})",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return RoomResponse.model_validate(room)


@router.patch("/{room_id}/status", response_model=RoomResponse)
def update_room_status(
    room_id: int,
    payload: RoomUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Quickly toggle or update room operational status with optimistic locking."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found",
        )

    # Optimistic concurrency check
    if payload.version is not None and payload.version != room.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "conflict", "message": "This room was modified by another user. Please refresh and try again."}},
        )

    # Guard: Cannot manually set room to Available if a guest is actively checked in
    if payload.status == "available":
        active_res = (
            db.query(Reservation)
            .filter(
                Reservation.room_id == room.id,
                Reservation.status == "checked_in",
            )
            .first()
        )
        if active_res:
            guest_name = active_res.guest.full_name if active_res.guest else "Guest"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {room.number} cannot be marked Available while guest '{guest_name}' is currently checked in. Please check out the guest first.",
            )

    before_state = {
        "status": room.status,
        "notes": room.notes,
        "version": room.version,
    }

    old_status = room.status
    room.status = payload.status
    if payload.notes:
        room.notes = payload.notes
    room.version = (room.version or 1) + 1

    after_state = {
        "status": room.status,
        "notes": room.notes,
        "version": room.version,
    }

    log_audit(
        db=db,
        org_id=room.organization_id,
        user_id=current_user.id,
        action="room_status_changed",
        entity_type="room",
        entity_id=room.id,
        before_state=before_state,
        after_state=after_state,
    )

    db.commit()
    db.refresh(room)

    # Record activity log
    log = ActivityLog(
        organization_id=room.organization_id,
        event_type="room_status",
        description=f"Room {room.number} changed from {old_status} to {room.status}",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return RoomResponse.model_validate(room)


@router.put("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    payload: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "manager", "admin")),
):
    """Update room configuration with optimistic locking and audit logging."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found",
        )

    # Optimistic concurrency check
    if payload.version is not None and payload.version != room.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "conflict", "message": "This room was modified by another user. Please refresh and try again."}},
        )

    # Guard: Cannot manually set room to Available if a guest is actively checked in
    if payload.status == "available":
        active_res = (
            db.query(Reservation)
            .filter(
                Reservation.room_id == room.id,
                Reservation.status == "checked_in",
            )
            .first()
        )
        if active_res:
            guest_name = active_res.guest.full_name if active_res.guest else "Guest"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {room.number} cannot be marked Available while guest '{guest_name}' is currently checked in. Please check out the guest first.",
            )

    before_state = {
        "number": room.number,
        "floor": room.floor,
        "room_type_id": room.room_type_id,
        "status": room.status,
        "notes": room.notes,
        "version": room.version,
    }

    if payload.number is not None:
        num_clean = payload.number.strip()
        if num_clean != room.number:
            existing = db.query(Room).filter(
                Room.number == num_clean,
                Room.organization_id == room.organization_id,
                Room.id != room.id,
                Room.deleted_at.is_(None),
            ).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Room {num_clean} already exists")
            room.number = num_clean

    if payload.floor is not None:
        room.floor = payload.floor
    if payload.room_type_id is not None:
        rt = db.query(RoomType).filter(RoomType.id == payload.room_type_id).first()
        if not rt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Room type {payload.room_type_id} not found")
        room.room_type_id = payload.room_type_id
    if payload.status is not None:
        room.status = payload.status
    if payload.notes is not None:
        room.notes = payload.notes

    room.version = (room.version or 1) + 1

    after_state = {
        "number": room.number,
        "floor": room.floor,
        "room_type_id": room.room_type_id,
        "status": room.status,
        "notes": room.notes,
        "version": room.version,
    }

    log_audit(
        db=db,
        org_id=room.organization_id,
        user_id=current_user.id,
        action="room_updated",
        entity_type="room",
        entity_id=room.id,
        before_state=before_state,
        after_state=after_state,
    )

    db.commit()
    db.refresh(room)
    return RoomResponse.model_validate(room)

