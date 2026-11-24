"""Organization Management and Multi-Tenancy API."""
from datetime import datetime, date, timedelta, timezone
import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.database import get_db
from app.deps import get_current_org, get_current_user, require_role, check_plan_limits
from app.models import (
    ActivityLog,
    Organization,
    Reservation,
    Room,
    User,
    UserOrgMembership,
)
from app.schemas import (
    OrganizationResponse,
    OrganizationUpdate,
    OrgMemberResponse,
    OrgUsageStats,
    UserOrgInviteRequest,
)

router = APIRouter(prefix="/api/org", tags=["Organizations"])


def compute_org_usage(org: Organization, db: Session) -> OrgUsageStats:
    """Computes room count, user count, and reservation metrics against plan limits."""
    limits = {
        "starter": {"rooms": 15, "users": 3},
        "pro": {"rooms": 50, "users": 10},
        "enterprise": {"rooms": "Unlimited", "users": "Unlimited"},
    }
    plan_key = org.plan.lower() if org.plan else "starter"
    plan_limit = limits.get(plan_key, limits["starter"])

    used_rooms = db.query(Room).filter(
        Room.organization_id == org.id,
        Room.deleted_at.is_(None),
    ).count()

    used_users = db.query(UserOrgMembership).filter(
        UserOrgMembership.organization_id == org.id
    ).count()

    # Reservations in current calendar month
    today = date.today()
    first_of_month = today.replace(day=1)
    res_count = db.query(Reservation).filter(
        Reservation.organization_id == org.id,
        Reservation.check_in_date >= first_of_month,
        Reservation.deleted_at.is_(None),
    ).count()

    return OrgUsageStats(
        rooms={"used": used_rooms, "limit": plan_limit["rooms"]},
        users={"used": used_users, "limit": plan_limit["users"]},
        reservations_this_month=res_count,
    )


@router.get("", response_model=OrganizationResponse)
def get_organization_info(
    org: Organization = Depends(get_current_org),
):
    """Retrieve details for the active organization."""
    return org


@router.patch("", response_model=OrganizationResponse)
def update_organization_info(
    payload: OrganizationUpdate,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Update organization profile, timezone, currency, address, and branding."""
    if payload.name is not None:
        org.name = payload.name.strip()
    if payload.brand_color is not None:
        org.brand_color = payload.brand_color.strip()
    if payload.timezone is not None:
        org.timezone = payload.timezone.strip()
    if payload.currency is not None:
        org.currency = payload.currency.strip().upper()
    if payload.address is not None:
        org.address = payload.address.strip()
    if payload.tax_id is not None:
        org.tax_id = payload.tax_id.strip()

    db.commit()
    db.refresh(org)
    return org


@router.post("/logo", response_model=OrganizationResponse)
async def upload_organization_logo(
    file: UploadFile = File(...),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Upload hotel logo image and associate with organization."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (PNG, JPG, SVG)",
        )

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".svg", ".webp"):
        ext = ".png"

    upload_dir = os.path.join("static", "uploads", org.slug)
    os.makedirs(upload_dir, exist_ok=True)
    logo_filename = f"logo{ext}"
    dest_path = os.path.join(upload_dir, logo_filename)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    relative_url = f"/static/uploads/{org.slug}/{logo_filename}"
    org.logo_url = relative_url
    db.commit()
    db.refresh(org)

    return org


@router.get("/usage", response_model=OrgUsageStats)
def get_organization_usage(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get live plan usage metrics (rooms used/limit, users used/limit, monthly bookings)."""
    return compute_org_usage(org, db)


@router.get("/members", response_model=List[OrgMemberResponse])
def list_organization_members(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all team members and roles assigned to this organization."""
    members = (
        db.query(UserOrgMembership)
        .filter(UserOrgMembership.organization_id == org.id)
        .all()
    )
    return members


@router.post("/invite", response_model=OrgMemberResponse, status_code=status.HTTP_201_CREATED)
def invite_organization_member(
    payload: UserOrgInviteRequest,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Invite an employee or manager to join this hotel property."""
    # Enforce user tier limits
    check_plan_limits(org, "users", db)

    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Create new user record with default password
        username = email.split("@")[0].replace(".", "_") + f"_{os.urandom(2).hex()}"
        full_name = payload.full_name or email.split("@")[0].title()
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=get_password_hash("CheckinOS@2026"),
            role=payload.role,
            organization_id=org.id,
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.flush()

    # Check if already a member of this org
    existing_mem = db.query(UserOrgMembership).filter(
        UserOrgMembership.user_id == user.id,
        UserOrgMembership.organization_id == org.id,
    ).first()

    if existing_mem:
        existing_mem.role = payload.role
        db.commit()
        db.refresh(existing_mem)
        return existing_mem

    membership = UserOrgMembership(
        user_id=user.id,
        organization_id=org.id,
        role=payload.role,
    )
    db.add(membership)

    log = ActivityLog(
        organization_id=org.id,
        event_type="user_invited",
        description=f"Invited {user.email} with role {payload.role}",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(membership)

    return membership


@router.delete("/members/{user_id}")
def remove_organization_member(
    user_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Remove user membership from this organization."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the organization",
        )

    mem = db.query(UserOrgMembership).filter(
        UserOrgMembership.user_id == user_id,
        UserOrgMembership.organization_id == org.id,
    ).first()

    if not mem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} is not a member of this organization",
        )

    db.delete(mem)
    db.commit()
    return {"message": "User membership removed successfully"}
