"""Guests Management API Endpoints."""
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app.models import ActivityLog, FolioItem, Guest, Payment, Reservation, User
from app.schemas import (
    GuestCreate,
    GuestResponse,
    GuestUpdate,
    PaginatedResponse,
    ReservationResponse,
)

router = APIRouter(prefix="/api/guests", tags=["Guests"])


def enrich_guest_stats(guest: Guest, db: Session, is_admin: bool = True) -> GuestResponse:
    """Computes total stays, lifetime spend, and last stay date for a guest."""
    # Stays count (completed or in-house)
    total_stays = (
        db.query(func.count(Reservation.id))
        .filter(
            Reservation.guest_id == guest.id,
            Reservation.status.in_(["checked_in", "checked_out"]),
        )
        .scalar()
        or 0
    )

    # Last stay date
    last_stay = (
        db.query(func.max(Reservation.check_out_date))
        .filter(Reservation.guest_id == guest.id)
        .scalar()
    )

    # Total spend across all guest reservations (Only revealed to Admin/Manager)
    total_spend = Decimal("0.00")
    if is_admin:
        total_spend = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .join(Reservation, Payment.reservation_id == Reservation.id)
            .filter(Reservation.guest_id == guest.id)
            .scalar()
        ) or Decimal("0.00")

    return GuestResponse(
        id=guest.id,
        first_name=guest.first_name,
        last_name=guest.last_name,
        full_name=guest.full_name,
        email=guest.email,
        phone=guest.phone,
        address=guest.address,
        id_number=guest.id_number,
        notes=guest.notes,
        created_at=guest.created_at,
        total_stays=total_stays,
        total_spend=Decimal(str(total_spend)),
        last_stay=last_stay,
    )


@router.get("", response_model=PaginatedResponse[GuestResponse])
def list_guests(
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve guests with full contact details and lifetime spend metrics."""
    query = db.query(Guest)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Guest.first_name.ilike(s),
                Guest.last_name.ilike(s),
                Guest.email.ilike(s),
                Guest.phone.ilike(s),
            )
        )

    total = query.count()
    guests = query.order_by(Guest.last_name.asc(), Guest.first_name.asc()).offset(offset).limit(limit).all()

    is_admin = current_user.role in ["admin", "manager"]
    enriched_items = [enrich_guest_stats(g, db, is_admin=is_admin) for g in guests]

    return PaginatedResponse(
        items=enriched_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{guest_id}")
def get_guest_detail(
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get guest profile along with full reservation history."""
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guest with ID {guest_id} not found",
        )

    is_admin = current_user.role in ["admin", "manager"]
    stats = enrich_guest_stats(guest, db, is_admin=is_admin)

    # Fetch reservations
    reservations = (
        db.query(Reservation)
        .filter(Reservation.guest_id == guest.id)
        .order_by(Reservation.check_in_date.desc())
        .all()
    )

    res_list = []
    for r in reservations:
        total_charges = db.query(func.coalesce(func.sum(FolioItem.amount), 0)).filter(FolioItem.reservation_id == r.id).scalar() or Decimal("0.00")
        total_paid = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.reservation_id == r.id).scalar() or Decimal("0.00")
        balance = total_charges - total_paid

        res_resp = ReservationResponse.model_validate(r)
        res_resp.total_charges = Decimal(str(total_charges))
        res_resp.total_payments = Decimal(str(total_paid))
        res_resp.balance = Decimal(str(balance))
        res_list.append(res_resp)

    return {
        "guest": stats,
        "reservations": res_list,
    }


@router.post("", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
def create_guest(
    payload: GuestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new guest profile."""
    existing = db.query(Guest).filter(Guest.email == payload.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Guest with email {payload.email} already registered",
        )

    guest = Guest(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=payload.email.lower().strip(),
        phone=payload.phone.strip(),
        address=payload.address.strip() if payload.address else None,
        id_number=payload.id_number.strip() if payload.id_number else None,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(guest)
    db.commit()
    db.refresh(guest)

    # Log activity
    log = ActivityLog(
        event_type="guest_created",
        description=f"Guest profile created for {guest.full_name}",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return enrich_guest_stats(guest, db)


@router.put("/{guest_id}", response_model=GuestResponse)
def update_guest(
    guest_id: int,
    payload: GuestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update existing guest profile details."""
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guest with ID {guest_id} not found",
        )

    if payload.email:
        email_clean = payload.email.lower().strip()
        existing = db.query(Guest).filter(Guest.email == email_clean, Guest.id != guest_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email {payload.email} is already in use by another guest",
            )
        guest.email = email_clean

    if payload.first_name:
        guest.first_name = payload.first_name.strip()
    if payload.last_name:
        guest.last_name = payload.last_name.strip()
    if payload.phone:
        guest.phone = payload.phone.strip()
    if payload.address is not None:
        guest.address = payload.address.strip() if payload.address else None
    if payload.id_number is not None:
        guest.id_number = payload.id_number.strip() if payload.id_number else None
    if payload.notes is not None:
        guest.notes = payload.notes.strip() if payload.notes else None

    db.commit()
    db.refresh(guest)

    return enrich_guest_stats(guest, db)
