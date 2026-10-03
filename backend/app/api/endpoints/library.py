import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_optional_current_user
from app.models.media import MediaItem, MediaSource
from app.models.user import User
from app.models.user_media import UserMedia, WatchStatus
from app.schemas.rating import UserMediaResponse
from app.schemas.unified_media import UnifiedMediaDTO

logger = logging.getLogger(__name__)

router = APIRouter()

DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_or_create_demo_user(session: AsyncSession) -> User:
    """Ensures a default demo user exists for seamless local/unauthenticated exploration."""
    stmt = select(User).where(User.id == DEMO_USER_ID)
    res = await session.execute(stmt)
    user = res.scalars().first()
    if not user:
        user = User(
            id=DEMO_USER_ID,
            username="demo_user",
            email="demo@shelflick.local",
            hashed_password="mock_password_hash",
        )
        session.add(user)
        await session.flush()
    return user


class AddToLibraryRequest(BaseModel):
    """Payload for adding or updating a media item in user's library."""
    user_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional User UUID. If omitted, uses default demo user.",
    )
    media: UnifiedMediaDTO = Field(..., description="Target media details to persist and link")
    status: WatchStatus = Field(
        default=WatchStatus.PLAN_TO_WATCH,
        description="Target shelf tracking status",
    )
    is_favorite: Optional[bool] = Field(
        default=None,
        description="Whether to mark as favorite for Altın Kutu",
    )
    user_score: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=10.0,
        description="User rating between 1.0 and 10.0",
    )
    personal_notes: Optional[str] = None
    drop_reason: Optional[str] = None


class LibraryItemDTO(BaseModel):
    id: uuid.UUID
    media_id: uuid.UUID
    external_id: str
    source: str
    title: str
    original_title: Optional[str] = None
    release_year: Optional[int] = None
    poster_url: str
    genres: List[str]
    themes: List[str]
    base_score: float
    status: WatchStatus
    is_favorite: bool
    user_score: Optional[float] = None
    personal_notes: Optional[str] = None
    drop_reason: Optional[str] = None



