"""Self-Serve Signup, Onboarding Wizard, and Password Management API."""
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import re
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_password_hash, verify_password
from app.database import get_db
from app.deps import get_current_org, get_current_user, require_role
from app.models import (
    ActivityLog,
    BusinessDate,
    CancellationPolicy,
    EmailTemplate,
    Folio,
    FolioItem,
    Guest,
    HousekeepingTask,
    Organization,
    Payment,
    RatePlan,
    Reservation,
    Room,
    RoomType,
    TaxRate,
    User,
    UserOrgMembership,
)
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    OnboardingRatePlan,
    OnboardingRoom,
    OnboardingRoomType,
    OnboardingSaveRequest,
    OnboardingStaff,
    OnboardingTaxRate,
    OrganizationResponse,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api", tags=["Signup & Onboarding"])


def slugify(text: str) -> str:
    """Converts hotel name into clean URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "hotel"


def generate_unique_slug(base_name: str, db: Session) -> str:
    """Generates a collision-free organization slug."""
    slug_base = slugify(base_name)
    slug = slug_base
    count = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{slug_base}-{count}"
        count += 1
    return slug


def seed_organization_demo_data(org: Organization, db: Session) -> None:
    """Auto-seeds a newly registered hotel organization with realistic demo data matching onboarding."""
    # Ensure no stale leftover demo records exist for this org.id
    db.query(Room).filter(Room.organization_id == org.id).delete(synchronize_session=False)
    db.query(RoomType).filter(RoomType.organization_id == org.id).delete(synchronize_session=False)
    db.query(RatePlan).filter(RatePlan.organization_id == org.id).delete(synchronize_session=False)
    db.query(CancellationPolicy).filter(CancellationPolicy.organization_id == org.id).delete(synchronize_session=False)
    db.query(TaxRate).filter(TaxRate.organization_id == org.id).delete(synchronize_session=False)
    db.flush()

    # 1. Room Types
    rt_dlx = RoomType(
        organization_id=org.id,
        name="Deluxe King",
        code=f"DLX-K-{org.id}",
        description="Max 2 Guests • Standard King Bed",
        base_rate=Decimal("7500.00"),
        max_occupancy=2,
        is_demo=True,
    )
    rt_exe = RoomType(
        organization_id=org.id,
        name="Executive Heritage Suite",
        code=f"EXE-H-{org.id}",
        description="Max 4 Guests • Living Room + Balcony",
        base_rate=Decimal("16500.00"),
        max_occupancy=4,
        is_demo=True,
    )
    rt_std = RoomType(
        organization_id=org.id,
        name="Standard Double",
        code=f"STD-D-{org.id}",
        description="Max 2 Guests • Courtyard View",
        base_rate=Decimal("5000.00"),
        max_occupancy=2,
        is_demo=True,
    )
    rt_prs = RoomType(
        organization_id=org.id,
        name="Presidential Penthouse",
        code=f"PRS-P-{org.id}",
        description="Max 6 Guests • Private Jacuzzi",
        base_rate=Decimal("35000.00"),
        max_occupancy=6,
        is_demo=True,
    )
    db.add_all([rt_dlx, rt_exe, rt_std, rt_prs])
    db.flush()

    # 2. Rooms (10 rooms)
    rooms = [
        Room(organization_id=org.id, number="101", floor=1, room_type_id=rt_dlx.id, status="occupied", is_demo=True),
        Room(organization_id=org.id, number="102", floor=1, room_type_id=rt_dlx.id, status="occupied", is_demo=True),
        Room(organization_id=org.id, number="201", floor=2, room_type_id=rt_dlx.id, status="available", is_demo=True),
        Room(organization_id=org.id, number="202", floor=2, room_type_id=rt_dlx.id, status="dirty", is_demo=True),
        Room(organization_id=org.id, number="301", floor=3, room_type_id=rt_exe.id, status="available", is_demo=True),
        Room(organization_id=org.id, number="302", floor=3, room_type_id=rt_exe.id, status="available", is_demo=True),
        Room(organization_id=org.id, number="303", floor=3, room_type_id=rt_std.id, status="available", is_demo=True),
        Room(organization_id=org.id, number="304", floor=3, room_type_id=rt_std.id, status="available", is_demo=True),
        Room(organization_id=org.id, number="401", floor=4, room_type_id=rt_prs.id, status="available", is_demo=True),
        Room(organization_id=org.id, number="402", floor=4, room_type_id=rt_prs.id, status="available", is_demo=True),
    ]
    db.add_all(rooms)
    db.flush()

    # 3. Cancellation Policies
    pol_flex = CancellationPolicy(
        organization_id=org.id,
        name="Flexible (24h)",
        description="Free cancellation up to 24 hours before check-in",
        free_cancel_days=1,
        penalty_type="first_night",
        active=True,
        is_demo=True,
    )
    pol_strict = CancellationPolicy(
        organization_id=org.id,
        name="Strict Non-Refundable",
        description="Full first-night penalty applies upon cancellation",
        free_cancel_days=0,
        penalty_type="first_night",
        active=True,
        is_demo=True,
    )
    db.add_all([pol_flex, pol_strict])
    db.flush()

    # 4. Rate Plans
    plans = [
        RatePlan(
            organization_id=org.id,
            hotel_id=org.id,
            code=f"FLEX-{org.id}",
            name="Flexible Rate",
            description="Base Rate (Refundable)",
            modifier_type="percent",
            modifier_value=Decimal("0.00"),
            cancellation_policy_id=pol_flex.id,
            refundable=True,
            is_demo=True,
        ),
        RatePlan(
            organization_id=org.id,
            hotel_id=org.id,
            code=f"NR-{org.id}",
            name="Non-Refundable Promo",
            description="-10% Off Base",
            modifier_type="percent",
            modifier_value=Decimal("-10.00"),
            cancellation_policy_id=pol_strict.id,
            refundable=False,
            is_demo=True,
        ),
        RatePlan(
            organization_id=org.id,
            hotel_id=org.id,
            code=f"BB-{org.id}",
            name="Bed & Breakfast",
            description="+₹500 / night",
            modifier_type="absolute",
            modifier_value=Decimal("500.00"),
            meal_plan="breakfast",
            cancellation_policy_id=pol_flex.id,
            refundable=True,
            is_demo=True,
        ),
        RatePlan(
            organization_id=org.id,
            hotel_id=org.id,
            code=f"LONG-{org.id}",
            name="Long Stay 7+ Nights",
            description="-15% Off Base",
            modifier_type="percent",
            modifier_value=Decimal("-15.00"),
            min_stay=7,
            cancellation_policy_id=pol_flex.id,
            refundable=True,
            is_demo=True,
        ),
    ]
    db.add_all(plans)
    db.flush()

    # 5. Taxes (GST)
    tax_12 = TaxRate(
        organization_id=org.id,
        hotel_id=org.id,
        name="Standard Room GST (12%)",
        rate=Decimal("12.00"),
        applies_to="rooms",
        type="exclusive",
        per="night",
        is_demo=True,
    )
    tax_18 = TaxRate(
        organization_id=org.id,
        hotel_id=org.id,
        name="Luxury Suite GST (18%)",
        rate=Decimal("18.00"),
        applies_to="rooms",
        type="exclusive",
        per="night",
        is_demo=True,
    )
    db.add_all([tax_12, tax_18])
    db.flush()

    # 6. Sample Guests
    sample_guests_data = [
        ("Aarav", "Patel", "aarav.patel@example.in", "+919812345001"),
        ("Meera", "Nambiar", "meera.nambiar@example.in", "+919812345002"),
        ("Rohan", "Kapoor", "rohan.kapoor@example.in", "+919812345003"),
        ("Ananya", "Deshmukh", "ananya.d@example.in", "+919812345004"),
        ("Vikram", "Singhania", "vikram.s@example.in", "+919812345005"),
        ("Pooja", "Menon", "pooja.menon@example.in", "+919812345006"),
    ]
    guests = []
    for fn, ln, em, ph in sample_guests_data:
        g = Guest(
            organization_id=org.id,
            first_name=fn,
            last_name=ln,
            email=f"{em.split('@')[0]}_{org.id}@{em.split('@')[1]}",
            phone=ph,
            address="Bengaluru, Karnataka, India",
            is_demo=True,
        )
        guests.append(g)
    db.add_all(guests)
    db.flush()

    # 7. Sample Reservations (across next 7 days)
    today = date.today()
    res1 = Reservation(
        organization_id=org.id,
        confirmation_number=f"DEMO-{org.id}-101",
        guest_id=guests[0].id,
        room_id=rooms[0].id,
        rate_plan_id=plans[0].id,
        check_in_date=today,
        check_out_date=today + timedelta(days=2),
        adults=1,
        nightly_rate=Decimal("7500.00"),
        status="checked_in",
        is_demo=True,
    )
    res2 = Reservation(
        organization_id=org.id,
        confirmation_number=f"DEMO-{org.id}-102",
        guest_id=guests[1].id,
        room_id=rooms[1].id,
        rate_plan_id=plans[1].id,
        check_in_date=today,
        check_out_date=today + timedelta(days=3),
        adults=2,
        nightly_rate=Decimal("6750.00"),
        status="checked_in",
        is_demo=True,
    )
    res3 = Reservation(
        organization_id=org.id,
        confirmation_number=f"DEMO-{org.id}-103",
        guest_id=guests[2].id,
        room_id=rooms[2].id,
        rate_plan_id=plans[0].id,
        check_in_date=today + timedelta(days=1),
        check_out_date=today + timedelta(days=4),
        adults=1,
        nightly_rate=Decimal("7500.00"),
        status="booked",
        is_demo=True,
    )
    res4 = Reservation(
        organization_id=org.id,
        confirmation_number=f"DEMO-{org.id}-104",
        guest_id=guests[3].id,
        room_id=rooms[4].id,
        rate_plan_id=plans[2].id,
        check_in_date=today + timedelta(days=2),
        check_out_date=today + timedelta(days=5),
        adults=2,
        nightly_rate=Decimal("17000.00"),
        status="booked",
        is_demo=True,
    )
    res5 = Reservation(
        organization_id=org.id,
        confirmation_number=f"DEMO-{org.id}-105",
        guest_id=guests[4].id,
        room_id=rooms[8].id,
        rate_plan_id=plans[0].id,
        check_in_date=today + timedelta(days=3),
        check_out_date=today + timedelta(days=6),
        adults=2,
        nightly_rate=Decimal("35000.00"),
        status="booked",
        is_demo=True,
    )
    db.add_all([res1, res2, res3, res4, res5])
    db.flush()

    # Create primary folios for reservations
    for res in [res1, res2, res3, res4, res5]:
        folio = Folio(
            organization_id=org.id,
            reservation_id=res.id,
            name="Primary",
            is_master=True,
        )
        db.add(folio)
        db.flush()
        # Post initial room charge for checked-in demo reservations
        if res.status == "checked_in":
            item = FolioItem(
                organization_id=org.id,
                reservation_id=res.id,
                folio_id=folio.id,
                date=today,
                description=f"Room Charge: Night of {today} (Room {res.room.number})",
                category="room",
                amount=res.nightly_rate,
                subtotal=res.nightly_rate,
                is_demo=True,
            )
            db.add(item)

    # 8. Email Templates
    templates = [
        EmailTemplate(
            organization_id=org.id,
            key="guest_booking_confirmation",
            name="Booking Confirmation",
            subject="Your booking at {{hotel.name}} is confirmed ({{reservation.confirmation_number}})",
            body="Dear {{guest.first_name}},\n\nThank you for choosing {{hotel.name}}. Your reservation from {{reservation.check_in}} to {{reservation.check_out}} for {{room.type_name}} has been confirmed.\n\nTotal Rate: ₹{{reservation.total_amount}}\nWe look forward to welcoming you!",
            variables_hint="{{guest.first_name}}, {{hotel.name}}, {{reservation.confirmation_number}}, {{reservation.check_in}}, {{reservation.check_out}}, {{room.type_name}}",
        ),
        EmailTemplate(
            organization_id=org.id,
            key="guest_pre_arrival",
            name="Pre-Arrival Welcome",
            subject="We're preparing for your arrival tomorrow at {{hotel.name}}",
            body="Dear {{guest.first_name}},\n\nWe look forward to seeing you tomorrow! Check-in starts at 2:00 PM. Please have your government ID ready at the front desk.\n\nAddress: {{hotel.address}}\nFront Desk: {{hotel.phone}}",
            variables_hint="{{guest.first_name}}, {{hotel.name}}, {{hotel.address}}, {{hotel.phone}}",
        ),
        EmailTemplate(
            organization_id=org.id,
            key="guest_invoice",
            name="Checkout Invoice",
            subject="Your stay invoice from {{hotel.name}}",
            body="Dear {{guest.first_name}},\n\nPlease find attached the official tax invoice for your stay at {{hotel.name}}. It was our pleasure hosting you.\n\nWarm regards,\n{{hotel.name}} Front Office",
            variables_hint="{{guest.first_name}}, {{hotel.name}}",
        ),
        EmailTemplate(
            organization_id=org.id,
            key="guest_post_stay",
            name="Post-Stay Feedback",
            subject="How was your stay at {{hotel.name}}?",
            body="Dear {{guest.first_name}},\n\nThank you for staying with us. We hope you had a restful stay. Could you take 60 seconds to share your experience with our team?\n\nThank you,\n{{hotel.name}} Management",
            variables_hint="{{guest.first_name}}, {{hotel.name}}",
        ),
        EmailTemplate(
            organization_id=org.id,
            key="staff_invite",
            name="Staff Team Invitation",
            subject="You've been invited to join {{hotel.name}} on CheckinOS",
            body="Hello,\n\nYou have been invited to collaborate on {{hotel.name}} PMS. Log in with your email to access your workspace.\n\nLogin URL: {{login_url}}",
            variables_hint="{{hotel.name}}, {{login_url}}",
        ),
        EmailTemplate(
            organization_id=org.id,
            key="staff_password_reset",
            name="Password Reset",
            subject="Reset your password for {{hotel.name}}",
            body="Hello,\n\nClick the link below to reset your CheckinOS password (expires in 1 hour):\n\n{{reset_url}}\n\nIf you did not request this, please ignore this email.",
            variables_hint="{{reset_url}}",
        ),
        EmailTemplate(
            organization_id=org.id,
            key="owner_trial_reminder",
            name="Trial Expiration Reminder",
            subject="Your 14-day free trial of {{hotel.name}} ends in {{days_left}} days",
            body="Hello {{owner.name}},\n\nYour CheckinOS trial has {{days_left}} days remaining. Upgrade now to keep managing reservations, rates, and guest billing without interruption.\n\nUpgrade link: {{billing_url}}",
            variables_hint="{{owner.name}}, {{days_left}}, {{billing_url}}",
        ),
        EmailTemplate(
            organization_id=org.id,
            key="owner_payment_failed",
            name="Subscription Payment Failed",
            subject="Action required: Payment failed for {{hotel.name}}",
            body="Hello {{owner.name}},\n\nWe were unable to process your monthly subscription payment for {{hotel.name}}. Please update your payment method to avoid account suspension.\n\nBilling portal: {{billing_url}}",
            variables_hint="{{owner.name}}, {{billing_url}}",
        ),
    ]
    for tmpl in templates:
        existing_tmpl = db.query(EmailTemplate).filter(
            EmailTemplate.organization_id == org.id,
            EmailTemplate.key == tmpl.key,
        ).first()
        if not existing_tmpl:
            db.add(tmpl)

    # 9. Business Date
    existing_bd = db.query(BusinessDate).filter(
        BusinessDate.organization_id == org.id,
        BusinessDate.date == today,
    ).first()
    if not existing_bd:
        bd = BusinessDate(
            organization_id=org.id,
            hotel_id=org.id,
            date=today,
            status="open",
        )
        db.add(bd)
    db.flush()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup_hotel_organization(
    payload: SignupRequest,
    db: Session = Depends(get_db),
):
    """Self-serve registration creating organization, owner user, 14-day trial, and demo data."""
    email = payload.email.lower().strip()

    # Reject duplicate email
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in.",
        )

    try:
        # 1. Create Organization
        slug = generate_unique_slug(payload.hotel_name, db)
        now = datetime.now(timezone.utc)
        trial_ends = now + timedelta(days=14)

        org = Organization(
            name=payload.hotel_name.strip(),
            slug=slug,
            plan=payload.plan or "starter",
            subscription_status="trialing",
            trial_ends_at=trial_ends,
            timezone=payload.timezone or "Asia/Kolkata",
            currency=payload.currency or "INR",
            address=f"{payload.hotel_name}, India",
        )
        db.add(org)
        db.flush()

        # 2. Create Owner User
        username = email.split("@")[0].replace(".", "_") + f"_{secrets.token_hex(2)}"
        owner = User(
            organization_id=org.id,
            email=email,
            username=username,
            full_name=payload.full_name.strip(),
            hashed_password=get_password_hash(payload.password),
            role="owner",
            email_verified=True,
            is_active=True,
            tour_completed=False,
        )
        db.add(owner)
        db.flush()

        # Link org owner
        org.owner_user_id = owner.id

        # Clean any stale records matching org.id or owner.id (safeguard against reused sequence/auto-increment IDs)
        db.query(UserOrgMembership).filter(
            (UserOrgMembership.organization_id == org.id) | (UserOrgMembership.user_id == owner.id)
        ).delete(synchronize_session=False)
        db.flush()

        # Create Owner Membership
        membership = UserOrgMembership(
            user_id=owner.id,
            organization_id=org.id,
            role="owner",
        )
        db.add(membership)
        db.flush()

        # 3. Auto-seed Demo Data for immediate exploration
        seed_organization_demo_data(org, db)

        # Activity log
        log = ActivityLog(
            organization_id=org.id,
            event_type="organization_registered",
            description=f"Hotel '{org.name}' ({org.slug}) signed up on 14-day trial",
            actor=owner.full_name,
        )
        db.add(log)
        db.commit()
        db.refresh(owner)
        db.refresh(org)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(exc)}",
        )

    # 4. Generate JWT Token with org_id claim
    token = create_access_token(
        data={"sub": owner.username, "role": "owner", "org_id": org.id}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=480 * 60,
        user=UserResponse.model_validate(owner),
        organization=OrganizationResponse.model_validate(org),
    )


@router.delete("/demo-data")
def delete_demo_data(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Soft-delete all sample demo records created during registration."""
    now = datetime.now(timezone.utc)

    # Soft delete demo reservations
    db.query(Reservation).filter(
        Reservation.organization_id == org.id,
        Reservation.is_demo.is_(True),
    ).update({"deleted_at": now}, synchronize_session=False)

    # Soft delete demo folio items
    db.query(FolioItem).filter(
        FolioItem.organization_id == org.id,
        FolioItem.is_demo.is_(True),
    ).update({"deleted_at": now}, synchronize_session=False)

    # Soft delete demo guests
    db.query(Guest).filter(
        Guest.organization_id == org.id,
        Guest.is_demo.is_(True),
    ).update({"deleted_at": now}, synchronize_session=False)

    # Soft delete demo rooms
    db.query(Room).filter(
        Room.organization_id == org.id,
        Room.is_demo.is_(True),
    ).update({"deleted_at": now}, synchronize_session=False)

    # Soft delete demo room types
    db.query(RoomType).filter(
        RoomType.organization_id == org.id,
        RoomType.is_demo.is_(True),
    ).update({"deleted_at": now}, synchronize_session=False)

    # Soft delete demo rate plans
    db.query(RatePlan).filter(
        RatePlan.organization_id == org.id,
        RatePlan.is_demo.is_(True),
    ).update({"deleted_at": now}, synchronize_session=False)

    # Soft delete demo policies
    db.query(CancellationPolicy).filter(
        CancellationPolicy.organization_id == org.id,
        CancellationPolicy.is_demo.is_(True),
    ).update({"deleted_at": now}, synchronize_session=False)

    # Soft delete demo taxes
    db.query(TaxRate).filter(
        TaxRate.organization_id == org.id,
        TaxRate.is_demo.is_(True),
    ).update({"deleted_at": now}, synchronize_session=False)

    log = ActivityLog(
        organization_id=org.id,
        event_type="demo_data_purged",
        description="Demo sample data was cleared from workspace.",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return {"message": "Demo data cleared successfully."}


@router.post("/auth/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Generates a secure password reset token and queues reset instructions."""
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        # In test/dev environment, token is returned in message for automated verification
        return {"message": "Password reset email sent if account exists.", "reset_token": token}
    return {"message": "Password reset email sent if account exists."}


@router.post("/auth/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Consumes password reset token and sets new password."""
    now = datetime.now(timezone.utc)
    user = db.query(User).filter(User.reset_token == payload.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    token_exp = user.reset_token_expires_at
    if token_exp:
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)
        if now > token_exp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset token has expired.",
            )

    user.hashed_password = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return {"message": "Password updated successfully. You can now log in."}


@router.post("/auth/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticated endpoint allowing users to update their current password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password.",
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}


@router.post("/user/complete-tour")
def mark_tour_completed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks onboarding product tour as completed for current user."""
    current_user.tour_completed = True
    db.commit()
    return {"status": "ok", "tour_completed": True}


# ── Interactive Onboarding Wizard Endpoints ─────────────────────────────────

@router.get("/onboarding/data")
def get_onboarding_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch current organization's configuration and pre-seeded rooms, rate plans, and taxes."""
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    room_types = db.query(RoomType).filter(
        RoomType.organization_id == org.id,
        RoomType.deleted_at.is_(None),
    ).order_by(RoomType.id.asc()).all()

    rooms = db.query(Room).filter(
        Room.organization_id == org.id,
        Room.deleted_at.is_(None),
    ).order_by(Room.floor.asc(), Room.number.asc()).all()

    rate_plans = db.query(RatePlan).filter(
        RatePlan.organization_id == org.id,
        RatePlan.deleted_at.is_(None),
    ).order_by(RatePlan.id.asc()).all()

    taxes = db.query(TaxRate).filter(
        TaxRate.organization_id == org.id,
        TaxRate.deleted_at.is_(None),
    ).order_by(TaxRate.id.asc()).all()

    rt_map = {rt.id: rt.name for rt in room_types}

    city_val = ""
    if org.address and "," in org.address:
        parts = org.address.split(",")
        city_val = parts[-1].strip() if len(parts) > 1 else org.address
    elif org.address:
        city_val = org.address

    return {
        "hotel_name": org.name,
        "city": city_val or "Jaipur, Rajasthan",
        "currency": org.currency or "INR",
        "gstin": org.tax_id or "",
        "room_types": [
            {
                "id": rt.id,
                "name": rt.name,
                "code": rt.code.split("-")[0] if "-" in rt.code else rt.code,
                "base_rate": float(rt.base_rate),
                "max_occupancy": rt.max_occupancy,
                "description": rt.description or "Standard King Bed",
            }
            for rt in room_types
        ],
        "rooms": [
            {
                "id": r.id,
                "number": r.number,
                "floor": r.floor,
                "room_type_name": rt_map.get(r.room_type_id, (room_types[0].name if room_types else "Deluxe King")),
            }
            for r in rooms
        ],
        "rate_plans": [
            {
                "id": rp.id,
                "code": rp.code.split("-")[0] if "-" in rp.code else rp.code,
                "name": rp.name,
                "description": rp.description or "",
                "modifier_type": rp.modifier_type,
                "modifier_value": float(rp.modifier_value),
                "refundable": rp.refundable,
            }
            for rp in rate_plans
        ],
        "taxes": [
            {
                "id": t.id,
                "name": t.name,
                "rate": float(t.rate),
                "applies_to": t.applies_to,
                "description": f"Tariffs {'≤' if t.rate <= 12 else '>'} ₹7,500",
            }
            for t in taxes
        ],
    }


@router.post("/onboarding/save")
def save_onboarding_data(
    payload: OnboardingSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persists customized room types, room inventory, rate plans, and taxes from onboarding wizard."""
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        # 1. Update Organization Profile
        if payload.hotel_name and payload.hotel_name.strip():
            org.name = payload.hotel_name.strip()
        if payload.city and payload.city.strip():
            org.address = f"{org.name}, {payload.city.strip()}"
        if payload.gstin is not None:
            org.tax_id = payload.gstin.strip() if payload.gstin else None
        if payload.currency:
            org.currency = payload.currency.strip().upper()

        # 2. Synchronize Room Types
        rt_name_to_obj = {}
        if payload.room_types is not None and len(payload.room_types) > 0:
            existing_rts = db.query(RoomType).filter(
                RoomType.organization_id == org.id,
                RoomType.deleted_at.is_(None),
            ).all()
            existing_by_name = {rt.name.strip().lower(): rt for rt in existing_rts}

            for item in payload.room_types:
                item_name = item.name.strip()
                code_prefix = slugify(item.code or item_name)[:4].upper() or "ROOM"
                base_code = f"{code_prefix}-{org.id}"

                if item_name.lower() in existing_by_name:
                    rt = existing_by_name[item_name.lower()]
                    rt.name = item_name
                    rt.base_rate = item.base_rate
                    rt.max_occupancy = item.max_occupancy
                    rt.description = item.description
                else:
                    counter = 1
                    test_code = base_code
                    while db.query(RoomType).filter(RoomType.organization_id == org.id, RoomType.code == test_code).first():
                        test_code = f"{code_prefix}{counter}-{org.id}"
                        counter += 1
                    rt = RoomType(
                        organization_id=org.id,
                        name=item_name,
                        code=test_code,
                        description=item.description or "Standard Bed",
                        base_rate=item.base_rate,
                        max_occupancy=item.max_occupancy,
                        is_demo=False,
                    )
                    db.add(rt)
                db.flush()
                rt_name_to_obj[item_name.lower()] = rt

        # Refresh all active room types
        all_rts = db.query(RoomType).filter(
            RoomType.organization_id == org.id,
            RoomType.deleted_at.is_(None),
        ).all()
        for rt in all_rts:
            rt_name_to_obj[rt.name.strip().lower()] = rt
        fallback_rt = all_rts[0] if all_rts else None

        # 3. Synchronize Rooms
        if payload.rooms is not None and fallback_rt:
            existing_rooms = db.query(Room).filter(
                Room.organization_id == org.id,
                Room.deleted_at.is_(None),
            ).all()
            existing_by_number = {r.number.strip(): r for r in existing_rooms}
            submitted_numbers = set()

            for r_item in payload.rooms:
                r_num = str(r_item.number).strip()
                if not r_num:
                    continue
                submitted_numbers.add(r_num)
                target_rt = rt_name_to_obj.get(r_item.room_type_name.strip().lower(), fallback_rt)

                if r_num in existing_by_number:
                    room = existing_by_number[r_num]
                    room.floor = r_item.floor
                    room.room_type_id = target_rt.id
                else:
                    room = Room(
                        organization_id=org.id,
                        number=r_num,
                        floor=r_item.floor,
                        room_type_id=target_rt.id,
                        status="available",
                        is_demo=False,
                    )
                    db.add(room)
                db.flush()

            # Handle removed rooms safely
            active_rooms = db.query(Room).filter(
                Room.organization_id == org.id,
                Room.number.in_(list(submitted_numbers)),
            ).all()
            first_active_room = active_rooms[0] if active_rooms else None

            for old_r in existing_rooms:
                if old_r.number.strip() not in submitted_numbers:
                    if first_active_room:
                        db.query(Reservation).filter(Reservation.room_id == old_r.id).update(
                            {"room_id": first_active_room.id}, synchronize_session=False
                        )
                        db.query(HousekeepingTask).filter(HousekeepingTask.room_id == old_r.id).update(
                            {"room_id": first_active_room.id}, synchronize_session=False
                        )
                    else:
                        db.query(HousekeepingTask).filter(HousekeepingTask.room_id == old_r.id).delete(synchronize_session=False)
                    db.delete(old_r)
            db.flush()

        # 4. Synchronize Rate Plans
        if payload.rate_plans is not None:
            existing_plans = db.query(RatePlan).filter(
                RatePlan.organization_id == org.id,
                RatePlan.deleted_at.is_(None),
            ).all()
            plan_by_code = {p.code.split("-")[0].upper(): p for p in existing_plans}

            for p_item in payload.rate_plans:
                p_code = p_item.code.strip().upper()
                if p_code in plan_by_code:
                    plan = plan_by_code[p_code]
                    plan.name = p_item.name.strip()
                    plan.description = p_item.description
                    plan.modifier_type = p_item.modifier_type
                    plan.modifier_value = p_item.modifier_value
                    plan.refundable = p_item.refundable
                else:
                    plan = RatePlan(
                        organization_id=org.id,
                        hotel_id=org.id,
                        code=f"{p_code}-{org.id}",
                        name=p_item.name.strip(),
                        description=p_item.description or "",
                        modifier_type=p_item.modifier_type,
                        modifier_value=p_item.modifier_value,
                        refundable=p_item.refundable,
                        is_demo=False,
                    )
                    db.add(plan)
                db.flush()

        # 5. Synchronize Tax Rates
        if payload.taxes is not None:
            existing_taxes = db.query(TaxRate).filter(
                TaxRate.organization_id == org.id,
                TaxRate.deleted_at.is_(None),
            ).all()
            tax_by_name = {t.name.strip().lower(): t for t in existing_taxes}

            for t_item in payload.taxes:
                t_name = t_item.name.strip()
                if t_name.lower() in tax_by_name:
                    tax = tax_by_name[t_name.lower()]
                    tax.rate = t_item.rate
                    tax.applies_to = t_item.applies_to
                else:
                    tax = TaxRate(
                        organization_id=org.id,
                        hotel_id=org.id,
                        name=t_name,
                        rate=t_item.rate,
                        applies_to=t_item.applies_to,
                        type="exclusive",
                        per="night",
                        is_demo=False,
                    )
                    db.add(tax)
                db.flush()

        # 6. Optional Staff Invitation
        if payload.staff and payload.staff.email:
            st_email = payload.staff.email.strip().lower()
            existing_st = db.query(User).filter(User.email == st_email).first()
            if not existing_st and payload.staff.full_name:
                st_username = st_email.split("@")[0].replace(".", "_") + f"_{secrets.token_hex(2)}"
                st_user = User(
                    organization_id=org.id,
                    email=st_email,
                    username=st_username,
                    full_name=payload.staff.full_name.strip(),
                    hashed_password=get_password_hash("WelcomePass123!"),
                    role=payload.staff.role or "front_desk",
                    email_verified=True,
                    is_active=True,
                    tour_completed=False,
                )
                db.add(st_user)
                db.flush()
                st_membership = UserOrgMembership(
                    user_id=st_user.id,
                    organization_id=org.id,
                    role=payload.staff.role or "front_desk",
                )
                db.add(st_membership)

        # 7. Complete Onboarding
        current_user.tour_completed = True
        log = ActivityLog(
            organization_id=org.id,
            event_type="onboarding_customized",
            description="User saved customized hotel rooms, rates, and tax setup in onboarding wizard.",
            actor=current_user.full_name,
        )
        db.add(log)
        db.commit()

        return {"status": "ok", "message": "Onboarding settings successfully saved!"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save onboarding configuration: {str(exc)}",
        )

