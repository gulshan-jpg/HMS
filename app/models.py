"""SQLAlchemy ORM Models for Hotel PMS - Commercial Multi-Tenant B2B SaaS."""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Date,
    DateTime,
    Numeric,
    Text,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    plan = Column(String(50), default="starter", nullable=False)  # starter, pro, enterprise
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    subscription_status = Column(String(50), default="trialing", nullable=False)  # trialing, active, past_due, cancelled, locked
    stripe_customer_id = Column(String(100), nullable=True)
    stripe_subscription_id = Column(String(100), nullable=True)
    logo_url = Column(String(255), nullable=True)
    brand_color = Column(String(20), nullable=True)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    address = Column(Text, nullable=True)
    tax_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    memberships = relationship("UserOrgMembership", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), default=1, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="front_desk", nullable=False)  # owner, manager, front_desk, housekeeping, accountant
    tour_completed = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=True, nullable=False)
    verification_token = Column(String(100), nullable=True)
    reset_token = Column(String(100), nullable=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    memberships = relationship("UserOrgMembership", back_populates="user", cascade="all, delete-orphan")


class UserOrgMembership(Base):
    __tablename__ = "user_org_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), default="front_desk", nullable=False)  # owner, manager, front_desk, housekeeping, accountant
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
    )

    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")


class CancellationPolicy(Base):
    __tablename__ = "cancellation_policies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    free_cancel_days = Column(Integer, default=1, nullable=False)
    penalty_type = Column(String(30), default="first_night", nullable=False)  # none, first_night, percent, fixed
    penalty_value = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    no_show_penalty = Column(String(30), default="first_night", nullable=False)  # none, first_night, percent, fixed
    no_show_value = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rate_plans = relationship("RatePlan", back_populates="cancellation_policy")


class RoomType(Base):
    __tablename__ = "room_types"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    name = Column(String(100), nullable=False)  # Standard Queen, Deluxe King, Executive Suite
    code = Column(String(20), index=True, nullable=False)  # STD-Q, DLX-K, EXE-S
    description = Column(Text, nullable=True)
    base_rate = Column(Numeric(10, 2), nullable=False)
    max_occupancy = Column(Integer, default=2, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_room_type_org_code"),
    )

    rooms = relationship("Room", back_populates="room_type", cascade="all")
    rate_overrides = relationship("RateOverride", back_populates="room_type", cascade="all, delete-orphan")


class RatePlan(Base):
    __tablename__ = "rate_plans"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    hotel_id = Column(Integer, default=1, nullable=False)
    code = Column(String(20), index=True, nullable=False)  # FLEX, NR, BB, LONG
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="SET NULL"), nullable=True)
    modifier_type = Column(String(20), default="percent", nullable=False)  # fixed, percent, absolute
    modifier_value = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    meal_plan = Column(String(30), default="room_only", nullable=False)  # room_only, breakfast, half_board, full_board
    min_stay = Column(Integer, default=1, nullable=False)
    max_stay = Column(Integer, nullable=True)
    cancellation_policy_id = Column(Integer, ForeignKey("cancellation_policies.id", ondelete="SET NULL"), nullable=True)
    refundable = Column(Boolean, default=True, nullable=False)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    closed_to_arrival = Column(Boolean, default=False, nullable=False)
    closed_to_departure = Column(Boolean, default=False, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    requires_deposit = Column(Boolean, default=False, nullable=False)
    deposit_percent = Column(Numeric(5, 2), nullable=True)
    deposit_fixed_amount = Column(Numeric(10, 2), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    room_type = relationship("RoomType")
    cancellation_policy = relationship("CancellationPolicy", back_populates="rate_plans")
    reservations = relationship("Reservation", back_populates="rate_plan")


class TaxRate(Base):
    __tablename__ = "tax_rates"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    hotel_id = Column(Integer, default=1, nullable=False)
    name = Column(String(100), nullable=False)  # City Tax, Tourism Tax, GST
    rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)  # percent e.g. 3.00, 12.00
    fixed_amount = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # fixed e.g. $2.00 / ₹150
    applies_to = Column(String(30), default="rooms", nullable=False)  # rooms, extras, all
    type = Column(String(20), default="exclusive", nullable=False)  # inclusive, exclusive
    per = Column(String(30), default="night", nullable=False)  # night, stay, person_per_night
    active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RateOverride(Base):
    __tablename__ = "rate_overrides"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    rate = Column(Numeric(10, 2), nullable=False)
    min_stay = Column(Integer, nullable=True)
    closed = Column(Boolean, default=False, nullable=False)
    closed_to_arrival = Column(Boolean, default=False, nullable=False)
    closed_to_departure = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("room_type_id", "date", name="uq_rate_override_room_type_date"),
    )

    room_type = relationship("RoomType", back_populates="rate_overrides")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    number = Column(String(20), index=True, nullable=False)
    floor = Column(Integer, nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(30), default="available", nullable=False)  # available, occupied, dirty, cleaning, maintenance
    notes = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "number", name="uq_room_org_number"),
    )

    room_type = relationship("RoomType", back_populates="rooms")
    reservations = relationship("Reservation", back_populates="room")
    housekeeping_tasks = relationship("HousekeepingTask", back_populates="room")


