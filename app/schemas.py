"""Pydantic V2 Request and Response Schemas."""
from datetime import datetime, date
from decimal import Decimal
import re
from typing import Any, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

T = TypeVar("T")


# ── Generic Envelopes ────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


# ── Auth & User Schemas ─────────────────────────────────────────────────────

class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., min_length=1)


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=10)
    role: str = Field("front_desk", pattern="^(owner|admin|manager|front_desk|housekeeping|accountant)$")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Password must be at least 10 characters long")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: Optional[int] = 1
    email: str
    username: str
    full_name: str
    role: str
    tour_completed: bool = False
    email_verified: bool = True
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    organization: Optional["OrganizationResponse"] = None


# ── Room & RoomType Schemas ─────────────────────────────────────────────────

class RoomTypeBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    base_rate: Decimal
    max_occupancy: int = 2


class RoomTypeResponse(RoomTypeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class RoomBase(BaseModel):
    number: str = Field(..., max_length=20)
    floor: int = Field(..., ge=1, le=100)
    room_type_id: int
    status: str = Field("available", pattern="^(available|occupied|dirty|cleaning|maintenance)$")
    notes: Optional[str] = None


class RoomCreate(RoomBase):
    model_config = ConfigDict(extra="forbid")


class RoomUpdateStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(..., pattern="^(available|occupied|dirty|cleaning|maintenance)$")
    notes: Optional[str] = None
    version: Optional[int] = None


class RoomUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: Optional[str] = Field(None, max_length=20)
    floor: Optional[int] = Field(None, ge=1, le=100)
    room_type_id: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(available|occupied|dirty|cleaning|maintenance)$")
    notes: Optional[str] = None
    version: Optional[int] = None


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    floor: int
    room_type_id: int
    status: str
    notes: Optional[str] = None
    version: int = 1
    is_demo: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    room_type: Optional[RoomTypeResponse] = None


class RoomDetailResponse(RoomResponse):
    current_guest: Optional[str] = None
    current_reservation_id: Optional[int] = None
    current_reservation_confirmation: Optional[str] = None
    current_balance: Optional[Decimal] = None
    current_total_charges: Optional[Decimal] = None
    current_total_payments: Optional[Decimal] = None
    current_check_in_date: Optional[date] = None
    current_check_out_date: Optional[date] = None
    next_arrival: Optional[str] = None
    next_arrival_date: Optional[date] = None


# ── Guest Schemas ───────────────────────────────────────────────────────────

class GuestBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=50)
    address: Optional[str] = None
    id_number: Optional[str] = None
    notes: Optional[str] = None


class GuestCreate(GuestBase):
    model_config = ConfigDict(extra="forbid")


class GuestUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=5, max_length=50)
    address: Optional[str] = None
    id_number: Optional[str] = None
    notes: Optional[str] = None


