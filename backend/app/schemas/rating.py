import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.user_media import WatchStatus


class UserScoreInput(BaseModel):
    """Schema for submitting or updating a user's media score."""
    user_score: float = Field(
        ...,
        ge=1.0,
        le=10.0,
        description="Rating score between 1.0 and 10.0",
        examples=[8.5],
    )


class UserMediaBase(BaseModel):
    """Base schema for user library interaction."""
    status: WatchStatus = Field(
        default=WatchStatus.PLAN_TO_WATCH,
        description="Media tracking status",
    )
    is_favorite: bool = Field(
        default=False,
        description="Favorite flag for 'Gold Box' highlighting",
    )
    user_score: Optional[float] = Field(
        None,
        ge=1.0,
        le=10.0,
        description="User rating score between 1.0 and 10.0",
    )
    drop_reason: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional reason if media is dropped",
    )
    personal_notes: Optional[str] = Field(
        None,
        description="Personal review or notes",
    )


class UserMediaCreate(UserMediaBase):
    """Schema for adding an item to the user's library."""
    media_id: uuid.UUID = Field(..., description="Target MediaItem ID")


class UserMediaUpdate(BaseModel):
    """Schema for updating an existing user library entry."""
    status: Optional[WatchStatus] = None
    is_favorite: Optional[bool] = None
    user_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    drop_reason: Optional[str] = Field(None, max_length=255)
    personal_notes: Optional[str] = None


class UserMediaResponse(UserMediaBase):
    """Schema for user library entry serialization."""
    id: uuid.UUID
    user_id: uuid.UUID
    media_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScoreCalculationResponse(BaseModel):
    """Response schema detailing calculated hybrid score results."""
    media_id: uuid.UUID
    imdb_score: Optional[float]
    user_avg_score: Optional[float]
    site_vote_count: int
    site_score: Optional[float]
    formula_applied: str

    model_config = ConfigDict(from_attributes=True)
