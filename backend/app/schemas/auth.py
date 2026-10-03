from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for registering with email and password."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, max_length=128, description="User password (min 6 chars)")
    name: Optional[str] = Field(default=None, description="Display name / Full name")


class UserLoginRequest(BaseModel):
    """Payload for logging in with email and password."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class GoogleAuthRequest(BaseModel):
    """Payload for Google OAuth2 ID Token login/registration."""
    credential: str = Field(..., description="Google ID Token (JWT) provided by Google Identity Services")


class UserResponse(BaseModel):
    """Public user response data."""
    id: uuid.UUID
    email: str
    name: str
    username: Optional[str] = None
    google_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT response payload returned on successful authentication."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
