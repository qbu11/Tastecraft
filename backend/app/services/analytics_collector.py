"""Analytics collection & aggregation service.

Fetches metrics from TikHub, computes engagement rates,
and provides dashboard aggregation queries.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analytics import Analytics
from app.models.content import Content
from app.models.taste_preference import TastePreference
from app.schemas.analytics import (
    ContentMetrics,
    PeriodDelta,
    PerformanceSummary,
    PlatformComparison,
    PlatformStats,
    TasteCorrelation,
    TimeSlot,
)

logger = logging.getLogger(__name__)


def _delta(current: int | float, previous: int | float) -> PeriodDelta:
    if previous == 0:
        pct = 100.0 if current > 0 else 0.0
    else:
        pct = round(((current - previous) / previous) * 100, 1)
    return PeriodDelta(current=current, previous=previous, delta_pct=pct)


class AnalyticsCollector:
    """Collect, store, and aggregate content performance metrics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Collection ──

    async def collect_metrics(
        self, content_id: int, platform: str, collection_type: str
    ) -> ContentMetrics:
        """Fetch current metrics for a published content piece via TikHub.

        Falls back to zero-valued stub when TikHub is unavailable.
        """
        metrics = await self._fetch_from_tikhub(content_id, platform)

        # Compute engagement rate
        total_interactions = (
            metrics["likes"]
            + metrics["comments"]
            + metrics["shares"]
            + metrics["saves"]
        )
        eng_rate = (
            round(total_interactions / metrics["views"] * 100, 2)
            if metrics["views"] > 0
            else 0.0
        )

        # Look up user_id from content
        result = await self.db.execute(
            select(Content.user_id).where(Content.id == content_id)
        )
        user_id = result.scalar_one()

        entry = Analytics(
            content_id=content_id,
            user_id=user_id,
            platform=platform,
            collection_type=collection_type,
            views=metrics["views"],
            likes=metrics["likes"],
            comments=metrics["comments"],
            shares=metrics["shares"],
            saves=metrics["saves"],
            engagement_rate=eng_rate,
        )
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)

        return ContentMetrics(
            content_id=content_id,
            platform=platform,
            views=entry.views,
            likes=entry.likes,
            comments=entry.comments,
            shares=entry.shares,
            saves=entry.saves,
            engagement_rate=entry.engagement_rate,
            collection_type=entry.collection_type,
            collected_at=entry.collected_at,
        )

    async def collect_all_pending(
        self, user_id: int
    ) -> list[ContentMetrics]:
        """Collect metrics for all content at their scheduled collection times."""
        now = datetime.now(timezone.utc)
        results: list[ContentMetrics] = []

        # Find published content that needs collection
        query = select(Content).where(
            Content.user_id == user_id,
            Content.status == "published",
            Content.published_at.is_not(None),
        )
        rows = await self.db.execute(query)
        contents = list(rows.scalars().all())

        for content in contents:
            published = content.published_at
            if published is None:
                continue

            elapsed = now - published.replace(tzinfo=timezone.utc)
            checkpoints = [
                ("t24h", timedelta(hours=24)),
                ("t72h", timedelta(hours=72)),
                ("t7d", timedelta(days=7)),
            ]
            for ctype, delta in checkpoints:
                if elapsed >= delta:
                    # Check if already collected
                    existing = await self.db.execute(
                        select(Analytics.id).where(
                            Analytics.content_id == content.id,
                            Analytics.collection_type == ctype,
                        )
                    )
                    if existing.scalar_one_or_none() is None:
                        try:
                            m = await self.collect_metrics(
                                content.id, content.platform, ctype
                            )
                            results.append(m)
                        except Exception:
                            logger.exception(
                                "Failed to collect %s for content %d",
                                ctype,
                                content.id,
                            )
        return results

    # ── Aggregation ──

    async def get_performance_summary(
        self, user_id: int, days: int = 7
    ) -> PerformanceSummary:
        """Aggregate performance stats for dashboard."""
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(days=days)
        previous_start = current_start - timedelta(days=days)

        async def _agg(start: datetime, end: datetime) -> dict:
            result = await self.db.execute(
                select(
                    func.coalesce(func.sum(Analytics.views), 0),
                    func.coalesce(func.sum(Analytics.likes), 0),
                    func.coalesce(func.sum(Analytics.comments), 0),
                    func.coalesce(func.sum(Analytics.shares), 0),
                    func.coalesce(func.sum(Analytics.saves), 0),
                    func.coalesce(func.avg(Analytics.engagement_rate), 0),
                ).where(
                    Analytics.user_id == user_id,
                    Analytics.collected_at >= start,
                    Analytics.collected_at < end,
                )
            )
            row = result.one()
            return {
                "views": int(row[0]),
                "likes": int(row[1]),
                "comments": int(row[2]),
                "shares": int(row[3]),
                "saves": int(row[4]),
                "eng": float(row[5]),
            }

        async def _count_published(start: datetime, end: datetime) -> int:
            result = await self.db.execute(
                select(func.count()).select_from(Content).where(
                    Content.user_id == user_id,
                    Content.status == "published",
                    Content.published_at >= start,
                    Content.published_at < end,
                )
            )
            return result.scalar_one()

        cur = await _agg(current_start, now)
        prev = await _agg(previous_start, current_start)
        cur_pub = await _count_published(current_start, now)
        prev_pub = await _count_published(previous_start, current_start)

        return PerformanceSummary(
            period_days=days,
            total_views=_delta(cur["views"], prev["views"]),
            total_likes=_delta(cur["likes"], prev["likes"]),
            total_comments=_delta(cur["comments"], prev["comments"]),
            total_shares=_delta(cur["shares"], prev["shares"]),
            total_saves=_delta(cur["saves"], prev["saves"]),
            avg_engagement_rate=_delta(
                round(cur["eng"], 2), round(prev["eng"], 2)
            ),
            total_published=_delta(cur_pub, prev_pub),
        )

    async def compute_taste_correlation(
        self, user_id: int
    ) -> list[TasteCorrelation]:
        """Correlate confirmed taste preferences with content performance.

        For each taste rule, compare avg engagement of content that
        matches the rule vs content that doesn't.
        """
        prefs_result = await self.db.execute(
            select(TastePreference).where(
                TastePreference.user_id == user_id,
                TastePreference.confirmed.is_(True),
            )
        )
        prefs = list(prefs_result.scalars().all())

        # Get all published content with analytics for this user
        analytics_q = (
            select(
                Analytics.content_id,
                Analytics.engagement_rate,
                Content.title,
                Content.body,
            )
            .join(Content, Content.id == Analytics.content_id)
            .where(
                Analytics.user_id == user_id,
                Analytics.collection_type == "t7d",
            )
        )
        rows = await self.db.execute(analytics_q)
        all_data = rows.all()

        if not all_data:
            return []

        correlations: list[TasteCorrelation] = []
        for pref in prefs:
            keyword = pref.rule.lower()
            matching = [r for r in all_data if keyword in (r[2] + r[3]).lower()]
            non_matching = [
                r for r in all_data if keyword not in (r[2] + r[3]).lower()
            ]

            if len(matching) < 2 or len(non_matching) < 1:
                continue

            avg_with = sum(r[1] for r in matching) / len(matching)
            avg_without = sum(r[1] for r in non_matching) / len(non_matching)
            lift = (
                round(((avg_with - avg_without) / avg_without) * 100, 1)
                if avg_without > 0
                else 0.0
            )

            correlations.append(
                TasteCorrelation(
                    dimension=pref.dimension,
                    rule=pref.rule,
                    metric="engagement_rate",
                    avg_with=round(avg_with, 2),
                    avg_without=round(avg_without, 2),
                    lift_pct=lift,
                    sample_size=len(matching),
                )
            )

        correlations.sort(key=lambda c: abs(c.lift_pct), reverse=True)
        return correlations[:20]

    async def get_best_posting_times(
        self, user_id: int, platform: str | None = None
    ) -> list[TimeSlot]:
        """Analyze historical data to find optimal posting times.

        Returns a 7x24 grid of average engagement rates.
        """
        query = (
            select(
                func.extract("dow", Content.published_at).label("dow"),
                func.extract("hour", Content.published_at).label("hour"),
                func.avg(Analytics.engagement_rate).label("avg_eng"),
                func.count().label("cnt"),
            )
            .join(Content, Content.id == Analytics.content_id)
            .where(
                Analytics.user_id == user_id,
                Content.published_at.is_not(None),
            )
        )
        if platform:
            query = query.where(Analytics.platform == platform)

        query = query.group_by("dow", "hour").order_by("dow", "hour")
        rows = await self.db.execute(query)

        return [
            TimeSlot(
                day_of_week=int(r[0]) if r[0] is not None else 0,
                hour=int(r[1]) if r[1] is not None else 0,
                avg_engagement=round(float(r[2]), 2),
                sample_size=int(r[3]),
            )
            for r in rows.all()
        ]

    async def get_platform_comparison(
        self, user_id: int
    ) -> PlatformComparison:
        """Cross-platform performance comparison."""
        query = (
            select(
                Analytics.platform,
                func.count(func.distinct(Analytics.content_id)).label("published"),
                func.coalesce(func.sum(Analytics.views), 0).label("views"),
                func.coalesce(func.sum(Analytics.likes), 0).label("likes"),
                func.coalesce(func.avg(Analytics.engagement_rate), 0).label("eng"),
            )
            .where(Analytics.user_id == user_id)
            .group_by(Analytics.platform)
        )
        rows = await self.db.execute(query)

        platforms: list[PlatformStats] = []
        for r in rows.all():
            # Find best content per platform
            best_q = (
                select(Analytics.content_id, Content.title)
                .join(Content, Content.id == Analytics.content_id)
                .where(
                    Analytics.user_id == user_id,
                    Analytics.platform == r[0],
                )
                .order_by(Analytics.engagement_rate.desc())
                .limit(1)
            )
            best = await self.db.execute(best_q)
            best_row = best.first()

            platforms.append(
                PlatformStats(
                    platform=r[0],
                    total_published=int(r[1]),
                    total_views=int(r[2]),
                    total_likes=int(r[3]),
                    avg_engagement_rate=round(float(r[4]), 2),
                    best_content_title=best_row[1] if best_row else None,
                    best_content_id=best_row[0] if best_row else None,
                )
            )

        return PlatformComparison(platforms=platforms)

    async def get_content_metrics(
        self, content_id: int, user_id: int
    ) -> list[ContentMetrics]:
        """Get all metric snapshots for a specific content piece."""
        result = await self.db.execute(
            select(Analytics)
            .where(
                Analytics.content_id == content_id,
                Analytics.user_id == user_id,
            )
            .order_by(Analytics.collected_at)
        )
        entries = list(result.scalars().all())

        # Get the content title
        title_result = await self.db.execute(
            select(Content.title).where(Content.id == content_id)
        )
        title = title_result.scalar_one_or_none() or ""

        return [
            ContentMetrics(
                content_id=e.content_id,
                platform=e.platform,
                title=title,
                views=e.views,
                likes=e.likes,
                comments=e.comments,
                shares=e.shares,
                saves=e.saves,
                engagement_rate=e.engagement_rate,
                collection_type=e.collection_type,
                collected_at=e.collected_at,
            )
            for e in entries
        ]

    # ── Internal ──

    async def _fetch_from_tikhub(
        self, content_id: int, platform: str
    ) -> dict:
        """Fetch metrics from TikHub API.

        Returns a dict with keys: views, likes, comments, shares, saves.
        Falls back to zeros if API key not configured or request fails.
        """
        if not settings.tikhub_api_key:
            logger.warning(
                "TikHub API key not set — returning stub metrics for content %d",
                content_id,
            )
            return {"views": 0, "likes": 0, "comments": 0, "shares": 0, "saves": 0}

        try:
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://api.tikhub.io/api/v1/{platform}/metrics",
                    params={"content_id": content_id},
                    headers={"Authorization": f"Bearer {settings.tikhub_api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "views": data.get("views", 0),
                        "likes": data.get("likes", 0),
                        "comments": data.get("comments", 0),
                        "shares": data.get("shares", 0),
                        "saves": data.get("saves", 0),
                    }
        except Exception:
            logger.exception("TikHub API call failed for content %d", content_id)

        return {"views": 0, "likes": 0, "comments": 0, "shares": 0, "saves": 0}
