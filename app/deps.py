"""FastAPI Dependencies for Security, Multi-Tenancy, Database, and RBAC."""
from datetime import datetime, timezone, timedelta
from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.config import settings
from app.database import get_db, current_org_id
from app.models import Organization, Room, User, UserOrgMembership

bearer_scheme = HTTPBearer(auto_error=False)


def resolve_subdomain_slug(host: str) -> Optional[str]:
    """Extracts tenant organization slug from subdomain if present."""
    if not host:
        return None
    hostname = host.split(":")[0].lower()
    root_domain = settings.ROOT_DOMAIN.lower()
    if hostname.endswith("." + root_domain) and hostname != root_domain:
        slug = hostname.replace("." + root_domain, "").strip()
        if slug and slug not in ("www", "app", "api", "admin", "mail", "static"):
            return slug
    return None


async def get_current_user(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extracts, verifies, and returns the current authenticated User."""
    token: Optional[str] = None

    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")
    elif "token" in request.query_params:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        username: Optional[str] = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        request.state.jwt_payload = payload
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    if user.organization_id:
        current_org_id.set(user.organization_id)
        request.state.current_org_id = user.organization_id

    return user


async def get_current_org(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    """Resolves the active Organization for the current request context."""
    # 1. Check Subdomain
    subdomain_slug = resolve_subdomain_slug(request.headers.get("host", ""))
    if subdomain_slug:
        org = db.query(Organization).filter(
            Organization.slug == subdomain_slug,
            Organization.deleted_at.is_(None),
        ).first()
        if org:
            # Verify user belongs to this org or is global admin
            membership = db.query(UserOrgMembership).filter(
                UserOrgMembership.user_id == current_user.id,
                UserOrgMembership.organization_id == org.id,
            ).first()
            if not membership and current_user.organization_id != org.id and current_user.role not in ("admin", "owner"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have access to organization '{org.name}'",
                )
            current_org_id.set(org.id)
            request.state.current_org = org
            return org

    # 2. Check header X-Organization-Id
    header_org_id = request.headers.get("X-Organization-Id")
    if header_org_id and header_org_id.isdigit():
        target_id = int(header_org_id)
        org = db.query(Organization).filter(
            Organization.id == target_id,
            Organization.deleted_at.is_(None),
        ).first()
        if org:
            membership = db.query(UserOrgMembership).filter(
                UserOrgMembership.user_id == current_user.id,
                UserOrgMembership.organization_id == org.id,
            ).first()
            if not membership and current_user.organization_id != org.id and current_user.role not in ("admin", "owner"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have access to organization ID {target_id}",
                )
            current_org_id.set(org.id)
            request.state.current_org = org
            return org

    # 3. Check JWT claim 'org_id'
    jwt_payload = getattr(request.state, "jwt_payload", {})
    if "org_id" in jwt_payload and str(jwt_payload["org_id"]).isdigit():
        target_id = int(jwt_payload["org_id"])
        org = db.query(Organization).filter(
            Organization.id == target_id,
            Organization.deleted_at.is_(None),
        ).first()
        if org:
            current_org_id.set(org.id)
            request.state.current_org = org
            return org

    # 4. Fallback to user's assigned organization_id or first membership
    target_id = current_user.organization_id
    if not target_id:
        first_mem = db.query(UserOrgMembership).filter(
            UserOrgMembership.user_id == current_user.id
        ).first()
        if first_mem:
            target_id = first_mem.organization_id
        else:
            target_id = 1

    org = db.query(Organization).filter(
        Organization.id == target_id,
        Organization.deleted_at.is_(None),
    ).first()

    if not org:
        # Fallback to org 1 or create default
        org = db.query(Organization).filter(Organization.id == 1).first()
        if not org:
            org = Organization(
                id=1,
                name="The Grand Palace Bangalore",
                slug="grand-palace",
                plan="pro",
                subscription_status="active",
                timezone="Asia/Kolkata",
                currency="INR",
            )
            db.add(org)
            db.commit()
            db.refresh(org)

    current_org_id.set(org.id)
    request.state.current_org = org
    return org


def get_user_role_in_org(user: User, org: Organization, db: Session) -> str:
    """Gets the user's specific role within the given organization."""
    if user.role in ("owner", "admin"):
        return user.role

    mem = db.query(UserOrgMembership).filter(
        UserOrgMembership.user_id == user.id,
        UserOrgMembership.organization_id == org.id,
    ).first()

    if mem:
        return mem.role
    return user.role or "front_desk"


def require_role(*allowed_roles: str) -> Callable:
    """Dependency restricting endpoints based on role presets."""
    async def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        # Admin and owner have superuser access to all operational endpoints
        if current_user.role in ("admin", "owner"):
            return current_user

        org = getattr(request.state, "current_org", None)
        active_role = get_user_role_in_org(current_user, org, db) if org else current_user.role

        if active_role in ("admin", "owner"):
            return current_user

        # Normalization: map role aliases
        check_roles = set(allowed_roles)
        if "admin" in check_roles or "owner" in check_roles:
            check_roles.update(["admin", "owner"])

        if active_role not in check_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join(allowed_roles)}. Your role: {active_role}",
            )
        return current_user

    return role_checker


