import logging
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
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

# Google sertifikalarını her istekte yeniden indirmemek için paylaşılan oturum
_google_request = google_requests.Request()

# Windows/yerel makinelerde saat kayması "Token used too early" hatasına yol açabiliyor.
GOOGLE_CLOCK_SKEW_SECONDS = 60

INVALID_CREDENTIALS_MSG = "E-posta veya şifre hatalı."
DB_ERROR_MSG = "Sunucuda geçici bir sorun oluştu. Lütfen biraz sonra tekrar deneyin."


# ----------------------------------------------------------------- helpers --

def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _make_username(email: str) -> str:
    """Generates a unique-ish username that always fits the 50 char column."""
    base = re.sub(r"[^a-z0-9_.]", "", email.split("@")[0].lower()) or "user"
    return f"{base[:40]}_{uuid.uuid4().hex[:6]}"


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(subject=user.id),
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


async def _get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def _google_client_id() -> Optional[str]:
    cid = (settings.GOOGLE_CLIENT_ID or "").strip().strip('"').strip("'")
    return cid or None


def _verify_google_token(credential: str) -> dict:
    """Blocking verification (network call for certs) - run in threadpool."""
    return id_token.verify_oauth2_token(
        credential,
        _google_request,
        audience=_google_client_id(),
        clock_skew_in_seconds=GOOGLE_CLOCK_SKEW_SECONDS,
    )


def _google_error_message(err: Exception) -> str:
    text = str(err)
    if "audience" in text.lower() or "Token has wrong" in text:
        return (
            "Google Client ID uyuşmuyor. Frontend (NEXT_PUBLIC_GOOGLE_CLIENT_ID) ve "
            "backend (GOOGLE_CLIENT_ID) aynı değeri kullanmalı."
        )
    if "expired" in text.lower():
        return "Google oturumunun süresi doldu. Lütfen tekrar deneyin."
    if "too early" in text.lower():
        return "Bilgisayarınızın saati senkronize değil. Saat ayarını kontrol edip tekrar deneyin."
    if "certs" in text.lower() or "connection" in text.lower() or "timed out" in text.lower():
        return "Google sunucularına ulaşılamadı. İnternet bağlantınızı kontrol edin."
    return "Google kimlik doğrulaması başarısız oldu. Lütfen tekrar deneyin."


# --------------------------------------------------------------- endpoints --

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with email and password."""
    email_clean = _normalize_email(payload.email)

    try:
        existing = await _get_user_by_email(db, email_clean)
        if existing:
            if not existing.hashed_password and existing.google_id:
                detail = (
                    "Bu e-posta adresi Google ile kayıtlı. "
                    "Lütfen 'Google ile giriş yap' seçeneğini kullanın."
                )
            else:
                detail = "Bu e-posta adresiyle kayıtlı bir hesap zaten var. Giriş yapmayı deneyin."
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

        name = (payload.name or "").strip() or email_clean.split("@")[0].capitalize()
        hashed = await run_in_threadpool(hash_password, payload.password)

        new_user = User(
            email=email_clean,
            name=name[:255],
            username=_make_username(email_clean),
            hashed_password=hashed,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except HTTPException:
        raise
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresiyle kayıtlı bir hesap zaten var. Giriş yapmayı deneyin.",
        )
    except (SQLAlchemyError, OSError) as e:
        await db.rollback()
        logger.exception("Register DB error: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DB_ERROR_MSG)

    return _token_response(new_user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password, returning a JWT token."""
    email_clean = _normalize_email(payload.email)

    try:
        user = await _get_user_by_email(db, email_clean)
    except (SQLAlchemyError, OSError) as e:
        logger.exception("Login DB error: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DB_ERROR_MSG)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS_MSG)

    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bu hesap Google ile oluşturulmuş. Lütfen 'Google ile giriş yap' seçeneğini kullanın.",
        )

    ok = await run_in_threadpool(verify_password, payload.password, user.hashed_password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS_MSG)

    return _token_response(user)


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate or register via Google OAuth2 ID Token."""
    if not _google_client_id():
        logger.warning("GOOGLE_CLIENT_ID is not configured; audience check is disabled.")

    try:
        id_info = await run_in_threadpool(_verify_google_token, payload.credential)
    except Exception as e:
        logger.warning("Google token verification failed: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_google_error_message(e))

    google_id = id_info.get("sub")
    email = id_info.get("email")
    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google hesabından e-posta adresi alınamadı.",
        )
    if id_info.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google hesabınızın e-posta adresi doğrulanmamış.",
        )

    email_clean = _normalize_email(email)
    name = (
        id_info.get("name")
        or id_info.get("given_name")
        or email_clean.split("@")[0].capitalize()
    )[:255]

    try:
        result = await db.execute(select(User).where(User.google_id == google_id))
        user = result.scalar_one_or_none()

        if not user:
            user = await _get_user_by_email(db, email_clean)
            if user:
                # Mevcut e-posta hesabını Google ile bağla
                user.google_id = google_id
                if not user.name:
                    user.name = name
            else:
                user = User(
                    email=email_clean,
                    name=name,
                    username=_make_username(email_clean),
                    google_id=google_id,
                    hashed_password=None,
                )
                db.add(user)
            await db.commit()
            await db.refresh(user)
    except IntegrityError:
        # Aynı anda iki istek (ör. çift tıklama) -> diğeri kullanıcıyı oluşturmuş olabilir
        await db.rollback()
        result = await db.execute(
            select(User).where((User.google_id == google_id) | (User.email == email_clean))
        )
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DB_ERROR_MSG)
    except (SQLAlchemyError, OSError) as e:
        await db.rollback()
        logger.exception("Google auth DB error: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DB_ERROR_MSG)

    return _token_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve current logged in user information."""
    return UserResponse.model_validate(current_user)
