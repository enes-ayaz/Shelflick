import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    GoogleAuthRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with email and password."""
    email_clean = payload.email.lower().strip()

    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == email_clean))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresiyle kayıtlı bir hesap zaten bulunmaktadır.",
        )

    # Resolve display name
    name = (payload.name or "").strip()
    if not name:
        name = email_clean.split("@")[0].capitalize()

    # Base username
    base_username = email_clean.split("@")[0]
    username_candidate = f"{base_username}_{uuid.uuid4().hex[:4]}"

    hashed = hash_password(payload.password)
    new_user = User(
        email=email_clean,
        name=name,
        username=username_candidate,
        hashed_password=hashed,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token(subject=new_user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password, returning a JWT token."""
    email_clean = payload.email.lower().strip()

    result = await db.execute(select(User).where(User.email == email_clean))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-posta veya şifre hatalı.",
        )

    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu hesap Google ile oluşturulmuş. Lütfen 'Google ile Devam Et' seçeneğini kullanın.",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-posta veya şifre hatalı.",
        )

    token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate or register via Google OAuth2 ID Token."""
    try:
        # Verify the Google ID token
        # If GOOGLE_CLIENT_ID is configured in settings, pass it as audience.
        # Otherwise None allows any valid Google signed token for development.
        client_id = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_ID.strip() else None
        
        id_info = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            audience=client_id,
        )
    except Exception as e:
        logger.warning(f"Google token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google kimlik doğrulaması başarısız oldu: {str(e)}",
        )

    google_id = id_info.get("sub")
    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google hesabından e-posta adresi alınamadı.",
        )

    email_clean = email.lower().strip()
    name = id_info.get("name") or id_info.get("given_name") or email_clean.split("@")[0].capitalize()

    # Check if user exists by google_id first
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        # Check if user exists by email
        result = await db.execute(select(User).where(User.email == email_clean))
        user = result.scalar_one_or_none()

        if user:
            # Link Google account to existing user
            user.google_id = google_id
            if not user.name:
                user.name = name
            await db.commit()
            await db.refresh(user)
        else:
            # Create new user without password
            base_username = email_clean.split("@")[0]
            username_candidate = f"{base_username}_{uuid.uuid4().hex[:4]}"
            user = User(
                email=email_clean,
                name=name,
                username=username_candidate,
                google_id=google_id,
                hashed_password=None,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

    token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve current logged in user information."""
    return UserResponse.model_validate(current_user)