class GuestResponse(GuestBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    total_stays: int = 0
    total_spend: Decimal = Decimal("0.00")
    last_stay: Optional[date] = None
    created_at: datetime


class GuestBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: str


# ── Reservation Schemas ─────────────────────────────────────────────────────

class ReservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guest_id: int
    room_id: int
    rate_plan_id: Optional[int] = None
    group_id: Optional[int] = None
    check_in_date: date
    check_out_date: date
    adults: int = Field(1, ge=1, le=2, description="Maximum 2 adults per room")
    children: int = Field(0, ge=0, le=10)
    nightly_rate: Optional[Decimal] = None
    deposit_required: Optional[Decimal] = None
    advance_amount: Optional[Decimal] = Field(None, ge=0)
    advance_payment_method: Optional[str] = "cash"
    advance_payment_reference: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ReservationCreate":
        if self.check_out_date <= self.check_in_date:
            raise ValueError("Check-out date must be strictly after check-in date")
        return self


class WalkInCheckInRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    address: Optional[str] = None
    room_id: int
    rate_plan_id: Optional[int] = None
    check_in_date: Optional[date] = None
    check_out_date: date
    adults: int = Field(1, ge=1, le=2, description="Maximum 2 adults per room")
    children: int = Field(0, ge=0, le=10)
    nightly_rate: Optional[Decimal] = None
    auto_check_in: bool = True
    advance_amount: Optional[Decimal] = Field(None, ge=0)
    advance_payment_method: Optional[str] = "cash"
    advance_payment_reference: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "WalkInCheckInRequest":
        if self.check_in_date is not None and self.check_out_date <= self.check_in_date:
            raise ValueError("Check-out date must be strictly after check-in date")
        return self


class ReservationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    room_id: Optional[int] = None
    rate_plan_id: Optional[int] = None
    group_id: Optional[int] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    adults: Optional[int] = Field(None, ge=1, le=2, description="Maximum 2 adults per room")
    children: Optional[int] = Field(None, ge=0, le=10)
    nightly_rate: Optional[Decimal] = None
    notes: Optional[str] = None
    version: Optional[int] = None


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    confirmation_number: str
    guest_id: int
    room_id: int
    rate_plan_id: Optional[int] = None
    group_id: Optional[int] = None
    is_group_master: bool = False
    check_in_date: date
    check_out_date: date
    nights: int
    adults: int
    children: int
    nightly_rate: Decimal
    deposit_required: Decimal = Decimal("0.00")
    deposit_paid: Decimal = Decimal("0.00")
    deposit_due_at: Optional[date] = None
    status: str
    notes: Optional[str] = None
    version: int = 1
    is_demo: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    guest: Optional[GuestBrief] = None
    room: Optional[RoomResponse] = None
    rate_plan: Optional["RatePlanResponse"] = None
    balance: Decimal = Decimal("0.00")
    total_charges: Decimal = Decimal("0.00")
    total_payments: Decimal = Decimal("0.00")
    organization_id: Optional[int] = None
    hotel_name: Optional[str] = None


class DepositRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field("credit_card", pattern="^(credit_card|cash|bank_transfer|stripe|other)$")
    reference: Optional[str] = None


class DepositStatusResponse(BaseModel):
    reservation_id: int
    deposit_required: Decimal
    deposit_paid: Decimal
    deposit_due_at: Optional[date] = None
    is_satisfied: bool
    balance_due: Decimal


class CheckOutRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    settle_payment: bool = False
    payment_method: Optional[str] = "cash"
    reference: Optional[str] = None
    amount: Optional[Decimal] = None


# ── Folio & Billing Schemas ─────────────────────────────────────────────────

class FolioItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folio_id: Optional[int] = None
    date: date
    description: str = Field(..., min_length=2, max_length=255)
    category: str = Field(..., pattern="^(room|tax|minibar|restaurant|service|adjustment|deposit_applied|cancellation_fee)$")
    amount: Decimal  # can be negative for adjustment/credit
    subtotal: Optional[Decimal] = None
    tax_total: Optional[Decimal] = Decimal("0.00")
    tax_breakdown: Optional[str] = None


class FolioItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reservation_id: int
    folio_id: Optional[int] = None
    date: date
    description: str
    category: str
    amount: Decimal
    subtotal: Optional[Decimal] = None
    tax_total: Decimal = Decimal("0.00")
    tax_breakdown: Optional[str] = None
    created_at: datetime


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folio_id: Optional[int] = None
    date: date
    amount: Decimal = Field(..., description="Payment amount (must be positive unless is_refund=True)")
    method: str = Field(..., pattern="^(credit_card|cash|bank_transfer|stripe|refund|other)$")
    reference: Optional[str] = Field(None, max_length=100)
    is_deposit: bool = False
    is_refund: bool = False

    @model_validator(mode="after")
    def validate_payment_amount(self) -> "PaymentCreate":
        if self.is_refund:
            if self.amount >= 0:
                raise ValueError("Refund amount must be negative")
        else:
            if self.amount <= 0:
                raise ValueError("Payment amount must be strictly greater than zero")
        return self


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reservation_id: int
    folio_id: Optional[int] = None
    date: date
    amount: Decimal
    method: str
    reference: Optional[str] = None
    is_deposit: bool = False
    is_refund: bool = False
    stripe_payment_intent_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    created_at: datetime


class FolioDetailResponse(BaseModel):
    reservation_id: int
    confirmation_number: str
    guest: GuestBrief
    room_number: str
    room_type: str
    check_in_date: date
    check_out_date: date
    nights: int
    items: List[FolioItemResponse]
    payments: List[PaymentResponse]
    subtotal: Decimal
    tax_total: Decimal
    total_amount: Decimal
    total_paid: Decimal
    balance_due: Decimal


# ── Housekeeping Schemas ────────────────────────────────────────────────────

class HousekeepingTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    room_id: int
    task_type: str = Field(..., pattern="^(checkout_clean|stayover_clean|deep_clean|inspection|maintenance_repair)$")
    priority: str = Field("medium", pattern="^(low|medium|high|urgent)$")
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class HousekeepingTaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|done)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class HousekeepingTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    task_type: str
    status: str
    priority: str
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    room: Optional[RoomResponse] = None