class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), index=True, nullable=False)
    phone = Column(String(50), nullable=False)
    address = Column(Text, nullable=True)
    id_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reservations = relationship("Reservation", back_populates="guest")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class BookingGroup(Base):
    __tablename__ = "booking_groups"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    hotel_id = Column(Integer, default=1, nullable=False)
    name = Column(String(150), nullable=False)  # e.g. Webb Corporate Retreat, Sharma Wedding
    contact_name = Column(String(100), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(50), nullable=False)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    cutoff_date = Column(Date, nullable=False)
    status = Column(String(30), default="tentative", nullable=False)  # tentative, confirmed, cancelled
    notes = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    room_blocks = relationship("GroupBlock", back_populates="group", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="group")


class GroupBlock(Base):
    __tablename__ = "group_blocks"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    group_id = Column(Integer, ForeignKey("booking_groups.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="RESTRICT"), nullable=False)
    count = Column(Integer, nullable=False)
    rate = Column(Numeric(10, 2), nullable=False)

    group = relationship("BookingGroup", back_populates="room_blocks")
    room_type = relationship("RoomType")


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    confirmation_number = Column(String(30), unique=True, index=True, nullable=False)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="RESTRICT"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False)
    rate_plan_id = Column(Integer, ForeignKey("rate_plans.id", ondelete="SET NULL"), nullable=True)
    group_id = Column(Integer, ForeignKey("booking_groups.id", ondelete="SET NULL"), nullable=True)
    is_group_master = Column(Boolean, default=False, nullable=False)
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    adults = Column(Integer, default=1, nullable=False)
    children = Column(Integer, default=0, nullable=False)
    nightly_rate = Column(Numeric(10, 2), nullable=False)
    status = Column(String(30), default="booked", nullable=False)  # booked, checked_in, checked_out, cancelled, no_show
    deposit_required = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    deposit_paid = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    deposit_due_at = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("check_out_date > check_in_date", name="chk_reservation_dates"),
    )

    guest = relationship("Guest", back_populates="reservations")
    room = relationship("Room", back_populates="reservations")
    rate_plan = relationship("RatePlan", back_populates="reservations")
    group = relationship("BookingGroup", back_populates="reservations")
    folios = relationship("Folio", back_populates="reservation", cascade="all, delete-orphan")
    folio_items = relationship("FolioItem", back_populates="reservation", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="reservation", cascade="all, delete-orphan")

    @property
    def nights(self) -> int:
        if self.check_out_date and self.check_in_date:
            return (self.check_out_date - self.check_in_date).days
        return 0


class Folio(Base):
    __tablename__ = "folios"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), default="Primary", nullable=False)
    is_master = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reservation = relationship("Reservation", back_populates="folios")
    items = relationship("FolioItem", back_populates="folio", cascade="all, delete-orphan")


