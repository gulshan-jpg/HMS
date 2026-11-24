"""Rate Plans Management and Dynamic Quotation Engine."""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.deps import get_current_user, require_role
from app.config import settings
from app.models import RatePlan, RoomType, RateOverride, TaxRate, User
from app.schemas import (
    RatePlanCreate,
    RatePlanUpdate,
    RatePlanResponse,
    RatePlanQuoteResponse,
    RateQuoteNightly,
    TaxBreakdownItem,
)

router = APIRouter(prefix="/api/rate-plans", tags=["Rate Plans"])


@router.get("", response_model=List[RatePlanResponse])
def list_rate_plans(
    room_type_id: Optional[int] = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all rate plans with optional room_type or active filtering."""
    query = db.query(RatePlan)
    if active_only:
        query = query.filter(RatePlan.active.is_(True))
    if room_type_id:
        query = query.filter(
            or_(RatePlan.room_type_id == room_type_id, RatePlan.room_type_id.is_(None))
        )
    return query.order_by(RatePlan.min_stay.asc(), RatePlan.id.asc()).all()


@router.post("", response_model=RatePlanResponse, status_code=status.HTTP_201_CREATED)
def create_rate_plan(
    payload: RatePlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Create a new rate plan (Admin/Manager only)."""
    existing = db.query(RatePlan).filter(RatePlan.code == payload.code.upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rate plan code '{payload.code.upper()}' is already in use.",
        )

    if payload.room_type_id:
        rt = db.query(RoomType).filter(RoomType.id == payload.room_type_id).first()
        if not rt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room type #{payload.room_type_id} not found.",
            )

    plan = RatePlan(
        code=payload.code.upper().strip(),
        name=payload.name.strip(),
        description=payload.description,
        room_type_id=payload.room_type_id,
        modifier_type=payload.modifier_type,
        modifier_value=payload.modifier_value,
        meal_plan=payload.meal_plan,
        min_stay=payload.min_stay,
        max_stay=payload.max_stay,
        cancellation_policy_id=payload.cancellation_policy_id,
        refundable=payload.refundable,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        closed_to_arrival=payload.closed_to_arrival,
        closed_to_departure=payload.closed_to_departure,
        active=payload.active,
        requires_deposit=payload.requires_deposit,
        deposit_percent=payload.deposit_percent,
        deposit_fixed_amount=payload.deposit_fixed_amount,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/quote", response_model=RatePlanQuoteResponse)
def quote_rate_plan(
    room_type_id: int = Query(..., description="Target room type ID"),
    check_in: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    check_out: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    plan_id: Optional[int] = Query(None, description="Specific RatePlan ID. If omitted, default FLEX is used"),
    adults: int = Query(1, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculate exact nightly rate breakdown, subtotal, taxes, and deposit requirement."""
    if check_out <= check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-out date must be strictly after check-in date.",
        )

    room_type = db.query(RoomType).filter(RoomType.id == room_type_id).first()
    if not room_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room type #{room_type_id} does not exist.",
        )

    # Resolve rate plan
    plan: Optional[RatePlan] = None
    if plan_id:
        plan = db.query(RatePlan).filter(RatePlan.id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rate plan #{plan_id} not found.",
            )
    else:
        # Default to flexible plan or first active
        plan = (
            db.query(RatePlan)
            .filter(
                RatePlan.active.is_(True),
                or_(RatePlan.room_type_id == room_type_id, RatePlan.room_type_id.is_(None)),
            )
            .order_by(RatePlan.id.asc())
            .first()
        )

    if not plan:
        # Fallback synthetic flexible plan
        plan = RatePlan(
            id=0,
            code="FLEX",
            name="Flexible Standard Rate",
            modifier_type="percent",
            modifier_value=Decimal("0.00"),
            min_stay=1,
            refundable=True,
            meal_plan="room_only",
            requires_deposit=False,
        )

    nights = (check_out - check_in).days
    min_stay_met = nights >= plan.min_stay

    # Compute nightly rates
    nightly_rates: List[RateQuoteNightly] = []
    subtotal = Decimal("0.00")

    curr = check_in
    while curr < check_out:
        # 1. Base rate check (RateOverride priority > room_type.base_rate)
        override = (
            db.query(RateOverride)
            .filter(RateOverride.room_type_id == room_type_id, RateOverride.date == curr)
            .first()
        )
        base = override.rate if override else room_type.base_rate

        # 2. Plan modifier calculation
        if plan.modifier_type == "fixed":
            night_rate = plan.modifier_value
        elif plan.modifier_type == "percent":
            night_rate = base * (Decimal("1.00") + (plan.modifier_value / Decimal("100.00")))
        elif plan.modifier_type == "absolute":
            night_rate = base + plan.modifier_value
        else:
            night_rate = base

        night_rate = max(Decimal("0.00"), Decimal(str(night_rate)).quantize(Decimal("0.01")))
        subtotal += night_rate
        nightly_rates.append(
            RateQuoteNightly(
                date=curr.isoformat(),
                base_rate=Decimal(str(base)).quantize(Decimal("0.01")),
                rate=night_rate,
            )
        )
        curr += timedelta(days=1)

    subtotal = subtotal.quantize(Decimal("0.01"))

    # Compute taxes
    taxes_breakdown: List[TaxBreakdownItem] = []
    tax_total = Decimal("0.00")

    active_taxes = (
        db.query(TaxRate)
        .filter(TaxRate.active.is_(True), TaxRate.applies_to.in_(["rooms", "all"]))
        .order_by(TaxRate.sort_order.asc(), TaxRate.id.asc())
        .all()
    )

    if active_taxes:
        for t in active_taxes:
            t_amount = Decimal("0.00")
            if t.type == "exclusive":
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
            elif t.type == "inclusive":
                # Inclusive tax is already within subtotal
                if t.rate > 0:
                    t_amount = (subtotal - (subtotal / (Decimal("1.00") + (t.rate / Decimal("100.00"))))).quantize(Decimal("0.01"))

            tax_total += t_amount
            taxes_breakdown.append(
                TaxBreakdownItem(
                    name=t.name,
                    rate=float(t.rate),
                    amount=t_amount,
                )
            )
    else:
        # Default GST
        gst_amount = (subtotal * Decimal(str(settings.HOTEL_TAX_RATE))).quantize(Decimal("0.01"))
        tax_total = gst_amount
        taxes_breakdown.append(
            TaxBreakdownItem(
                name=f"GST ({int(settings.HOTEL_TAX_RATE * 100)}%)",
                rate=float(settings.HOTEL_TAX_RATE * 100),
                amount=gst_amount,
            )
        )

    grand_total = (subtotal + tax_total).quantize(Decimal("0.01"))

    # Compute deposit
    deposit_required = Decimal("0.00")
    if plan.requires_deposit:
        if plan.deposit_percent and plan.deposit_percent > 0:
            deposit_required = (grand_total * (plan.deposit_percent / Decimal("100.00"))).quantize(Decimal("0.01"))
        elif plan.deposit_fixed_amount and plan.deposit_fixed_amount > 0:
            deposit_required = min(plan.deposit_fixed_amount, grand_total).quantize(Decimal("0.01"))

    return RatePlanQuoteResponse(
        room_type_id=room_type.id,
        room_type_name=room_type.name,
        plan_id=plan.id,
        plan_code=plan.code,
        plan_name=plan.name,
        check_in_date=check_in,
        check_out_date=check_out,
        nights=nights,
        nightly_rates=nightly_rates,
        subtotal=subtotal,
        taxes=taxes_breakdown,
        tax_total=tax_total,
        grand_total=grand_total,
        min_stay_met=min_stay_met,
        min_stay_required=plan.min_stay,
        requires_deposit=plan.requires_deposit,
        deposit_required=deposit_required,
    )


@router.get("/{id}", response_model=RatePlanResponse)
def get_rate_plan(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single rate plan by ID."""
    plan = db.query(RatePlan).filter(RatePlan.id == id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rate plan #{id} not found.")
    return plan


@router.put("/{id}", response_model=RatePlanResponse)
def update_rate_plan(
    id: int,
    payload: RatePlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Update a rate plan (Admin/Manager only)."""
    plan = db.query(RatePlan).filter(RatePlan.id == id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rate plan #{id} not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(plan, k, v)

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rate_plan(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Delete a rate plan (Admin/Manager only)."""
    plan = db.query(RatePlan).filter(RatePlan.id == id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rate plan #{id} not found.")
    db.delete(plan)
    db.commit()
    return None
