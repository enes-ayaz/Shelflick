from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.media import MediaSource


class UnifiedMediaDTO(BaseModel):
    """Standardized Data Transfer Object for external media entities (TMDB & AniList)."""

    external_id: str = Field(
        ...,
        description="Origin provider identifier (TMDB ID or AniList ID)",
        examples=["603", "16498"],
    )
    source: Literal["TMDB_MOVIE", "TMDB_SERIES", "ANILIST"] = Field(
        ...,
        description="Source provider platform and media type",
        examples=["TMDB_MOVIE"],
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Primary display title",
        examples=["The Matrix"],
    )
    original_title: Optional[str] = Field(
        default=None,
        description="Original language title",
        examples=["The Matrix"],
    )
    release_year: Optional[int] = Field(
        default=None,
        ge=1888,
        le=2100,
        description="Release year",
        examples=[1999],
    )
    poster_url: str = Field(
        ...,
        description="Fully qualified CDN poster URL (TMDB includes w500 prefix)",
        examples=["https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg"],
    )
    synopsis: str = Field(
        default="",
        description="Clean text synopsis or overview",
        examples=["A computer hacker learns from mysterious rebels about the true nature of his reality..."],
    )
    genres: List[str] = Field(
        default_factory=list,
        description="List of genre names",
        examples=[["Action", "Science Fiction"]],
    )
    themes: List[str] = Field(
        default_factory=list,
        description="List of theme/mood tags (e.g., cyberpunk, revenge)",
        examples=[["cyberpunk", "virtual reality"]],
    )
    base_score: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Normalized baseline rating on a 0.0 - 10.0 scale",
        examples=[8.7],
    )
    vote_count: int = Field(
        default=0,
        ge=0,
        description="Total votes or popularity metric count",
        examples=[24500],
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
    )