class FolioItem(Base):
    __tablename__ = "folio_items"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False)
    folio_id = Column(Integer, ForeignKey("folios.id", ondelete="CASCADE"), nullable=True)
    date = Column(Date, nullable=False)
    description = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # room, tax, minibar, restaurant, service, adjustment, deposit_applied, cancellation_fee
    amount = Column(Numeric(10, 2), nullable=False)  # can be negative for credits/deposits
    subtotal = Column(Numeric(10, 2), nullable=True)
    tax_total = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    tax_breakdown = Column(Text, nullable=True)  # JSON string
    version = Column(Integer, default=1, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reservation = relationship("Reservation", back_populates="folio_items")
    folio = relationship("Folio", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False)
    folio_id = Column(Integer, ForeignKey("folios.id", ondelete="SET NULL"), nullable=True)
    date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)  # negative for refunds
    method = Column(String(50), nullable=False)  # credit_card, cash, bank_transfer, stripe, other, refund
    reference = Column(String(100), nullable=True)
    is_deposit = Column(Boolean, default=False, nullable=False)
    is_refund = Column(Boolean, default=False, nullable=False)
    stripe_payment_intent_id = Column(String(100), nullable=True)
    stripe_charge_id = Column(String(100), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("amount != 0", name="chk_payment_amount_nonzero"),
    )

    reservation = relationship("Reservation", back_populates="payments")


class BusinessDate(Base):
    __tablename__ = "business_dates"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    hotel_id = Column(Integer, default=1, nullable=False)
    date = Column(Date, nullable=False, index=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="open", nullable=False)  # open, closed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    closed_by_user = relationship("User")


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    hotel_id = Column(Integer, default=1, nullable=False)
    business_date = Column(Date, nullable=False, index=True)
    occupancy_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    adr = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    revpar = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    arrivals = Column(Integer, default=0, nullable=False)
    departures = Column(Integer, default=0, nullable=False)
    room_revenue = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    total_revenue = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    tax_collected = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(100), primary_key=True)  # Stripe event ID
    event_type = Column(String(100), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class HousekeepingTask(Base):
    __tablename__ = "housekeeping_tasks"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False)
    task_type = Column(String(50), nullable=False)  # checkout_clean, stayover_clean, deep_clean, inspection, maintenance_repair
    status = Column(String(30), default="pending", nullable=False)  # pending, in_progress, done
    priority = Column(String(20), default="medium", nullable=False)  # low, medium, high, urgent
    assigned_to = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    token = Column(String(100), unique=True, index=True, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    room = relationship("Room", back_populates="housekeeping_tasks")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    event_type = Column(String(50), nullable=False)  # check_in, check_out, payment, charge, room_status, reservation_created, reservation_cancelled, task_completed
    description = Column(String(255), nullable=False)
    actor = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    key = Column(String(50), nullable=False)  # guest_booking_confirmation, guest_pre_arrival, guest_invoice, guest_post_stay, staff_invite, staff_password_reset, owner_trial_reminder, owner_payment_failed
    name = Column(String(100), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    variables_hint = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("organization_id", "key", name="uq_email_template_org_key"),
    )


class InvoiceLog(Base):
    __tablename__ = "invoice_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False)
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)  # {org_slug}-{year}-{seq:06d}
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by = Column(String(100), nullable=False)
    pdf_path = Column(String(255), nullable=True)


class BackupRecord(Base):
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    s3_key = Column(String(255), nullable=False)
    size_bytes = Column(Integer, default=0, nullable=False)
    status = Column(String(30), default="completed", nullable=False)  # completed, failed, running
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(String(50), primary_key=True)  # uuid string
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), default="pending", nullable=False)  # pending, processing, completed, failed
    file_path = Column(String(255), nullable=True)
    s3_key = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), default=1, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, RESTORE
    entity_type = Column(String(50), nullable=False)  # reservation, guest, room, folio_item, payment, user, rate_plan
    entity_id = Column(Integer, nullable=True)
    before_json = Column(Text, nullable=True)
    after_json = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    hotel_name = Column(String(255), nullable=False)
    property_type = Column(String(50), default="boutique", nullable=False)
    rooms_count = Column(String(50), default="16-50", nullable=False)
    city = Column(String(150), nullable=True)
    preferred_slot = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, contacted, scheduled, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

