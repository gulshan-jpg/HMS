"""Authentication API Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app.auth import create_access_token, verify_password
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.limiter import limiter
from app.models import User, ActivityLog
from app.schemas import TokenResponse, UserLogin, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user with rate limiting and issue JWT access token."""
    login_ident = credentials.username_or_email.strip()
    user = db.query(User).filter(
        (User.username == login_ident) | (User.email == login_ident)
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    expires_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role, "org_id": user.organization_id}
    )

    # Set cookie for seamless HTML app navigation
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,
        max_age=expires_seconds,
        samesite="lax",
        secure=settings.ENV == "prod",
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_seconds,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    """Clear session cookie and invalidate client state."""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return currently authenticated user profile."""
    return current_user
