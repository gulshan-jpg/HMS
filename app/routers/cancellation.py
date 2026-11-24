"""Cancellation Policies Management and Penalty Calculation Engine."""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import CancellationPolicy, Reservation, BusinessDate, User, FolioItem, Payment
from app.schemas import (
    CancellationPolicyCreate,
    CancellationPolicyUpdate,
    CancellationPolicyResponse,
    CancellationQuoteResponse,
)

router = APIRouter(prefix="/api/cancellation-policies", tags=["Cancellation Policies"])


def get_current_business_date(db: Session) -> date:
    """Helper to get current active hotel business date."""
    bd = db.query(BusinessDate).filter(BusinessDate.status == "open").first()
    return bd.date if bd else date.today()


def compute_cancellation_details(reservation: Reservation, db: Session) -> dict:
    """Computes cancellation penalty, refund, and fee window according to policy."""
    policy = None
    if reservation.rate_plan and reservation.rate_plan.cancellation_policy:
        policy = reservation.rate_plan.cancellation_policy
    else:
        policy = db.query(CancellationPolicy).filter(CancellationPolicy.active.is_(True)).first()

    if not policy:
        # Fallback standard 24h flexible policy
        policy = CancellationPolicy(
            id=0,
            name="Flexible 24-Hour",
            free_cancel_days=1,
            penalty_type="first_night",
            penalty_value=Decimal("100.00"),
        )

    current_date = get_current_business_date(db)
    free_cancel_until = reservation.check_in_date - timedelta(days=policy.free_cancel_days)
    can_cancel_free = current_date <= free_cancel_until

    deposit_paid = Decimal(str(reservation.deposit_paid or "0.00"))
    is_refundable = reservation.rate_plan.refundable if reservation.rate_plan else True

    if can_cancel_free:
        penalty_amount = Decimal("0.00")
        reason = f"Cancelled on or before {free_cancel_until} within the free window ({policy.name})."
        refund_amount = deposit_paid if is_refundable else Decimal("0.00")
    else:
        # Outside free window
        if policy.penalty_type == "none":
            penalty_amount = Decimal("0.00")
        elif policy.penalty_type == "first_night":
            penalty_amount = Decimal(str(reservation.nightly_rate)).quantize(Decimal("0.01"))
        elif policy.penalty_type == "percent":
            total_stay = reservation.nightly_rate * Decimal(str(reservation.nights))
            penalty_amount = (total_stay * (policy.penalty_value / Decimal("100.00"))).quantize(Decimal("0.01"))
        elif policy.penalty_type == "fixed":
            penalty_amount = Decimal(str(policy.penalty_value)).quantize(Decimal("0.01"))
        else:
            penalty_amount = Decimal(str(reservation.nightly_rate)).quantize(Decimal("0.01"))

        reason = f"Cancellation penalty applied under policy '{policy.name}' ({policy.penalty_type})."
        if is_refundable:
            refund_amount = max(Decimal("0.00"), deposit_paid - penalty_amount)
        else:
            refund_amount = Decimal("0.00")

    return {
        "policy": policy,
        "free_cancel_until": free_cancel_until,
        "can_cancel_free": can_cancel_free,
        "penalty_amount": penalty_amount,
        "deposit_paid": deposit_paid,
        "refund_amount": refund_amount,
        "reason": reason,
    }


@router.get("", response_model=List[CancellationPolicyResponse])
def list_cancellation_policies(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all cancellation policies."""
    query = db.query(CancellationPolicy)
    if active_only:
        query = query.filter(CancellationPolicy.active.is_(True))
    return query.order_by(CancellationPolicy.id.asc()).all()


@router.post("", response_model=CancellationPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_cancellation_policy(
    payload: CancellationPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Create a new cancellation policy (Admin/Manager only)."""
    policy = CancellationPolicy(
        name=payload.name.strip(),
        description=payload.description,
        free_cancel_days=payload.free_cancel_days,
        penalty_type=payload.penalty_type,
        penalty_value=payload.penalty_value,
        no_show_penalty=payload.no_show_penalty,
        no_show_value=payload.no_show_value,
        active=payload.active,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/{id}", response_model=CancellationPolicyResponse)
def get_cancellation_policy(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single cancellation policy by ID."""
    policy = db.query(CancellationPolicy).filter(CancellationPolicy.id == id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy #{id} not found.")
    return policy


@router.put("/{id}", response_model=CancellationPolicyResponse)
def update_cancellation_policy(
    id: int,
    payload: CancellationPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Update a cancellation policy (Admin/Manager only)."""
    policy = db.query(CancellationPolicy).filter(CancellationPolicy.id == id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy #{id} not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(policy, k, v)

    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cancellation_policy(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Delete a cancellation policy (Admin/Manager only)."""
    policy = db.query(CancellationPolicy).filter(CancellationPolicy.id == id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy #{id} not found.")
    db.delete(policy)
    db.commit()
    return None
