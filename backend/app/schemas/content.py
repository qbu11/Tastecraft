from datetime import datetime

from pydantic import BaseModel


class ContentCreate(BaseModel):
    prompt: str
    platform: str = "xiaohongshu"
    project_id: int | None = None


class ContentUpdate(BaseModel):
    title: str | None = None
    body: str | None = None


class ContentResponse(BaseModel):
    id: int
    user_id: int
    project_id: int | None
    title: str
    body: str
    platform: str
    status: str
    taste_score: float | None
    created_at: datetime
    published_at: datetime | None

    model_config = {"from_attributes": True}


class ContentList(BaseModel):
    items: list[ContentResponse]
    total: int
