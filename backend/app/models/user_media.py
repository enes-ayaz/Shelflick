import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.media import MediaItem
    from app.models.user import User


class WatchStatus(str, enum.Enum):
    """User media consumption and tracking status."""
    COMPLETED = "COMPLETED"
    WATCHING = "WATCHING"
    DROPPED = "DROPPED"
    PLAN_TO_WATCH = "PLAN_TO_WATCH"


class UserMedia(Base):
    """UserMedia entity mapping user interaction, rating, and tracking for a media item."""

    __tablename__ = "user_media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique user media record ID (UUID)",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key reference to User",
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key reference to MediaItem",
    )
    status: Mapped[WatchStatus] = mapped_column(
        SAEnum(
            WatchStatus,
            name="watch_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=WatchStatus.PLAN_TO_WATCH,
        doc="Current consumption status",
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        doc="Favorite flag for 'Gold Box' highlighting",
    )
    user_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="User rating score between 1.0 and 10.0",
    )
    drop_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Optional note explaining why consumption was dropped",
    )
    personal_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Private user notes, comments or review",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
        doc="Initial record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Last modification timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="library_entries",
    )
    media_item: Mapped["MediaItem"] = relationship(
        "MediaItem",
        back_populates="user_media_entries",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "media_id",
            name="uq_user_media_user_id_media_id",
        ),
        CheckConstraint(
            "user_score IS NULL OR (user_score >= 1.0 AND user_score <= 10.0)",
            name="check_user_score_range",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UserMedia(user_id={self.user_id}, media_id={self.media_id}, "
            f"status={self.status}, score={self.user_score}, fav={self.is_favorite})>"
        )
