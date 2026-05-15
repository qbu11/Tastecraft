from datetime import datetime

from pydantic import BaseModel, Field


# ── Metrics ──


class ContentMetrics(BaseModel):
    content_id: int
    platform: str
    title: str | None = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0
    collection_type: str | None = None
    collected_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContentMetricsHistory(BaseModel):
    content_id: int
    title: str
    platform: str
    snapshots: list[ContentMetrics]


# ── Performance Summary ──


class PeriodDelta(BaseModel):
    """Comparison with previous period (absolute and %)."""

    current: int | float
    previous: int | float
    delta_pct: float = Field(
        description="Percentage change vs previous period"
    )


class PerformanceSummary(BaseModel):
    period_days: int
    total_views: PeriodDelta
    total_likes: PeriodDelta
    total_comments: PeriodDelta
    total_shares: PeriodDelta
    total_saves: PeriodDelta
    avg_engagement_rate: PeriodDelta
    total_published: PeriodDelta


# ── Taste Correlation ──


class TasteCorrelation(BaseModel):
    dimension: str
    rule: str
    metric: str = Field(description="e.g. engagement_rate, views")
    avg_with: float
    avg_without: float
    lift_pct: float = Field(description="Percentage lift when rule is present")
    sample_size: int


# ── Time Slot ──


class TimeSlot(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Mon, 6=Sun")
    hour: int = Field(ge=0, le=23)
    avg_engagement: float
    sample_size: int


# ── Platform Comparison ──


class PlatformStats(BaseModel):
    platform: str
    total_published: int
    total_views: int
    total_likes: int
    avg_engagement_rate: float
    best_content_title: str | None = None
    best_content_id: int | None = None


class PlatformComparison(BaseModel):
    platforms: list[PlatformStats]
