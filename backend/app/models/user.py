import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user_media import UserMedia


class User(Base):
    """User entity model representing platform users."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique user identifier (UUID)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        doc="Full name or display name of the user",
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=True,
        doc="Unique username for login and public profile",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique user email address",
    )
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Bcrypt hashed password string (null for Google sign-in users)",
    )
    google_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
        doc="Google OAuth2 account ID",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
        doc="Account creation timestamp with timezone",
    )

    # Relationships
    library_entries: Mapped[List["UserMedia"]] = relationship(
        "UserMedia",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Library entries belonging to this user",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
