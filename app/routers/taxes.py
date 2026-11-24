"""Tax Rates and Dynamic Tax Calculation Engine."""
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import TaxRate, User
from app.schemas import TaxRateCreate, TaxRateUpdate, TaxRateResponse

router = APIRouter(prefix="/api/taxes", tags=["Tax Engine"])


def compute_tax_breakdown(
    amount: Decimal,
    category: str,
    nights: int = 1,
    adults: int = 1,
    db: Session = None,
) -> dict:
    """Computes applicable inclusive/exclusive taxes for a given line item."""
    if not db:
        return {"subtotal": amount, "tax_total": Decimal("0.00"), "breakdown": []}

    target_applies = ["all"]
    if category == "room":
        target_applies.append("rooms")
    else:
        target_applies.append("extras")

    active_taxes = (
        db.query(TaxRate)
        .filter(TaxRate.active.is_(True), TaxRate.applies_to.in_(target_applies))
        .order_by(TaxRate.sort_order.asc(), TaxRate.id.asc())
        .all()
    )

    if not active_taxes:
        from app.config import settings
        if settings.HOTEL_TAX_RATE > 0:
            gst_amount = (amount * Decimal(str(settings.HOTEL_TAX_RATE))).quantize(Decimal("0.01"))
            return {
                "subtotal": amount,
                "tax_total": gst_amount,
                "breakdown": [
                    {
                        "name": f"Goods & Services Tax (GST {int(settings.HOTEL_TAX_RATE * 100)}%)",
                        "rate": float(settings.HOTEL_TAX_RATE * 100),
                        "amount": float(gst_amount),
                        "type": "exclusive",
                    }
                ],
            }
        return {"subtotal": amount, "tax_total": Decimal("0.00"), "breakdown": []}

    subtotal = amount
    exclusive_tax_total = Decimal("0.00")
    breakdown = []

    # 1. Process inclusive taxes first (extract from base amount)
    inclusive_rate_sum = sum(t.rate for t in active_taxes if t.type == "inclusive")
    if inclusive_rate_sum > 0:
        subtotal = (amount / (Decimal("1.00") + (inclusive_rate_sum / Decimal("100.00")))).quantize(Decimal("0.01"))
        for t in active_taxes:
            if t.type == "inclusive" and t.rate > 0:
                inc_amount = (subtotal * (t.rate / Decimal("100.00"))).quantize(Decimal("0.01"))
                breakdown.append({
                    "name": t.name,
                    "rate": float(t.rate),
                    "amount": float(inc_amount),
                    "type": "inclusive",
                })

    # 2. Process exclusive taxes (add on top of subtotal)
    for t in active_taxes:
        if t.type == "exclusive":
            t_amount = Decimal("0.00")
            if t.per == "night":
                if t.rate > 0:
                    t_amount = (subtotal * (t.rate / Decimal("100.00"))).quantize(Decimal("0.01"))
                elif t.fixed_amount > 0:
                    t_amount = (t.fixed_amount * Decimal(str(nights))).quantize(Decimal("0.01"))
            elif t.per == "stay":
                if t.rate > 0:
                    t_amount = (subtotal * (t.rate / Decimal("100.00"))).quantize(Decimal("0.01"))
                elif t.fixed_amount > 0:
                    t_amount = t.fixed_amount.quantize(Decimal("0.01"))
            elif t.per == "person_per_night":
                if t.fixed_amount > 0:
                    t_amount = (t.fixed_amount * Decimal(str(nights * adults))).quantize(Decimal("0.01"))
                elif t.rate > 0:
                    t_amount = (subtotal * (t.rate / Decimal("100.00"))).quantize(Decimal("0.01"))

            exclusive_tax_total += t_amount
            breakdown.append({
                "name": t.name,
                "rate": float(t.rate),
                "amount": float(t_amount),
                "type": "exclusive",
            })

    return {
        "subtotal": subtotal,
        "tax_total": exclusive_tax_total,
        "breakdown": breakdown,
    }


@router.get("", response_model=List[TaxRateResponse])
def list_taxes(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all configured tax rates."""
    query = db.query(TaxRate)
    if active_only:
        query = query.filter(TaxRate.active.is_(True))
    return query.order_by(TaxRate.sort_order.asc(), TaxRate.id.asc()).all()


@router.post("", response_model=TaxRateResponse, status_code=status.HTTP_201_CREATED)
def create_tax(
    payload: TaxRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Create a new tax rate (Admin/Manager only)."""
    tax = TaxRate(
        name=payload.name.strip(),
        rate=payload.rate,
        fixed_amount=payload.fixed_amount,
        applies_to=payload.applies_to,
        type=payload.type,
        per=payload.per,
        active=payload.active,
        sort_order=payload.sort_order,
    )
    db.add(tax)
    db.commit()
    db.refresh(tax)
    return tax


@router.get("/{id}", response_model=TaxRateResponse)
def get_tax(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single tax rate by ID."""
    tax = db.query(TaxRate).filter(TaxRate.id == id).first()
    if not tax:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tax rate #{id} not found.")
    return tax


@router.put("/{id}", response_model=TaxRateResponse)
def update_tax(
    id: int,
    payload: TaxRateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Update a tax rate (Admin/Manager only)."""
    tax = db.query(TaxRate).filter(TaxRate.id == id).first()
    if not tax:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tax rate #{id} not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(tax, k, v)

    db.commit()
    db.refresh(tax)
    return tax


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tax(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Delete a tax rate (Admin/Manager only)."""
    tax = db.query(TaxRate).filter(TaxRate.id == id).first()
    if not tax:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tax rate #{id} not found.")
    db.delete(tax)
    db.commit()
    return None
