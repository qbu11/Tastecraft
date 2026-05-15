import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content
from app.models.schedule import Schedule
from app.schemas.calendar import (
    CalendarEntry,
    CalendarStats,
    CalendarView,
    ScheduleResponse,
    SuggestedTime,
    SuggestTimesResponse,
)

logger = logging.getLogger(__name__)

# Platform-specific optimal posting hours (Asia/Shanghai)
_OPTIMAL_HOURS: dict[str, list[int]] = {
    "xiaohongshu": [12, 18, 21],
    "wechat": [8, 12, 20],
    "weibo": [9, 12, 18, 22],
    "zhihu": [10, 14, 21],
    "douyin": [12, 18, 21],
    "bilibili": [11, 17, 20],
}


class ContentScheduler:
    """Service for scheduling content publication."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def schedule_content(
        self,
        content_id: int,
        user_id: int,
        platform: str,
        scheduled_at: datetime,
        tz: str = "Asia/Shanghai",
    ) -> Schedule:
        """Schedule content for future publication."""
        # Verify content exists and belongs to user
        result = await self.db.execute(
            select(Content).where(
                Content.id == content_id,
                Content.user_id == user_id,
            )
        )
        content = result.scalar_one_or_none()
        if not content:
            raise ValueError(f"Content {content_id} not found or access denied")

        schedule = Schedule(
            content_id=content_id,
            user_id=user_id,
            platform=platform,
            scheduled_at=scheduled_at,
            timezone=tz,
            status="pending",
        )
        self.db.add(schedule)
        await self.db.flush()
        await self.db.refresh(schedule)

        logger.info(
            "Scheduled content %d for %s at %s",
            content_id,
            platform,
            scheduled_at.isoformat(),
        )
        return schedule

    async def cancel_schedule(self, schedule_id: int, user_id: int) -> bool:
        """Cancel a scheduled publication."""
        result = await self.db.execute(
            select(Schedule).where(
                Schedule.id == schedule_id,
                Schedule.user_id == user_id,
            )
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            return False

        if schedule.status != "pending":
            raise ValueError(f"Cannot cancel schedule in '{schedule.status}' status")

        schedule.status = "cancelled"
        await self.db.flush()
        logger.info("Cancelled schedule %d", schedule_id)
        return True

    async def reschedule(
        self,
        schedule_id: int,
        user_id: int,
        new_time: datetime,
        new_tz: str | None = None,
    ) -> Schedule:
        """Move scheduled publication to a new time."""
        result = await self.db.execute(
            select(Schedule).where(
                Schedule.id == schedule_id,
                Schedule.user_id == user_id,
            )
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        if schedule.status != "pending":
            raise ValueError(f"Cannot reschedule in '{schedule.status}' status")

        schedule.scheduled_at = new_time
        if new_tz is not None:
            schedule.timezone = new_tz
        await self.db.flush()
        await self.db.refresh(schedule)

        logger.info("Rescheduled %d to %s", schedule_id, new_time.isoformat())
        return schedule

    async def get_upcoming(self, user_id: int, days: int = 7) -> list[Schedule]:
        """Get all scheduled content for next N days."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days)

        result = await self.db.execute(
            select(Schedule)
            .where(
                Schedule.user_id == user_id,
                Schedule.status == "pending",
                Schedule.scheduled_at >= now,
                Schedule.scheduled_at <= cutoff,
            )
            .order_by(Schedule.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def get_calendar_view(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> CalendarView:
        """Get calendar entries (published + scheduled + drafts) for date range."""
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Fetch schedules in range
        sched_result = await self.db.execute(
            select(Schedule)
            .where(
                Schedule.user_id == user_id,
                Schedule.scheduled_at >= start_dt,
                Schedule.scheduled_at <= end_dt,
            )
            .order_by(Schedule.scheduled_at.asc())
        )
        schedules = list(sched_result.scalars().all())

        # Fetch content titles for scheduled items
        content_ids = {s.content_id for s in schedules}
        content_titles: dict[int, str] = {}
        if content_ids:
            content_result = await self.db.execute(
                select(Content.id, Content.title).where(Content.id.in_(content_ids))
            )
            for row in content_result:
                content_titles[row[0]] = row[1]

        # Also fetch published content directly (not via schedules)
        published_result = await self.db.execute(
            select(Content).where(
                Content.user_id == user_id,
                Content.status == "published",
                Content.published_at >= start_dt,
                Content.published_at <= end_dt,
            )
        )
        published_contents = list(published_result.scalars().all())

        # Also fetch drafts created in range
        draft_result = await self.db.execute(
            select(Content).where(
                Content.user_id == user_id,
                Content.status == "draft",
                Content.created_at >= start_dt,
                Content.created_at <= end_dt,
            )
        )
        draft_contents = list(draft_result.scalars().all())

        # Build entries grouped by date
        entries_by_date: dict[date, list[ScheduleResponse]] = defaultdict(list)
        scheduled_content_ids: set[int] = set()

        # Add scheduled items
        for s in schedules:
            d = s.scheduled_at.date()
            entries_by_date[d].append(
                ScheduleResponse(
                    id=s.id,
                    content_id=s.content_id,
                    content_title=content_titles.get(s.content_id, ""),
                    platform=s.platform,
                    scheduled_at=s.scheduled_at,
                    timezone=s.timezone,
                    status=s.status,
                    published_at=s.published_at,
                    error_message=s.error_message,
                    created_at=s.created_at,
                )
            )
            scheduled_content_ids.add(s.content_id)

        # Add published content not already covered by schedules
        for c in published_contents:
            if c.id not in scheduled_content_ids and c.published_at:
                d = c.published_at.date()
                entries_by_date[d].append(
                    ScheduleResponse(
                        id=0,
                        content_id=c.id,
                        content_title=c.title,
                        platform=c.platform,
                        scheduled_at=c.published_at,
                        timezone="Asia/Shanghai",
                        status="published",
                        published_at=c.published_at,
                        created_at=c.created_at,
                    )
                )

        # Add drafts
        for c in draft_contents:
            if c.id not in scheduled_content_ids:
                d = c.created_at.date()
                entries_by_date[d].append(
                    ScheduleResponse(
                        id=0,
                        content_id=c.id,
                        content_title=c.title,
                        platform=c.platform,
                        scheduled_at=c.created_at,
                        timezone="Asia/Shanghai",
                        status="draft",
                        created_at=c.created_at,
                    )
                )

        # Build sorted calendar entries
        all_dates = sorted(entries_by_date.keys())
        calendar_entries = [
            CalendarEntry(date=d, entries=entries_by_date[d]) for d in all_dates
        ]

        # Compute stats
        all_items = [e for ce in calendar_entries for e in ce.entries]
        stats = CalendarStats(
            total=len(all_items),
            published=sum(1 for e in all_items if e.status == "published"),
            scheduled=sum(1 for e in all_items if e.status == "pending"),
            draft=sum(1 for e in all_items if e.status == "draft"),
        )

        return CalendarView(
            start_date=start_date,
            end_date=end_date,
            entries=calendar_entries,
            stats=stats,
        )

    async def suggest_optimal_times(
        self,
        platform: str,
        user_id: int,
    ) -> SuggestTimesResponse:
        """Suggest best posting times based on platform defaults.

        MVP placeholder: returns static optimal hours per platform.
        Future: analyze past performance data.
        """
        hours = _OPTIMAL_HOURS.get(platform, [12, 18, 21])
        tomorrow = date.today() + timedelta(days=1)

        suggestions = [
            SuggestedTime(
                time=datetime.combine(tomorrow, datetime.min.time()).replace(hour=h),
                reason=f"{platform} 用户活跃高峰时段",
            )
            for h in hours
        ]

        return SuggestTimesResponse(platform=platform, suggestions=suggestions)
