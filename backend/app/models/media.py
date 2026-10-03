import enum
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    CheckConstraint,
    Float,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user_media import UserMedia


class MediaSource(str, enum.Enum):
    """Supported external media sources."""
    TMDB_MOVIE = "TMDB_MOVIE"
    TMDB_SERIES = "TMDB_SERIES"
    ANILIST = "ANILIST"


class MediaItem(Base):
    """MediaItem entity representing movies, series, or anime records."""

    __tablename__ = "media_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique media item identifier (UUID)",
    )
    external_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="External identifier from origin API (e.g., TMDB ID or AniList ID)",
    )
    media_source: Mapped[MediaSource] = mapped_column(
        SAEnum(
            MediaSource,
            name="media_source_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        doc="Origin provider type (TMDB Movie, TMDB Series, AniList)",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Primary localized or display title",
    )
    original_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Original language title",
    )
    release_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Release or first air year",
    )
    poster_url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        doc="Full CDN poster image URL",
    )
    synopsis: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Plot summary or overview",
    )
    genres: Mapped[List[str]] = mapped_column(
        ARRAY(String).with_variant(JSON, "sqlite"),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Array of genre names (e.g. Action, Sci-Fi, Drama)",
    )
    themes: Mapped[List[str]] = mapped_column(
        ARRAY(String).with_variant(JSON, "sqlite"),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Array of themes and moods (e.g. dark, revenge, cyberpunk)",
    )
    imdb_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="IMDb baseline rating between 0.0 and 10.0",
    )
    imdb_vote_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Total number of IMDb votes recorded",
    )
    site_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Calculated hybrid weighted score",
    )
    site_vote_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Total community ratings submitted on MediaPulse",
    )

    # Relationships
    user_media_entries: Mapped[List["UserMedia"]] = relationship(
        "UserMedia",
        back_populates="media_item",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="User library interactions linked to this media item",
    )

    __table_args__ = (
        UniqueConstraint(
            "external_id",
            "media_source",
            name="uq_media_item_source_external_id",
        ),
        CheckConstraint(
            "imdb_score IS NULL OR (imdb_score >= 0.0 AND imdb_score <= 10.0)",
            name="check_imdb_score_range",
        ),
        CheckConstraint(
            "site_score IS NULL OR (site_score >= 0.0 AND site_score <= 10.0)",
            name="check_site_score_range",
        ),
        CheckConstraint(
            "site_vote_count >= 0",
            name="check_site_vote_count_positive",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MediaItem(id={self.id}, title='{self.title}', source={self.media_source}, "
            f"site_score={self.site_score}, votes={self.site_vote_count})>"
        )
