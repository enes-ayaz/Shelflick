import asyncio
import logging
import uuid
from typing import Any, List, Optional
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
from app.services.external.anilist_client import AniListClient
from app.services.external.tmdb_client import TMDBClient

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
            name="Demo User",
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
    watched_episodes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total episodes watched by the user",
    )
    watched_seasons: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total seasons watched by the user",
    )


class LibraryItemDTO(BaseModel):
    id: uuid.UUID
    media_id: uuid.UUID
    external_id: str
    source: str
    title: str
    original_title: Optional[str] = None
    release_year: Optional[int] = None
    poster_url: str
    synopsis: Optional[str] = ""
    genres: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    base_score: float = 0.0
    status: WatchStatus = WatchStatus.PLAN_TO_WATCH
    is_favorite: bool = False
    user_score: Optional[float] = None
    personal_notes: Optional[str] = None
    drop_reason: Optional[str] = None
    runtime: Optional[int] = None
    total_episodes: Optional[int] = 1
    total_seasons: Optional[int] = None
    airing_status: Optional[str] = None
    next_airing_info: Optional[Any] = None
    watched_episodes: int = 0
    watched_seasons: int = 0


class WatchTimeFormatted(BaseModel):
    days: int
    hours: int
    minutes: int


class LibraryStatsResponse(BaseModel):
    total_watch_time_minutes: int
    total_watch_time_formatted: WatchTimeFormatted
    total_episodes_watched: int
    radar_items: List[LibraryItemDTO]