async def check_subscription_state(
    request: Request,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
) -> Organization:
    """Enforces trial, payment status, and subscription write locks."""
    path = request.url.path

    # Bypass billing, auth, and setup routes so user can upgrade
    bypass_prefixes = (
        "/api/billing",
        "/api/org",
        "/settings/billing",
        "/pricing",
        "/locked",
        "/api/auth",
        "/docs",
        "/openapi.json",
    )
    if any(path.startswith(prefix) for prefix in bypass_prefixes):
        return org

    sub_status = org.subscription_status.lower() if org.subscription_status else "trialing"
    is_write = request.method in ("POST", "PUT", "PATCH", "DELETE")

    # Completely locked organization
    if sub_status == "locked":
        if is_write:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "subscription_locked", "message": "Your subscription is locked. Upgrade to reactivate."},
            )

    # Trial expiration check
    if sub_status == "trialing":
        if org.trial_ends_at:
            # Timezone-aware check
            now = datetime.now(timezone.utc)
            trial_end = org.trial_ends_at
            if trial_end.tzinfo is None:
                trial_end = trial_end.replace(tzinfo=timezone.utc)

            if now > trial_end:
                if is_write:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail={"code": "trial_expired", "message": "Trial ended. Upgrade to continue."},
                    )

    # Past due soft lock on writes
    elif sub_status == "past_due":
        if is_write:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "payment_failed", "message": "Payment failed. Update payment method."},
            )

    # Cancelled: 30 days read-only grace, then locked
    elif sub_status == "cancelled":
        if is_write:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "subscription_cancelled", "message": "Subscription cancelled. Account is in read-only mode."},
            )

    return org


def check_plan_limits(org: Organization, entity_type: str, db: Session) -> None:
    """Enforces room and user limits per tier (starter, pro, enterprise)."""
    limits = {
        "starter": {"rooms": 15, "users": 3},
        "pro": {"rooms": 50, "users": 10},
        "enterprise": {"rooms": float("inf"), "users": float("inf")},
    }

    plan_key = org.plan.lower() if org.plan else "starter"
    limit = limits.get(plan_key, limits["starter"]).get(entity_type, float("inf"))

    if entity_type == "rooms":
        current_count = db.query(Room).filter(
            Room.organization_id == org.id,
            Room.deleted_at.is_(None),
        ).count()
        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "plan_limit", "message": f"Room limit reached. Upgrade to add more."},
            )
    elif entity_type == "users":
        current_count = db.query(UserOrgMembership).filter(
            UserOrgMembership.organization_id == org.id
        ).count()
        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "plan_limit", "message": f"User limit reached. Upgrade to add more."},
            )
