import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.unified_media import UnifiedMediaDTO


class UserIntentFilter(BaseModel):
    """Stage A: Extracted search intent and constraints parsed from natural language."""

    is_direct_title_search: bool = Field(
        default=False,
        description="True if the user is asking directly for a specific title by name",
    )
    direct_title: Optional[str] = Field(
        default=None,
        description="The specific title requested if is_direct_title_search is True",
    )
    media_type_filter: Literal["ALL", "ANIME", "MOVIE", "SERIES"] = Field(
        default="ALL",
        description="Target media category inferred from prompt",
    )
    mood_keywords: List[str] = Field(
        default_factory=list,
        description="Emotional tones or atmosphere (e.g., dark, melancholic, adrenaline, cozy)",
    )
    target_themes: List[str] = Field(
        default_factory=list,
        description="Thematic elements or subgenres (e.g., cyberpunk, time travel, revenge, psychological)",
    )
    excluded_tropes: List[str] = Field(
        default_factory=list,
        description="Clichés, tropes, or themes the user explicitly wishes to avoid (e.g., power of friendship, harem)",
    )
    reference_titles: List[str] = Field(
        default_factory=list,
        description="Comparable reference titles mentioned in prompt (e.g., 'like Inception')",
    )

    model_config = ConfigDict(from_attributes=True)


class RecommendationResultItem(BaseModel):
    """Single item recommendation output from LLM re-ranking."""
    selected_external_id: str = Field(
        ...,
        description="The external_id of the recommended media item",
    )
    confidence_score: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Confidence score for this selection",
    )
    justification_text: str = Field(
        ...,
        description="Personalized rationale (Max 2 sentences referencing user taste)",
    )

    model_config = ConfigDict(from_attributes=True)


class RecommendationResult(BaseModel):
    """Stage B: LLM re-ranking evaluation containing top recommendations."""

    recommendations: List[RecommendationResultItem] = Field(
        default_factory=list,
        description="List of selected media recommendations",
    )
    # Support backward compatibility if LLM returns a single object
    selected_external_id: Optional[str] = None
    confidence_score: Optional[float] = None
    justification_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def sync_recommendations_fields(self) -> "RecommendationResult":
        if self.recommendations and not self.selected_external_id:
            self.selected_external_id = self.recommendations[0].selected_external_id
            self.confidence_score = self.recommendations[0].confidence_score
            self.justification_text = self.recommendations[0].justification_text
        elif not self.recommendations and self.selected_external_id:
            self.recommendations.append(
                RecommendationResultItem(
                    selected_external_id=self.selected_external_id,
                    confidence_score=self.confidence_score or 0.95,
                    justification_text=self.justification_text or "",
                )
            )
        return self


class UserLibraryProfile(BaseModel):
    """Contextual profile of user favorites and dropped media for personalized ranking."""

    user_id: Optional[uuid.UUID] = None
    gold_list: List[str] = Field(
        default_factory=list,
        description="Titles the user loved/favorited (Altın Kutu / Başyapıtlar)",
    )
    red_list: List[str] = Field(
        default_factory=list,
        description="Titles the user dropped or disliked along with explicit drop reasons",
    )
    completed_titles: List[str] = Field(
        default_factory=list,
        description="Titles the user completed/watched (to exclude from recommendations)",
    )
    completed_ids: List[str] = Field(
        default_factory=list,
        description="External IDs of completed/watched items",
    )



class RecommendationRequest(BaseModel):
    """API request payload for generating a natural language recommendation."""

    prompt: str = Field(
        ...,
        min_length=2,
        description="Natural language discovery prompt in Turkish or English",
        examples=["Shounen klişesi içermeyen karanlık anime"],
    )
    user_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional User ID to load personalized Gold/Red lists",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=30,
        description="Candidate retrieval limit before re-ranking",
    )
    media_type: Optional[str] = Field(
        default=None,
        description="Optional media type filter: 'movie', 'tv' / 'series', 'anime', or 'all'",
        examples=["movie", "tv", "anime"],
    )


class SingleRecommendation(BaseModel):
    """A single recommended media item accompanied by AI personalized justification."""
    media: UnifiedMediaDTO = Field(
        ...,
        description="The recommended movie, TV series, or anime item",
    )
    justification: str = Field(
        ...,
        description="Tailored 2-sentence 'Neden Bu?' explanation",
    )
    confidence_score: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Match confidence score",
    )

    model_config = ConfigDict(from_attributes=True)


# Type aliases for modular architecture & semantic clarity
MediaItem = SingleRecommendation
MediaRecommendation = SingleRecommendation


class RecommendationResponse(BaseModel):
    """API response payload returning 5 recommended media items and justifications."""

    recommendations: List[SingleRecommendation] = Field(
        default_factory=list,
        description="List of 5 personalized recommendations with individual 2-sentence justifications",
    )
    recommended_media: Optional[UnifiedMediaDTO] = Field(
        default=None,
        description="First selected winning media item (for backward compatibility)",
    )
    justification: Optional[str] = Field(
        default=None,
        description="First personalized explanation (for backward compatibility)",
    )
    confidence_score: Optional[float] = Field(
        default=0.95,
        description="Match confidence score",
    )
    parsed_intent: UserIntentFilter = Field(
        ...,
        description="The parsed structured intent filter",
    )
    candidates_count: int = Field(
        ...,
        description="Total candidates evaluated by the engine",
    )
    all_candidates: List[UnifiedMediaDTO] = Field(
        default_factory=list,
        description="All candidates fetched for this query",
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def sync_legacy_fields(self) -> "RecommendationResponse":
        if self.recommendations:
            if self.recommended_media is None:
                self.recommended_media = self.recommendations[0].media
            if self.justification is None:
                self.justification = self.recommendations[0].justification
            if self.confidence_score is None:
                self.confidence_score = self.recommendations[0].confidence_score
        elif self.recommended_media is not None:
            self.recommendations.append(
                SingleRecommendation(
                    media=self.recommended_media,
                    justification=self.justification or "Öne çıkan öneri.",
                    confidence_score=self.confidence_score or 0.95,
                )
            )
        return self
