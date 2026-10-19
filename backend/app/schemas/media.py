import uuid
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.media import MediaSource


class MediaItemBase(BaseModel):
    """Base schema for MediaItem entity."""
    external_id: str = Field(..., max_length=100, description="External provider ID (TMDB/AniList)")
    media_source: MediaSource = Field(..., description="Provider source type")
    title: str = Field(..., min_length=1, max_length=255, description="Media title")
    original_title: Optional[str] = Field(None, max_length=255, description="Original title in source language")
    release_year: Optional[int] = Field(None, ge=1888, le=2100, description="Release year")
    poster_url: str = Field(..., max_length=1024, description="Full CDN poster image URL")
    synopsis: str = Field(..., description="Plot synopsis or description")
    genres: List[str] = Field(default_factory=list, description="List of genre tags")
    themes: List[str] = Field(default_factory=list, description="List of theme/mood tags")
    runtime: Optional[int] = Field(default=None, description="Runtime in minutes")
    total_episodes: Optional[int] = Field(default=1, description="Total episode count")
    total_seasons: Optional[int] = Field(default=None, description="Total seasons count")
    airing_status: Optional[str] = Field(default=None, description="Airing status")
    next_airing_info: Optional[Any] = Field(default=None, description="Next airing episode/season info")


class MediaItemCreate(MediaItemBase):
    """Schema for creating a new MediaItem."""
    imdb_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Initial IMDb rating")
    imdb_vote_count: int = Field(default=0, ge=0, description="Initial IMDb vote count")


class MediaItemUpdate(BaseModel):
    """Schema for updating an existing MediaItem."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    original_title: Optional[str] = Field(None, max_length=255)
    release_year: Optional[int] = Field(None, ge=1888, le=2100)
    poster_url: Optional[str] = Field(None, max_length=1024)
    synopsis: Optional[str] = None
    genres: Optional[List[str]] = None
    themes: Optional[List[str]] = None
    imdb_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    imdb_vote_count: Optional[int] = Field(None, ge=0)
    runtime: Optional[int] = None
    total_episodes: Optional[int] = None
    total_seasons: Optional[int] = None
    airing_status: Optional[str] = None
    next_airing_info: Optional[Any] = None


class MediaItemResponse(MediaItemBase):
    """Schema for MediaItem response serialization."""
    id: uuid.UUID
    imdb_score: Optional[float] = None
    imdb_vote_count: int = 0
    site_score: Optional[float] = None
    site_vote_count: int = 0

    model_config = ConfigDict(from_attributes=True)
