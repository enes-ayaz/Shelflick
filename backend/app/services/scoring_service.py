import logging
import uuid
from typing import Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaItem
from app.models.user_media import UserMedia

logger = logging.getLogger(__name__)


class ScoringService:
    """Business logic service for MediaPulse hybrid rating calculations.

    Mathematical Scoring Rules:
    - Rule 1: Community vote count == 0:
        Score = imdb_score (100% IMDb weight, 0% Community).
    - Rule 2: Community vote count between 1 and 20 (inclusive):
        Score = (imdb_score * 0.70) + (user_avg_score * 0.30).
    - Rule 3: Community vote count between 21 and 99 (inclusive):
        Score = (imdb_score * 0.30) + (user_avg_score * 0.70).
    - Rule 4: Community vote count >= 100:
        Score = user_avg_score (0% IMDb weight, fully independent community score).
    """

    MIN_SCORE: float = 1.0
    MAX_SCORE: float = 10.0

    @staticmethod
    def calculate_hybrid_score(
        imdb_score: Optional[float],
        site_vote_count: int,
        user_avg_score: Optional[float],
    ) -> Optional[float]:
        """Calculates the hybrid weighted score based on community volume.

        Args:
            imdb_score: Baseline IMDb score (0.0 to 10.0) or None.
            site_vote_count: Total community votes recorded.
            user_avg_score: Cumulative average of user votes.

        Returns:
            Calculated score rounded to 2 decimal places, or None if no score can be determined.
        """
        if site_vote_count < 0:
            raise ValueError("site_vote_count cannot be negative.")

        # Rule 1: No community votes yet -> 100% IMDb
        if site_vote_count == 0:
            return round(imdb_score, 2) if imdb_score is not None else None

        # If community votes exist, user_avg_score must be provided
        if user_avg_score is None:
            return round(imdb_score, 2) if imdb_score is not None else None

        # Clamp user average within valid bounds
        user_avg = max(ScoringService.MIN_SCORE, min(ScoringService.MAX_SCORE, user_avg_score))

        # Fallback if IMDb score is missing: rely 100% on community
        if imdb_score is None:
            return round(user_avg, 2)

        imdb = max(0.0, min(ScoringService.MAX_SCORE, imdb_score))

        # Rule 2: 1 to 20 community votes -> 70% IMDb, 30% Community
        if 1 <= site_vote_count <= 20:
            score = (imdb * 0.70) + (user_avg * 0.30)
            return round(score, 2)

        # Rule 3: 21 to 99 community votes -> 30% IMDb, 70% Community
        if 21 <= site_vote_count <= 99:
            score = (imdb * 0.30) + (user_avg * 0.70)
            return round(score, 2)

        # Rule 4: 100 or more community votes -> 100% Community
        return round(user_avg, 2)

    @classmethod
    def calculate_cumulative_user_average(
        cls,
        current_vote_count: int,
        current_site_score: Optional[float],
        imdb_score: Optional[float],
        new_user_score: float,
        known_previous_avg: Optional[float] = None,
    ) -> Tuple[float, int]:
        """Calculates updated cumulative user average and updated vote count.

        Args:
            current_vote_count: Existing community votes count (N).
            current_site_score: Existing hybrid site_score.
            imdb_score: IMDb baseline score.
            new_user_score: Newly submitted user score.
            known_previous_avg: If already calculated from DB, passes direct average.

        Returns:
            Tuple of (new_user_avg_score, new_vote_count).
        """
        if current_vote_count == 0 or current_site_score is None:
            return round(new_user_score, 4), 1

        new_vote_count = current_vote_count + 1

        # Use known previous average if available
        if known_previous_avg is not None:
            prev_avg = known_previous_avg
        else:
            # Reconstruct previous user average from hybrid score formula
            prev_avg = cls._reconstruct_user_average(
                vote_count=current_vote_count,
                site_score=current_site_score,
                imdb_score=imdb_score,
            )

        # Incremental cumulative moving average: A_new = (A_old * N + X) / (N + 1)
        new_user_avg = ((prev_avg * current_vote_count) + new_user_score) / new_vote_count
        return round(new_user_avg, 4), new_vote_count

    @classmethod
    def _reconstruct_user_average(
        cls,
        vote_count: int,
        site_score: float,
        imdb_score: Optional[float],
    ) -> float:
        """Helper to mathematically back-calculate user average from hybrid score."""
        if imdb_score is None:
            return site_score

        if 1 <= vote_count <= 20:
            # site_score = (imdb * 0.70) + (user_avg * 0.30)
            # user_avg = (site_score - 0.70 * imdb) / 0.30
            raw_avg = (site_score - (imdb_score * 0.70)) / 0.30
            return max(cls.MIN_SCORE, min(cls.MAX_SCORE, raw_avg))

        if 21 <= vote_count <= 99:
            # site_score = (imdb * 0.30) + (user_avg * 0.70)
            # user_avg = (site_score - 0.30 * imdb) / 0.70
            raw_avg = (site_score - (imdb_score * 0.30)) / 0.70
            return max(cls.MIN_SCORE, min(cls.MAX_SCORE, raw_avg))

        # vote_count >= 100: 100% community average
        return site_score

    @classmethod
    def apply_score_in_memory(
        cls,
        media_item: MediaItem,
        new_user_score: float,
        known_previous_avg: Optional[float] = None,
    ) -> float:
        """Applies a new user rating directly to a MediaItem instance in-memory.

        Args:
            media_item: Target MediaItem instance.
            new_user_score: Rating submitted by user (1.0 to 10.0).
            known_previous_avg: Optional known previous community average.

        Returns:
            The newly calculated site_score.
        """
        cls._validate_score(new_user_score)

        new_avg, new_count = cls.calculate_cumulative_user_average(
            current_vote_count=media_item.site_vote_count,
            current_site_score=media_item.site_score,
            imdb_score=media_item.imdb_score,
            new_user_score=new_user_score,
            known_previous_avg=known_previous_avg,
        )

        new_hybrid_score = cls.calculate_hybrid_score(
            imdb_score=media_item.imdb_score,
            site_vote_count=new_count,
            user_avg_score=new_avg,
        )

        media_item.site_vote_count = new_count
        media_item.site_score = new_hybrid_score
        return new_hybrid_score or 0.0

    @classmethod
    async def update_media_score(
        cls,
        session: AsyncSession,
        media_item: MediaItem,
        new_user_score: float,
        user_id: Optional[uuid.UUID] = None,
    ) -> MediaItem:
        """Applies a user rating and recalculates hybrid score within a database transaction.

        If user_id is provided, checks if an existing score is being edited or if this
        is a brand new score, querying exact database aggregations.

        Args:
            session: Active AsyncSession database transaction.
            media_item: Target MediaItem instance.
            new_user_score: Submitted score (1.0 to 10.0).
            user_id: Optional ID of the user submitting the score.

        Returns:
            The updated MediaItem instance.
        """
        cls._validate_score(new_user_score)

        if user_id is not None:
            # Query existing user record for this media within the transaction
            stmt = select(UserMedia).where(
                UserMedia.media_id == media_item.id,
                UserMedia.user_id == user_id,
            )
            result = await session.execute(stmt)
            user_media = result.scalars().first()

            if user_media is None:
                user_media = UserMedia(
                    user_id=user_id,
                    media_id=media_item.id,
                    user_score=new_user_score,
                )
                session.add(user_media)
            else:
                user_media.user_score = new_user_score

            await session.flush()

            # Query exact database community aggregations for this media
            agg_stmt = select(
                func.coalesce(func.avg(UserMedia.user_score), 0.0),
                func.count(UserMedia.id),
            ).where(
                UserMedia.media_id == media_item.id,
                UserMedia.user_score.is_not(None),
            )
            agg_result = await session.execute(agg_stmt)
            exact_avg, exact_count = agg_result.one()

            user_avg = float(exact_avg)
            vote_count = int(exact_count)
        else:
            # When direct score update is invoked without individual user tracking
            user_avg, vote_count = cls.calculate_cumulative_user_average(
                current_vote_count=media_item.site_vote_count,
                current_site_score=media_item.site_score,
                imdb_score=media_item.imdb_score,
                new_user_score=new_user_score,
            )

        new_hybrid_score = cls.calculate_hybrid_score(
            imdb_score=media_item.imdb_score,
            site_vote_count=vote_count,
            user_avg_score=user_avg,
        )

        media_item.site_vote_count = vote_count
        media_item.site_score = new_hybrid_score

        session.add(media_item)
        await session.flush()

        logger.info(
            "Recalculated hybrid score for MediaItem %s: site_score=%s, votes=%s, user_avg=%s",
            media_item.id,
            media_item.site_score,
            media_item.site_vote_count,
            round(user_avg, 2),
        )
        return media_item

    @classmethod
    def _validate_score(cls, score: float) -> None:
        """Validates that submitted score falls between MIN_SCORE and MAX_SCORE."""
        if score < cls.MIN_SCORE or score > cls.MAX_SCORE:
            raise ValueError(
                f"User score must be between {cls.MIN_SCORE} and {cls.MAX_SCORE}. Received: {score}"
            )


# Functional interface alias matching prompt requirements
async def update_media_score_transaction(
    session: AsyncSession,
    media_item: MediaItem,
    new_user_score: float,
) -> MediaItem:
    """Service function to update cumulative user average and hybrid site_score in transaction."""
    return await ScoringService.update_media_score(
        session=session,
        media_item=media_item,
        new_user_score=new_user_score,
    )