async def _enrich_media_details(media_dto: UnifiedMediaDTO) -> None:
    """Enriches media DTO with details from TMDB/AniList only if essential fields are missing.
    Skips external network calls if runtime or total_episodes are already present.
    Enforces a strict 1.5s timeout to prevent UI lag.
    """
    # 0ms Fast-path: If runtime or episode count is already populated, do not query external APIs!
    has_runtime = media_dto.runtime is not None and media_dto.runtime > 0
    has_episodes = media_dto.total_episodes is not None and media_dto.total_episodes > 1
    if has_runtime or has_episodes:
        return

    try:
        if media_dto.source == "ANILIST":
            async with AniListClient() as client:
                details = await asyncio.wait_for(
                    client.get_details(int(media_dto.external_id)),
                    timeout=1.5,
                )
                if details:
                    if media_dto.runtime is None:
                        media_dto.runtime = details.runtime
                    if media_dto.total_episodes is None or media_dto.total_episodes <= 1:
                        media_dto.total_episodes = details.total_episodes
                    if media_dto.airing_status is None:
                        media_dto.airing_status = details.airing_status
                    if media_dto.next_airing_info is None:
                        media_dto.next_airing_info = details.next_airing_info
        elif media_dto.source in ("TMDB_MOVIE", "TMDB_SERIES"):
            async with TMDBClient() as client:
                mtype = "movie" if media_dto.source == "TMDB_MOVIE" else "tv"
                details = await asyncio.wait_for(
                    client.get_details(mtype, int(media_dto.external_id) if str(media_dto.external_id).isdigit() else media_dto.external_id),
                    timeout=1.5,
                )
                if details:
                    if media_dto.runtime is None:
                        media_dto.runtime = details.runtime
                    if media_dto.total_episodes is None or (media_dto.source == "TMDB_SERIES" and media_dto.total_episodes <= 1):
                        media_dto.total_episodes = details.total_episodes
                    if media_dto.total_seasons is None:
                        media_dto.total_seasons = details.total_seasons
                    if media_dto.airing_status is None:
                        media_dto.airing_status = details.airing_status
                    if media_dto.next_airing_info is None:
                        media_dto.next_airing_info = details.next_airing_info
    except Exception as exc:
        logger.warning("Could not enrich media details for %s/%s: %s", media_dto.source, media_dto.external_id, exc)



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
        if current_user and hasattr(current_user, "id"):
            user_id = current_user.id
        elif payload.user_id and str(payload.user_id) != str(DEMO_USER_ID):
            user_exists = await db.scalar(select(User.id).where(User.id == payload.user_id))
            if user_exists:
                user_id = payload.user_id
            else:
                user_id = DEMO_USER_ID
                await get_or_create_demo_user(db)
        else:
            user_id = DEMO_USER_ID
            await get_or_create_demo_user(db)

        # 2. Enrich media details if missing (e.g. from search results)
        media_dto = payload.media
        await _enrich_media_details(media_dto)

        # 3. Find or create MediaItem in database
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
                external_id=str(media_dto.external_id),
                media_source=source_enum,
                title=media_dto.title or "Bilinmeyen Yapım",
                original_title=media_dto.original_title,
                release_year=media_dto.release_year,
                poster_url=media_dto.poster_url or "",
                synopsis=media_dto.synopsis or "",
                genres=media_dto.genres or [],
                themes=media_dto.themes or [],
                imdb_score=media_dto.base_score,
                site_score=media_dto.base_score,
                site_vote_count=media_dto.vote_count or 0,
                runtime=media_dto.runtime,
                total_episodes=media_dto.total_episodes if media_dto.total_episodes is not None else 1,
                total_seasons=media_dto.total_seasons,
                airing_status=media_dto.airing_status,
                next_airing_info=media_dto.next_airing_info,
            )
            db.add(db_media)
            await db.flush()
        else:
            # Backfill any missing fields if now available
            if media_dto.synopsis and not db_media.synopsis:
                db_media.synopsis = media_dto.synopsis
            if media_dto.poster_url and not db_media.poster_url:
                db_media.poster_url = media_dto.poster_url
            if media_dto.runtime is not None and db_media.runtime is None:
                db_media.runtime = media_dto.runtime
            if media_dto.total_episodes is not None and (db_media.total_episodes is None or db_media.total_episodes <= 1):
                db_media.total_episodes = media_dto.total_episodes
            if media_dto.total_seasons is not None and db_media.total_seasons is None:
                db_media.total_seasons = media_dto.total_seasons
            if media_dto.airing_status is not None and db_media.airing_status is None:
                db_media.airing_status = media_dto.airing_status
            if media_dto.next_airing_info is not None and db_media.next_airing_info is None:
                db_media.next_airing_info = media_dto.next_airing_info

        # 4. Resolve watched episode & season counts with automatic synchronization
        target_watched_episodes = payload.watched_episodes
        target_watched_seasons = payload.watched_seasons

        effective_total_episodes = db_media.total_episodes if (db_media.total_episodes and db_media.total_episodes > 0) else 1

        if payload.status == WatchStatus.COMPLETED:
            if target_watched_episodes is None:
                target_watched_episodes = effective_total_episodes
            if target_watched_seasons is None and db_media.total_seasons:
                target_watched_seasons = db_media.total_seasons

        # 5. Find or create UserMedia link
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
                watched_episodes=target_watched_episodes if target_watched_episodes is not None else 0,
                watched_seasons=target_watched_seasons if target_watched_seasons is not None else 0,
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

            if target_watched_episodes is not None:
                user_media.watched_episodes = target_watched_episodes
            elif payload.status == WatchStatus.COMPLETED and user_media.watched_episodes == 0:
                user_media.watched_episodes = effective_total_episodes

            if target_watched_seasons is not None:
                user_media.watched_seasons = target_watched_seasons
            elif payload.status == WatchStatus.COMPLETED and user_media.watched_seasons == 0 and db_media.total_seasons:
                user_media.watched_seasons = db_media.total_seasons

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
            synopsis=db_media.synopsis or "",
            genres=db_media.genres or [],
            themes=db_media.themes or [],
            base_score=db_media.site_score or db_media.imdb_score or 0.0,
            status=user_media.status,
            is_favorite=bool(user_media.is_favorite),
            user_score=user_media.user_score,
            personal_notes=user_media.personal_notes,
            drop_reason=user_media.drop_reason,
            runtime=db_media.runtime,
            total_episodes=db_media.total_episodes if db_media.total_episodes is not None else 1,
            total_seasons=db_media.total_seasons,
            airing_status=db_media.airing_status,
            next_airing_info=db_media.next_airing_info,
            watched_episodes=user_media.watched_episodes or 0,
            watched_seasons=user_media.watched_seasons or 0,
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
        real_user_id = user_id if isinstance(user_id, uuid.UUID) else None
        real_status_filter = status_filter if isinstance(status_filter, WatchStatus) else None

        if current_user and hasattr(current_user, "id"):
            resolved_uid = current_user.id
        elif real_user_id and str(real_user_id) != str(DEMO_USER_ID):
            user_exists = await db.scalar(select(User.id).where(User.id == real_user_id))
            resolved_uid = real_user_id if user_exists else DEMO_USER_ID
        else:
            resolved_uid = DEMO_USER_ID

        stmt = (
            select(UserMedia, MediaItem)
            .join(MediaItem, UserMedia.media_id == MediaItem.id)
            .where(UserMedia.user_id == resolved_uid)
        )
        if real_status_filter:
            stmt = stmt.where(UserMedia.status == real_status_filter)

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
                    synopsis=mi.synopsis or "",
                    genres=mi.genres or [],
                    themes=mi.themes or [],
                    base_score=mi.site_score or mi.imdb_score or 0.0,
                    status=um.status,
                    is_favorite=bool(um.is_favorite),
                    user_score=um.user_score,
                    personal_notes=um.personal_notes,
                    drop_reason=um.drop_reason,
                    runtime=mi.runtime,
                    total_episodes=mi.total_episodes if mi.total_episodes is not None else 1,
                    total_seasons=mi.total_seasons,
                    airing_status=mi.airing_status,
                    next_airing_info=mi.next_airing_info,
                    watched_episodes=um.watched_episodes or 0,
                    watched_seasons=um.watched_seasons or 0,
                )
            )
        return results
    except Exception as exc:
        logger.error("Failed to fetch library items: %s", exc, exc_info=True)
        return []


