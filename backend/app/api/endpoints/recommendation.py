import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_optional_current_user
from app.models.user import User
from app.services.llm.recommendation_engine import RecommendationEngine
from app.services.llm.schemas import (
    RecommendationRequest,
    RecommendationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()
engine = RecommendationEngine()


@router.post(
    "",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate personalized media recommendation using AI pipeline",
    description="Processes natural language search query, parses intent, fetches candidates, and performs personalized re-ranking returning exactly 5 recommended media items with individual 2-sentence 'Neden Bu?' justifications.",
)
async def get_ai_recommendation(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> RecommendationResponse:
    """Natural language discovery endpoint running the 2-stage LLM recommendation pipeline."""
    target_user_id = request.user_id or (current_user.id if current_user else None)
    try:
        response = await engine.recommend(
            prompt=request.prompt,
            user_id=target_user_id,
            session=db,
            limit=request.limit,
            media_type=request.media_type,
        )
        return response
    except Exception as exc:
        logger.warning("Primary recommendation with DB session failed (%s), retrying in stateless mode", exc)
        try:
            return await engine.recommend(
                prompt=request.prompt,
                user_id=None,
                session=None,
                limit=request.limit,
                media_type=request.media_type,
            )
        except Exception as exc2:
            logger.error("Stateless fallback recommendation also failed: %s", exc2, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate recommendation: {str(exc2)}",
            )


@router.get(
    "/random",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="'Şansıma Güveniyorum' random masterpiece recommendation",
    description="Fetches a random universally acclaimed, high-scoring masterpiece from the library or discovery pool with an AI justification.",
)
async def get_random_recommendation(
    user_id: Optional[UUID] = Query(None, description="Optional user ID to exclude already saved/watched media"),
    media_type: Optional[str] = Query(None, description="Optional media type filter ('movie', 'tv', 'anime', 'all')"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> RecommendationResponse:

    """Random masterpiece discovery endpoint for the 'Şansıma Güveniyorum' feature."""
    target_user_id = user_id or (current_user.id if current_user else None)
    try:
        response = await engine.get_random_masterpiece(
            user_id=target_user_id,
            session=db,
            media_type=media_type,
        )
        return response
    except Exception as exc:
        logger.error("Error fetching random masterpiece recommendation: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch random recommendation: {str(exc)}",
        )
