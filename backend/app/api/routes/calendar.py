import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.calendar import (
    CalendarView,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
    SuggestTimesResponse,
    UpcomingSummary,
)
from app.services.scheduler import ContentScheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/", response_model=CalendarView)
async def get_calendar(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarView:
    """Get calendar entries for a date range."""
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be >= start_date")

    scheduler = ContentScheduler(db)
    return await scheduler.get_calendar_view(current_user.id, start_date, end_date)


@router.post("/schedule", response_model=ScheduleResponse, status_code=201)
async def schedule_content(
    payload: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduleResponse:
    """Schedule a content piece for future publication."""
    scheduler = ContentScheduler(db)
    try:
        schedule = await scheduler.schedule_content(
            content_id=payload.content_id,
            user_id=current_user.id,
            platform=payload.platform,
            scheduled_at=payload.scheduled_at,
            tz=payload.timezone,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Load content title
    content_title = ""
    if schedule.content:
        content_title = schedule.content.title

    return ScheduleResponse(
        id=schedule.id,
        content_id=schedule.content_id,
        content_title=content_title,
        platform=schedule.platform,
        scheduled_at=schedule.scheduled_at,
        timezone=schedule.timezone,
        status=schedule.status,
        published_at=schedule.published_at,
        error_message=schedule.error_message,
        created_at=schedule.created_at,
    )


@router.put("/schedule/{schedule_id}", response_model=ScheduleResponse)
async def reschedule_content(
    schedule_id: int,
    payload: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduleResponse:
    """Reschedule a content piece."""
    scheduler = ContentScheduler(db)
    try:
        schedule = await scheduler.reschedule(
            schedule_id=schedule_id,
            user_id=current_user.id,
            new_time=payload.scheduled_at,
            new_tz=payload.timezone,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    content_title = ""
    if schedule.content:
        content_title = schedule.content.title

    return ScheduleResponse(
        id=schedule.id,
        content_id=schedule.content_id,
        content_title=content_title,
        platform=schedule.platform,
        scheduled_at=schedule.scheduled_at,
        timezone=schedule.timezone,
        status=schedule.status,
        published_at=schedule.published_at,
        error_message=schedule.error_message,
        created_at=schedule.created_at,
    )


@router.delete("/schedule/{schedule_id}", status_code=204)
async def cancel_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Cancel a scheduled publication."""
    scheduler = ContentScheduler(db)
    try:
        success = await scheduler.cancel_schedule(schedule_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")


@router.get("/upcoming", response_model=UpcomingSummary)
async def get_upcoming(
    days: int = Query(7, ge=1, le=30, description="Number of days to look ahead"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UpcomingSummary:
    """Get upcoming scheduled content for the next N days."""
    scheduler = ContentScheduler(db)
    schedules = await scheduler.get_upcoming(current_user.id, days)

    items = []
    for s in schedules:
        content_title = ""
        if s.content:
            content_title = s.content.title
        items.append(
            ScheduleResponse(
                id=s.id,
                content_id=s.content_id,
                content_title=content_title,
                platform=s.platform,
                scheduled_at=s.scheduled_at,
                timezone=s.timezone,
                status=s.status,
                published_at=s.published_at,
                error_message=s.error_message,
                created_at=s.created_at,
            )
        )

    return UpcomingSummary(items=items, total=len(items))


@router.get("/suggest-times", response_model=SuggestTimesResponse)
async def suggest_times(
    platform: str = Query(..., description="Target platform"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuggestTimesResponse:
    """Suggest optimal posting times for a platform (placeholder)."""
    scheduler = ContentScheduler(db)
    return await scheduler.suggest_optimal_times(platform, current_user.id)