# ── Dashboard & Activity Schemas ────────────────────────────────────────────

class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_type: str
    description: str
    actor: str
    created_at: datetime


class OccupancyTrendPoint(BaseModel):
    date: str
    occupancy_rate: float
    occupied_count: int
    total_rooms: int


class DashboardArrivalItem(BaseModel):
    reservation_id: int
    confirmation_number: str
    guest_name: str
    guest_id: int
    room_number: str
    room_type: str
    nights: int
    nightly_rate: Decimal
    status: str


class DashboardDepartureItem(BaseModel):
    reservation_id: int
    confirmation_number: str
    guest_name: str
    guest_id: int
    room_number: str
    nights: int
    balance: Decimal
    status: str


class DashboardResponse(BaseModel):
    occupancy_rate: float
    occupied_rooms: int
    total_rooms: int
    occupancy_sparkline: List[float]  # 7-day occupancy percentages

    arrivals_total: int
    arrivals_checked_in: int
    arrivals_remaining: int

    departures_total: int
    departures_checked_out: int
    departures_remaining: int

    revenue_today: Decimal
    revenue_trend_pct: float  # e.g. 12.0 for +12%

    occupancy_trend_14d: List[OccupancyTrendPoint]
    room_status_summary: dict  # available, occupied, dirty, cleaning, maintenance

    today_arrivals: List[DashboardArrivalItem]
    today_departures: List[DashboardDepartureItem]
    recent_activity: List[ActivityLogResponse]
    pending_housekeeping: List[HousekeepingTaskResponse]
    revenue_chart: Optional[dict] = None
    platform_breakdown: Optional[dict] = None


# ── Rate Plans & Cancellation Policies Schemas ──────────────────────────────

class CancellationPolicyBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    free_cancel_days: int = Field(1, ge=0)
    penalty_type: str = Field("first_night", pattern="^(none|first_night|percent|fixed)$")
    penalty_value: Decimal = Field(Decimal("0.00"), ge=0)
    no_show_penalty: str = Field("first_night", pattern="^(none|first_night|percent|fixed)$")
    no_show_value: Decimal = Field(Decimal("0.00"), ge=0)
    active: bool = True


class CancellationPolicyCreate(CancellationPolicyBase):
    model_config = ConfigDict(extra="forbid")


class CancellationPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    description: Optional[str] = None
    free_cancel_days: Optional[int] = None
    penalty_type: Optional[str] = Field(None, pattern="^(none|first_night|percent|fixed)$")
    penalty_value: Optional[Decimal] = None
    no_show_penalty: Optional[str] = Field(None, pattern="^(none|first_night|percent|fixed)$")
    no_show_value: Optional[Decimal] = None
    active: Optional[bool] = None


