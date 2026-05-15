from datetime import date, datetime

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    content_id: int
    platform: str
    scheduled_at: datetime
    timezone: str = "Asia/Shanghai"


class ScheduleUpdate(BaseModel):
    scheduled_at: datetime
    timezone: str | None = None


class ScheduleResponse(BaseModel):
    id: int
    content_id: int
    content_title: str = ""
    platform: str
    scheduled_at: datetime
    timezone: str
    status: str
    published_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CalendarEntry(BaseModel):
    date: date
    entries: list[ScheduleResponse]


class CalendarStats(BaseModel):
    total: int = 0
    published: int = 0
    scheduled: int = 0
    draft: int = 0


class CalendarView(BaseModel):
    start_date: date
    end_date: date
    entries: list[CalendarEntry]
    stats: CalendarStats


class UpcomingSummary(BaseModel):
    items: list[ScheduleResponse]
    total: int


class SuggestedTime(BaseModel):
    time: datetime
    reason: str = ""


class SuggestTimesResponse(BaseModel):
    platform: str
    suggestions: list[SuggestedTime]