@router.post(
    "/items",
    response_model=LibraryItemDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update an item in the user's library",
)
async def add_to_library(
    payload: AddToLibraryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> LibraryItemDTO:
    """Saves a media item and creates/updates a UserMedia entry."""
    try:
        # 1. Resolve user: Authenticated JWT user ALWAYS takes top priority!
        if current_user:
            user_id = current_user.id
        elif payload.user_id and str(payload.user_id) != str(DEMO_USER_ID):
            user_id = payload.user_id
        else:
            user_id = DEMO_USER_ID
            await get_or_create_demo_user(db)

        # 2. Find or create MediaItem in database
        media_dto = payload.media
        try:
            source_enum = MediaSource(media_dto.source)
        except ValueError:
            source_enum = MediaSource.TMDB_MOVIE

        media_stmt = select(MediaItem).where(
            MediaItem.external_id == media_dto.external_id,
            MediaItem.media_source == source_enum,
        )
        res = await db.execute(media_stmt)
        db_media = res.scalars().first()

        if not db_media:
            db_media = MediaItem(
                id=uuid.uuid4(),
                external_id=media_dto.external_id,
                media_source=source_enum,
                title=media_dto.title,
                original_title=media_dto.original_title,
                release_year=media_dto.release_year,
                poster_url=media_dto.poster_url,
                synopsis=media_dto.synopsis,
                genres=media_dto.genres or [],
                themes=media_dto.themes or [],
                imdb_score=media_dto.base_score,
                site_score=media_dto.base_score,
                site_vote_count=media_dto.vote_count,
            )
            db.add(db_media)
            await db.flush()

        # 3. Find or create UserMedia link
        um_stmt = select(UserMedia).where(
            UserMedia.user_id == user_id,
            UserMedia.media_id == db_media.id,
        )
        um_res = await db.execute(um_stmt)
        user_media = um_res.scalars().first()

        if not user_media:
            user_media = UserMedia(
                id=uuid.uuid4(),
                user_id=user_id,
                media_id=db_media.id,
                status=payload.status,
                is_favorite=payload.is_favorite if payload.is_favorite is not None else False,
                user_score=payload.user_score,
                personal_notes=payload.personal_notes,
                drop_reason=payload.drop_reason,
            )
            db.add(user_media)
        else:
            user_media.status = payload.status
            if payload.is_favorite is not None:
                user_media.is_favorite = payload.is_favorite
            if payload.user_score is not None:
                user_media.user_score = payload.user_score
            if payload.personal_notes is not None:
                user_media.personal_notes = payload.personal_notes
            if payload.drop_reason is not None:
                user_media.drop_reason = payload.drop_reason

        await db.commit()
        await db.refresh(user_media)

        return LibraryItemDTO(
            id=user_media.id,
            media_id=db_media.id,
            external_id=db_media.external_id,
            source=db_media.media_source.value,
            title=db_media.title,
            original_title=db_media.original_title,
            release_year=db_media.release_year,
            poster_url=db_media.poster_url,
            genres=db_media.genres or [],
            themes=db_media.themes or [],
            base_score=db_media.site_score or db_media.imdb_score or 0.0,
            status=user_media.status,
            is_favorite=user_media.is_favorite,
            user_score=user_media.user_score,
            personal_notes=user_media.personal_notes,
            drop_reason=user_media.drop_reason,
        )

    except Exception as exc:
        await db.rollback()
        logger.error("Failed to add item to library: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Library action failed: {str(exc)}",
        )


@router.get(
    "/items",
    response_model=List[LibraryItemDTO],
    summary="Get user library items",
)
async def get_library_items(
    user_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[WatchStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> List[LibraryItemDTO]:
    """Retrieves all media items tracked in user's personal shelf."""
    try:
        if current_user:
            resolved_uid = current_user.id
        elif user_id and str(user_id) != str(DEMO_USER_ID):
            resolved_uid = user_id
        else:
            resolved_uid = DEMO_USER_ID

        stmt = (
            select(UserMedia, MediaItem)
            .join(MediaItem, UserMedia.media_id == MediaItem.id)
            .where(UserMedia.user_id == resolved_uid)
        )
        if status_filter:
            stmt = stmt.where(UserMedia.status == status_filter)

        stmt = stmt.order_by(UserMedia.updated_at.desc())
        res = await db.execute(stmt)
        rows = res.all()

        results: List[LibraryItemDTO] = []
        for um, mi in rows:
            results.append(
                LibraryItemDTO(
                    id=um.id,
                    media_id=mi.id,
                    external_id=mi.external_id,
                    source=mi.media_source.value,
                    title=mi.title,
                    original_title=mi.original_title,
                    release_year=mi.release_year,
                    poster_url=mi.poster_url,
                    genres=mi.genres or [],
                    themes=mi.themes or [],
                    base_score=mi.site_score or mi.imdb_score or 0.0,
                    status=um.status,
                    is_favorite=um.is_favorite,
                    user_score=um.user_score,
                    personal_notes=um.personal_notes,
                    drop_reason=um.drop_reason,
                )
            )
        return results
    except Exception as exc:
        logger.error("Failed to fetch library items: %s", exc, exc_info=True)
        return []


from fastapi import Response

@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item from user library",
)
async def delete_library_item(
    item_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Deletes a UserMedia entry by id or media_id."""
    if current_user:
        resolved_uid = current_user.id
    elif user_id and str(user_id) != str(DEMO_USER_ID):
        resolved_uid = user_id
    else:
        resolved_uid = DEMO_USER_ID

    stmt = select(UserMedia).where(
        (UserMedia.id == item_id) | (UserMedia.media_id == item_id),
        UserMedia.user_id == resolved_uid,
    )
    res = await db.execute(stmt)
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kütüphane kaydı bulunamadı.",
        )
    await db.delete(entry)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