class CancellationPolicyResponse(CancellationPolicyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class CancellationQuoteResponse(BaseModel):
    reservation_id: int
    policy_name: str
    free_cancel_until: Optional[date] = None
    can_cancel_free: bool
    penalty_amount: Decimal
    deposit_paid: Decimal
    refund_amount: Decimal
    reason: str


class RatePlanBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    room_type_id: Optional[int] = None
    modifier_type: str = Field("percent", pattern="^(fixed|percent|absolute)$")
    modifier_value: Decimal = Decimal("0.00")
    meal_plan: str = Field("room_only", pattern="^(room_only|breakfast|half_board|full_board)$")
    min_stay: int = Field(1, ge=1)
    max_stay: Optional[int] = None
    cancellation_policy_id: Optional[int] = None
    refundable: bool = True
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    closed_to_arrival: bool = False
    closed_to_departure: bool = False
    active: bool = True
    requires_deposit: bool = False
    deposit_percent: Optional[Decimal] = None
    deposit_fixed_amount: Optional[Decimal] = None


class RatePlanCreate(RatePlanBase):
    model_config = ConfigDict(extra="forbid")


class RatePlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    description: Optional[str] = None
    room_type_id: Optional[int] = None
    modifier_type: Optional[str] = Field(None, pattern="^(fixed|percent|absolute)$")
    modifier_value: Optional[Decimal] = None
    meal_plan: Optional[str] = Field(None, pattern="^(room_only|breakfast|half_board|full_board)$")
    min_stay: Optional[int] = Field(None, ge=1)
    max_stay: Optional[int] = None
    cancellation_policy_id: Optional[int] = None
    refundable: Optional[bool] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    closed_to_arrival: Optional[bool] = None
    closed_to_departure: Optional[bool] = None
    active: Optional[bool] = None
    requires_deposit: Optional[bool] = None
    deposit_percent: Optional[Decimal] = None
    deposit_fixed_amount: Optional[Decimal] = None


class RatePlanResponse(RatePlanBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hotel_id: int
    created_at: datetime
    room_type: Optional[RoomTypeResponse] = None
    cancellation_policy: Optional[CancellationPolicyResponse] = None


ReservationResponse.model_rebuild()


class RateQuoteNightly(BaseModel):
    date: str
    base_rate: Decimal
    rate: Decimal


class TaxBreakdownItem(BaseModel):
    name: str
    rate: float
    amount: Decimal


class RatePlanQuoteResponse(BaseModel):
    room_type_id: int
    room_type_name: str
    plan_id: int
    plan_code: str
    plan_name: str
    check_in_date: date
    check_out_date: date
    nights: int
    nightly_rates: List[RateQuoteNightly]
    subtotal: Decimal
    taxes: List[TaxBreakdownItem]
    tax_total: Decimal
    grand_total: Decimal
    min_stay_met: bool
    min_stay_required: int
    requires_deposit: bool
    deposit_required: Decimal


# ── Tax Rate Schemas ────────────────────────────────────────────────────────

class TaxRateBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    rate: Decimal = Field(Decimal("0.00"), ge=0)
    fixed_amount: Decimal = Field(Decimal("0.00"), ge=0)
    applies_to: str = Field("rooms", pattern="^(rooms|extras|all)$")
    type: str = Field("exclusive", pattern="^(inclusive|exclusive)$")
    per: str = Field("night", pattern="^(night|stay|person_per_night)$")
    active: bool = True
    sort_order: int = 0


class TaxRateCreate(TaxRateBase):
    model_config = ConfigDict(extra="forbid")


class TaxRateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    rate: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    applies_to: Optional[str] = Field(None, pattern="^(rooms|extras|all)$")
    type: Optional[str] = Field(None, pattern="^(inclusive|exclusive)$")
    per: Optional[str] = Field(None, pattern="^(night|stay|person_per_night)$")
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class TaxRateResponse(TaxRateBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hotel_id: int
    created_at: datetime


# ── Rate Calendar & Overrides Schemas ───────────────────────────────────────

class RateOverrideCreate(BaseModel):
    room_type_id: int
    date: date
    rate: Decimal = Field(..., gt=0)
    min_stay: Optional[int] = None
    closed: bool = False
    closed_to_arrival: bool = False
    closed_to_departure: bool = False


class RateOverrideBulkCreate(BaseModel):
    room_type_ids: List[int]
    dates: List[date]
    rate: Optional[Decimal] = None
    min_stay: Optional[int] = None
    closed: Optional[bool] = None
    closed_to_arrival: Optional[bool] = None
    closed_to_departure: Optional[bool] = None


class RateOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_type_id: int
    date: date
    rate: Decimal
    min_stay: Optional[int] = None
    closed: bool
    closed_to_arrival: bool
    closed_to_departure: bool
    created_at: datetime


class RateCalendarDayItem(BaseModel):
    date: str
    rate: Decimal
    base_rate: Decimal
    occupancy_pct: float
    occupied_count: int
    available_count: int
    total_rooms: int
    override_id: Optional[int] = None
    closed: bool = False
    closed_to_arrival: bool = False
    closed_to_departure: bool = False
    min_stay: Optional[int] = None


class RateCalendarRoomTypeItem(BaseModel):
    id: int
    name: str
    code: str
    room_count: int
    base_rate: Decimal
    days: List[RateCalendarDayItem]


class RateCalendarResponse(BaseModel):
    start_date: str
    days_count: int
    room_types: List[RateCalendarRoomTypeItem]


# ── Timeline & Gantt Schemas ────────────────────────────────────────────────

class TimelineReservationItem(BaseModel):
    id: int
    confirmation_number: str
    guest_name: str
    guest_initials: str
    check_in_date: str
    check_out_date: str
    nights: int
    nightly_rate: Decimal
    status: str
    adults: int
    children: int
    balance: Decimal


class TimelineRoomItem(BaseModel):
    id: int
    number: str
    floor: int
    room_type_name: str
    room_type_code: str
    status: str
    reservations: List[TimelineReservationItem]


class TimelineResponse(BaseModel):
    start_date: str
    days_count: int
    rooms: List[TimelineRoomItem]


class ReservationMoveRequest(BaseModel):
    room_id: Optional[int] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    version: Optional[int] = None


# ── Folio Split & Transfer Schemas ──────────────────────────────────────────

class FolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class FolioUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class FolioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reservation_id: int
    name: str
    is_master: bool
    created_at: datetime
    items: List[FolioItemResponse] = []
    total_amount: Decimal = Decimal("0.00")
    total_paid: Decimal = Decimal("0.00")
    balance_due: Decimal = Decimal("0.00")


class FolioItemMoveRequest(BaseModel):
    folio_id: int


class FolioItemBulkMoveRequest(BaseModel):
    item_ids: List[int]
    folio_id: int


class FolioTransferRequest(BaseModel):
    to_folio_id: int


# ── Group Booking Schemas ───────────────────────────────────────────────────

class GroupBlockCreate(BaseModel):
    room_type_id: int
    count: int = Field(..., ge=1)
    rate: Decimal = Field(..., ge=0)


class GroupBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    group_id: int
    room_type_id: int
    room_type_name: Optional[str] = None
    count: int
    rate: Decimal
    picked_up_count: int = 0
    available_to_pick: int = 0


class BookingGroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    contact_name: str = Field(..., min_length=2, max_length=100)
    contact_email: EmailStr
    contact_phone: str = Field(..., min_length=5, max_length=50)
    check_in: date
    check_out: date
    cutoff_date: date
    notes: Optional[str] = None
    room_blocks: List[GroupBlockCreate] = []

    @model_validator(mode="after")
    def validate_group_dates(self) -> "BookingGroupCreate":
        if self.check_out <= self.check_in:
            raise ValueError("Check-out must be after check-in")
        if self.cutoff_date > self.check_in:
            raise ValueError("Cutoff date cannot be after check-in date")
        return self


class BookingGroupUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    cutoff_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(tentative|confirmed|cancelled)$")
    notes: Optional[str] = None


class BookingGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hotel_id: int
    name: str
    contact_name: str
    contact_email: str
    contact_phone: str
    check_in: date
    check_out: date
    cutoff_date: date
    status: str
    notes: Optional[str] = None
    created_at: datetime
    rooms_blocked_total: int = 0
    rooms_picked_up_total: int = 0
    room_blocks: List[GroupBlockResponse] = []


class GroupDetailResponse(BookingGroupResponse):
    reservations: List[ReservationResponse] = []
    master_folio_total: Decimal = Decimal("0.00")
    master_folio_paid: Decimal = Decimal("0.00")
    master_folio_balance: Decimal = Decimal("0.00")


# ── Night Audit & Business Date Schemas ─────────────────────────────────────

class BusinessDateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hotel_id: int
    date: date
    status: str
    closed_at: Optional[datetime] = None


class NightAuditPreviewResponse(BaseModel):
    business_date: date
    next_business_date: date
    checked_in_reservations_count: int
    room_charges_to_post_count: int
    room_charges_estimated_total: Decimal
    no_shows_count: int
    no_show_estimated_penalties: Decimal
    unresolved_departures_count: int
    can_run_without_force: bool
    warning_message: Optional[str] = None


class NightAuditRunRequest(BaseModel):
    force: bool = False


class DailySnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    business_date: date
    occupancy_rate: Decimal
    adr: Decimal
    revpar: Decimal
    arrivals: int
    departures: int
    room_revenue: Decimal
    total_revenue: Decimal
    tax_collected: Decimal
    created_at: datetime


class NightAuditRunResponse(BaseModel):
    success: bool
    previous_business_date: date
    new_business_date: date
    room_charges_posted: int
    room_charges_total: Decimal
    no_shows_marked: int
    no_show_penalties_total: Decimal
    snapshot: DailySnapshotResponse


# ── Payment Intent & Stripe Schemas ─────────────────────────────────────────

class PaymentIntentCreateRequest(BaseModel):
    reservation_id: int
    amount: Decimal = Field(..., gt=0)
    folio_id: Optional[int] = None


class PaymentIntentResponse(BaseModel):
    client_secret: Optional[str] = None
    payment_intent_id: str
    publishable_key: Optional[str] = None
    amount: Decimal
    currency: str
    manual_mode: bool = False


class PaymentRefundRequest(BaseModel):
    amount: Optional[Decimal] = None  # None = full refund
    reason: Optional[str] = "Customer requested refund"


# ── Organization & Multi-Tenancy Schemas ─────────────────────────────────────

class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    owner_user_id: Optional[int] = None
    plan: str
    trial_ends_at: Optional[datetime] = None
    subscription_status: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None
    timezone: str
    currency: str
    address: Optional[str] = None
    tax_id: Optional[str] = None
    created_at: datetime


class OrganizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None


class OrgUsageStats(BaseModel):
    rooms: dict
    users: dict
    reservations_this_month: int


class OrgMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    organization_id: int
    role: str
    created_at: datetime
    user: Optional[UserResponse] = None


class UserOrgInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    role: str = Field("front_desk", pattern="^(owner|admin|manager|front_desk|housekeeping|accountant)$")
    full_name: Optional[str] = None


# ── Signup & Onboarding Schemas ──────────────────────────────────────────────

class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    hotel_name: str = Field(..., min_length=2, max_length=150)
    timezone: Optional[str] = "Asia/Kolkata"
    currency: Optional[str] = "INR"
    plan: Optional[str] = "pro"
    property_type: Optional[str] = None
    rooms_count: Optional[Union[int, str]] = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=10)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Password must be at least 10 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=10)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Password must be at least 10 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


# ── Subscriptions & Billing Schemas ──────────────────────────────────────────

class CheckoutSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: str = Field(..., pattern="^(starter|pro|enterprise)$")


class BillingStatusResponse(BaseModel):
    plan: str
    status: str
    trial_ends_at: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    days_left: int = 0
    usage: OrgUsageStats


# ── Email Templates Schemas ──────────────────────────────────────────────────

class EmailTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    name: str
    subject: str
    body: str
    variables_hint: Optional[str] = None
    updated_at: Optional[datetime] = None


class EmailTemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: Optional[str] = None
    body: Optional[str] = None


# ── Backup & Export Schemas ──────────────────────────────────────────────────

class BackupRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    s3_key: str
    size_bytes: int
    status: str
    created_at: datetime


class ExportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# ── Audit Log Schemas ────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    before_json: Optional[str] = None
    after_json: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


# ── CSV Import Schemas ───────────────────────────────────────────────────────

class ImportPreviewResponse(BaseModel):
    type: str
    total_rows: int
    valid_rows: int
    error_rows: int
    preview_items: List[dict]
    errors: List[dict]


class ImportExecuteRequest(BaseModel):
    type: str = Field(..., pattern="^(guests|rooms)$")
    rows: List[dict]


class ImportExecuteResponse(BaseModel):
    imported: int
    skipped: int
    errors: List[dict]


# ── Onboarding Customization Schemas ─────────────────────────────────────────

class OnboardingRoomType(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    base_rate: Decimal = Field(..., ge=0)
    max_occupancy: int = Field(2, ge=1, le=20)
    description: Optional[str] = None
    code: Optional[str] = None


class OnboardingRoom(BaseModel):
    number: str = Field(..., min_length=1, max_length=20)
    floor: int = Field(1, ge=0, le=100)
    room_type_name: str = Field(..., min_length=1)


class OnboardingRatePlan(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    modifier_type: str = Field("percent", pattern="^(percent|absolute)$")
    modifier_value: Decimal = Field(Decimal("0.00"))
    description: Optional[str] = None
    refundable: bool = True


class OnboardingTaxRate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: Decimal = Field(Decimal("12.00"), ge=0, le=100)
    applies_to: str = Field("rooms", pattern="^(rooms|extras|all)$")
    description: Optional[str] = None


class OnboardingStaff(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = "front_desk"


class OnboardingSaveRequest(BaseModel):
    hotel_name: Optional[str] = None
    city: Optional[str] = None
    currency: Optional[str] = "INR"
    gstin: Optional[str] = None
    room_types: Optional[List[OnboardingRoomType]] = None
    rooms: Optional[List[OnboardingRoom]] = None
    rate_plans: Optional[List[OnboardingRatePlan]] = None
    taxes: Optional[List[OnboardingTaxRate]] = None
    staff: Optional[OnboardingStaff] = None
    staff_members: Optional[List[OnboardingStaff]] = None


TokenResponse.model_rebuild()


