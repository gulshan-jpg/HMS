"""Billing and Folio Management API Endpoints."""
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import ActivityLog, Folio, FolioItem, Payment, Reservation, User
from app.routers.reservations import ensure_room_charges_posted
from app.schemas import (
    FolioDetailResponse,
    FolioItemCreate,
    FolioItemResponse,
    GuestBrief,
    PaymentCreate,
    PaymentResponse,
)

router = APIRouter(prefix="/api/billing", tags=["Billing"])


@router.get("/reservations/{reservation_id}/folio", response_model=FolioDetailResponse)
def get_reservation_folio(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager", "accountant")),
):
    """Retrieve itemized folio breakdown, receipts, payments, and outstanding balance."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res and current_user.role in ("owner", "superadmin"):
        res = db.query(Reservation).execution_options(ignore_tenant=True).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Ensure in-house guests have room charges accurately posted
    ensure_room_charges_posted(res, db)

    items = (
        db.query(FolioItem)
        .filter(FolioItem.reservation_id == res.id)
        .order_by(FolioItem.date.asc(), FolioItem.id.asc())
        .all()
    )

    payments = (
        db.query(Payment)
        .filter(Payment.reservation_id == res.id)
        .order_by(Payment.date.asc(), Payment.id.asc())
        .all()
    )

    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")
    total_amount = Decimal("0.00")

    for item in items:
        amt = Decimal(str(item.amount))
        total_amount += amt
        if item.category == "tax":
            tax_total += amt
        else:
            subtotal += amt

    total_paid = sum((Decimal(str(p.amount)) for p in payments), Decimal("0.00"))
    balance_due = total_amount - total_paid

    return FolioDetailResponse(
        reservation_id=res.id,
        confirmation_number=res.confirmation_number,
        guest=GuestBrief.model_validate(res.guest),
        room_number=res.room.number if res.room else "Unassigned",
        room_type=res.room.room_type.name if res.room and res.room.room_type else "Standard",
        check_in_date=res.check_in_date,
        check_out_date=res.check_out_date,
        nights=res.nights,
        items=[FolioItemResponse.model_validate(i) for i in items],
        payments=[PaymentResponse.model_validate(p) for p in payments],
        subtotal=subtotal,
        tax_total=tax_total,
        total_amount=total_amount,
        total_paid=total_paid,
        balance_due=balance_due,
    )


@router.post("/reservations/{reservation_id}/charges", response_model=FolioItemResponse, status_code=status.HTTP_201_CREATED)
def post_folio_charge(
    reservation_id: int,
    payload: FolioItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Post an incidental or room charge / adjustment to a reservation folio."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res and current_user.role in ("owner", "superadmin"):
        res = db.query(Reservation).execution_options(ignore_tenant=True).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    if res.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot post charges to a cancelled reservation",
        )

    target_folio_id = payload.folio_id
    if not target_folio_id:
        primary_folio = db.query(Folio).filter(Folio.reservation_id == res.id, Folio.is_master.is_(True)).first()
        if not primary_folio:
            primary_folio = Folio(reservation_id=res.id, name="Primary", is_master=True)
            db.add(primary_folio)
            db.commit()
            db.refresh(primary_folio)
        target_folio_id = primary_folio.id

    item = FolioItem(
        organization_id=res.organization_id,
        reservation_id=res.id,
        folio_id=target_folio_id,
        date=payload.date,
        description=payload.description.strip(),
        category=payload.category,
        amount=payload.amount,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Activity log
    log = ActivityLog(
        event_type="charge",
        description=f"Posted {item.category} charge of ₹{item.amount:.2f} ({item.description}) to Res #{res.confirmation_number}",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return FolioItemResponse.model_validate(item)


@router.post("/reservations/{reservation_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def post_folio_payment(
    reservation_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "owner")),
):
    """Post a transaction payment receipt to a reservation folio."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res and current_user.role in ("owner", "superadmin"):
        res = db.query(Reservation).execution_options(ignore_tenant=True).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    target_folio_id = payload.folio_id
    if not target_folio_id:
        primary_folio = db.query(Folio).filter(Folio.reservation_id == res.id, Folio.is_master.is_(True)).first()
        if not primary_folio:
            primary_folio = Folio(organization_id=res.organization_id, reservation_id=res.id, name="Primary", is_master=True)
            db.add(primary_folio)
            db.commit()
            db.refresh(primary_folio)
        target_folio_id = primary_folio.id

    payment = Payment(
        organization_id=res.organization_id,
        reservation_id=res.id,
        folio_id=target_folio_id,
        date=payload.date,
        amount=payload.amount,
        method=payload.method,
        reference=payload.reference.strip() if payload.reference else None,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Activity log
    log = ActivityLog(
        event_type="payment",
        description=f"Received payment of ₹{payment.amount:.2f} ({payment.method}) for Res #{res.confirmation_number}",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return PaymentResponse.model_validate(payment)
