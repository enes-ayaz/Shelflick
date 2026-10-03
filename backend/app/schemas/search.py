from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class LiveSearchResultItem(BaseModel):
    """Lightweight autocomplete search result item from TMDB & AniList."""

    id: str = Field(..., description="Media external identifier")
    title: str = Field(..., description="Display title")
    release_year: Optional[int] = Field(default=None, description="Release year")
    type: Literal["MOVIE", "SERIES", "ANIME"] = Field(..., description="Media category")
    poster_path: Optional[str] = Field(default=None, description="Thumbnail / poster image URL")

    # Extra rich metadata for instant card rendering
    source: Optional[str] = Field(default=None, description="Original source identifier")
    base_score: Optional[float] = Field(default=None, description="Review score rating")
    synopsis: Optional[str] = Field(default=None, description="Plot overview")
    genres: List[str] = Field(default_factory=list, description="Genre tags")

    model_config = ConfigDict(from_attributes=True)
