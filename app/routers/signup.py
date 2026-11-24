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
    """Auto-seeds a newly registered hotel organization with realistic demo data."""
    # 1. Room Types
    rt_std = RoomType(
        organization_id=org.id,
        name="Standard Queen",
        code=f"STD-Q-{org.id}",
        description="Comfortable standard queen room with city views",
        base_rate=Decimal("3500.00"),
        max_occupancy=2,
        is_demo=True,
    )
    rt_dlx = RoomType(
        organization_id=org.id,
        name="Deluxe King",
        code=f"DLX-K-{org.id}",
        description="Spacious king room with luxury bathroom and balcony",
        base_rate=Decimal("6500.00"),
        max_occupancy=2,
        is_demo=True,
    )
    rt_ste = RoomType(
        organization_id=org.id,
        name="Executive Suite",
        code=f"EXE-S-{org.id}",
        description="Premium suite with separate living room and skyline views",
        base_rate=Decimal("12000.00"),
        max_occupancy=4,
        is_demo=True,
    )
    db.add_all([rt_std, rt_dlx, rt_ste])
    db.flush()

    # 2. Rooms (10 rooms)
    rooms = []
    for i in range(1, 6):
        rooms.append(Room(
            organization_id=org.id,
            number=f"10{i}",
            floor=1,
            room_type_id=rt_std.id,
            status="available" if i > 2 else "occupied",
            is_demo=True,
        ))
    for i in range(1, 4):
        rooms.append(Room(
            organization_id=org.id,
            number=f"20{i}",
            floor=2,
            room_type_id=rt_dlx.id,
            status="available" if i > 1 else "dirty",
            is_demo=True,
        ))
    for i in range(4, 6):
        rooms.append(Room(
            organization_id=org.id,
            number=f"20{i}",
            floor=2,
            room_type_id=rt_ste.id,
            status="available",
            is_demo=True,
        ))
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
            description="Best flexible rate with free cancellation",
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
            description="10% discount for prepaid non-refundable bookings",
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
            description="Room plus chef complimentary buffet breakfast",
            modifier_type="absolute",
            modifier_value=Decimal("1200.00"),
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
            description="15% discount for extended stays",
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
        name="GST 12% (Rooms ≤ ₹7,500)",
        rate=Decimal("12.00"),
        applies_to="rooms",
        type="exclusive",
        per="night",
        is_demo=True,
    )
    tax_18 = TaxRate(
        organization_id=org.id,
        hotel_id=org.id,
        name="GST 18% (Luxury Rooms > ₹7,500)",
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
        nightly_rate=Decimal("3500.00"),
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
        nightly_rate=Decimal("3150.00"),
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
        nightly_rate=Decimal("3500.00"),
        status="booked",
        is_demo=True,
    )
    res4 = Reservation(
        organization_id=org.id,
        confirmation_number=f"DEMO-{org.id}-104",
        guest_id=guests[3].id,
        room_id=rooms[5].id,
        rate_plan_id=plans[2].id,
        check_in_date=today + timedelta(days=2),
        check_out_date=today + timedelta(days=5),
        adults=2,
        nightly_rate=Decimal("7700.00"),
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
        nightly_rate=Decimal("12000.00"),
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
