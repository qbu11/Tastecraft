from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ──


class CompetitorCreate(BaseModel):
    platform: str = Field(
        ..., description="Platform: xiaohongshu, wechat, weibo, zhihu, douyin"
    )
    account_id: str = Field(..., description="Platform-specific account ID")
    account_name: str = Field(..., description="Display name of the account")
    account_url: str | None = Field(None, description="Profile URL on the platform")
    project_id: int | None = Field(None, description="Associated project ID")


# ── Response schemas ──


class CompetitorResponse(BaseModel):
    id: int
    user_id: int
    project_id: int | None
    platform: str
    account_id: str
    account_name: str
    account_url: str | None
    last_synced_at: datetime | None
    total_posts_tracked: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CompetitorPostResponse(BaseModel):
    id: int
    competitor_id: int
    platform_post_id: str
    title: str | None
    content_text: str | None
    media_urls: list[str] | None = None
    tags: list[str] | None = None
    likes: int
    comments: int
    shares: int
    views: int
    published_at: datetime | None
    fetched_at: datetime
    is_viral: bool

    model_config = {"from_attributes": True}


class CompetitorPostList(BaseModel):
    items: list[CompetitorPostResponse]
    total: int


class CompetitorList(BaseModel):
    items: list[CompetitorResponse]
    total: int


# ── Trend report ──


class TrendingTopic(BaseModel):
    topic: str
    frequency: int = Field(description="How many posts reference this topic")
    avg_engagement: float = Field(description="Average likes+comments+shares")
    example_titles: list[str] = Field(default_factory=list)


class ViralAlert(BaseModel):
    post_id: int
    competitor_name: str
    platform: str
    title: str | None
    likes: int
    comments: int
    shares: int
    views: int
    published_at: datetime | None
    engagement_ratio: float = Field(description="Engagement vs competitor average")


class TrendReport(BaseModel):
    project_id: int | None = None
    generated_at: datetime
    period_days: int = 7
    top_topics: list[TrendingTopic] = Field(default_factory=list)
    viral_posts: list[ViralAlert] = Field(default_factory=list)
    total_posts_analyzed: int = 0
    summary: str = ""


# ── Sync result ──


class SyncResult(BaseModel):
    competitor_id: int
    competitor_name: str
    platform: str
    new_posts: int = 0
    updated_posts: int = 0
    viral_detected: int = 0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None