@router.get(
    "/stats",
    response_model=LibraryStatsResponse,
    summary="Get user watch time statistics and season radar",
)
async def get_library_stats(
    user_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> LibraryStatsResponse:
    """Calculates cumulative watch time and discovers upcoming episodes/seasons radar items."""
    try:
        real_user_id = user_id if isinstance(user_id, uuid.UUID) else None
        if current_user and hasattr(current_user, "id"):
            resolved_uid = current_user.id
        elif real_user_id and str(real_user_id) != str(DEMO_USER_ID):
            user_exists = await db.scalar(select(User.id).where(User.id == real_user_id))
            resolved_uid = real_user_id if user_exists else DEMO_USER_ID
        else:
            resolved_uid = DEMO_USER_ID

        stmt = (
            select(UserMedia, MediaItem)
            .join(MediaItem, UserMedia.media_id == MediaItem.id)
            .where(UserMedia.user_id == resolved_uid)
            .order_by(UserMedia.updated_at.desc())
        )
        res = await db.execute(stmt)
        rows = res.all()

        total_watch_time_minutes = 0
        total_episodes_watched = 0
        radar_items: List[LibraryItemDTO] = []

        for um, mi in rows:
            watched_eps = um.watched_episodes or 0
            total_episodes_watched += watched_eps

            # Runtime calculation with defaults: movies 120m, series 45m, anime 24m
            if mi.runtime and mi.runtime > 0:
                item_runtime = mi.runtime
            else:
                if mi.media_source == MediaSource.TMDB_MOVIE:
                    item_runtime = 120
                elif mi.media_source == MediaSource.TMDB_SERIES:
                    item_runtime = 45
                elif mi.media_source == MediaSource.ANILIST:
                    item_runtime = 24
                else:
                    item_runtime = 45

            total_watch_time_minutes += (watched_eps * item_runtime)

            # Radar filter: user is WATCHING, PLAN_TO_WATCH, or COMPLETED, and item has next info or is ongoing
            if um.status in (WatchStatus.WATCHING, WatchStatus.PLAN_TO_WATCH, WatchStatus.COMPLETED):
                has_next = mi.next_airing_info is not None and bool(mi.next_airing_info)
                status_raw = (mi.airing_status or "").strip().lower()
                is_ongoing = status_raw in (
                    "returning series",
                    "releasing",
                    "in production",
                    "planned",
                    "not_yet_released",
                ) or (
                    bool(status_raw)
                    and status_raw not in ("ended", "finished", "canceled", "cancelled", "released")
                )

                if is_ongoing or has_next:
                    radar_items.append(
                        LibraryItemDTO(
                            id=um.id,
                            media_id=mi.id,
                            external_id=mi.external_id,
                            source=mi.media_source.value,
                            title=mi.title,
                            original_title=mi.original_title,
                            release_year=mi.release_year,
                            poster_url=mi.poster_url,
                            synopsis=mi.synopsis or "",
                            genres=mi.genres or [],
                            themes=mi.themes or [],
                            base_score=mi.site_score or mi.imdb_score or 0.0,
                            status=um.status,
                            is_favorite=bool(um.is_favorite),
                            user_score=um.user_score,
                            personal_notes=um.personal_notes,
                            drop_reason=um.drop_reason,
                            runtime=mi.runtime,
                            total_episodes=mi.total_episodes if mi.total_episodes is not None else 1,
                            total_seasons=mi.total_seasons,
                            airing_status=mi.airing_status,
                            next_airing_info=mi.next_airing_info,
                            watched_episodes=um.watched_episodes or 0,
                            watched_seasons=um.watched_seasons or 0,
                        )
                    )

        days = total_watch_time_minutes // 1440
        remainder = total_watch_time_minutes % 1440
        hours = remainder // 60
        minutes = remainder % 60

        return LibraryStatsResponse(
            total_watch_time_minutes=total_watch_time_minutes,
            total_watch_time_formatted=WatchTimeFormatted(
                days=days,
                hours=hours,
                minutes=minutes,
            ),
            total_episodes_watched=total_episodes_watched,
            radar_items=radar_items,
        )

    except Exception as exc:
        logger.error("Failed to calculate library stats: %s", exc, exc_info=True)
        return LibraryStatsResponse(
            total_watch_time_minutes=0,
            total_watch_time_formatted=WatchTimeFormatted(days=0, hours=0, minutes=0),
            total_episodes_watched=0,
            radar_items=[],
        )


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
    real_user_id = user_id if isinstance(user_id, uuid.UUID) else None
    if current_user and hasattr(current_user, "id"):
        resolved_uid = current_user.id
    elif real_user_id and str(real_user_id) != str(DEMO_USER_ID):
        user_exists = await db.scalar(select(User.id).where(User.id == real_user_id))
        resolved_uid = real_user_id if user_exists else DEMO_USER_ID
    else:
        resolved_uid = DEMO_USER_ID

    stmt = select(UserMedia).where(
        (UserMedia.id == item_id) | (UserMedia.media_id == item_id),
        (UserMedia.user_id == resolved_uid) | (UserMedia.user_id == DEMO_USER_ID),
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


