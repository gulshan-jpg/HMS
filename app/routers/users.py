"""User Management and Hotel Information API Endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth import get_password_hash
from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import ActivityLog, User
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
def list_team_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List staff and administration accounts for team management."""
    return db.query(User).order_by(User.id.asc()).all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_team_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Create a new staff member account with strict password policy."""
    # Check duplicate email
    if db.query(User).filter(User.email == payload.email.lower().strip()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {payload.email} already exists",
        )

    # Check duplicate username
    if db.query(User).filter(User.username == payload.username.strip()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username {payload.username} is already taken",
        )

    hashed_pw = get_password_hash(payload.password)
    user = User(
        email=payload.email.lower().strip(),
        username=payload.username.strip(),
        full_name=payload.full_name.strip(),
        hashed_password=hashed_pw,
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Activity log
    log = ActivityLog(
        event_type="user_created",
        description=f"Staff account {user.username} ({user.role}) created",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return UserResponse.model_validate(user)


@router.get("/hotel-info")
def get_hotel_info(current_user: User = Depends(get_current_user)):
    """Return configured property information, currency, and locale parameters."""
    return {
        "name": settings.HOTEL_NAME,
        "address": settings.HOTEL_ADDRESS,
        "phone": settings.HOTEL_PHONE,
        "email": settings.HOTEL_EMAIL,
        "currency": settings.HOTEL_CURRENCY,
        "timezone": settings.HOTEL_TIMEZONE,
        "tax_rate": settings.HOTEL_TAX_RATE,
        "version": "1.0.0",
    }
