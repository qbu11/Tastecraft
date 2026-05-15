"""Analytics API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import (
    ContentMetrics,
    PerformanceSummary,
    PlatformComparison,
    TasteCorrelation,
    TimeSlot,
)
from app.services.analytics_collector import AnalyticsCollector

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=PerformanceSummary)
async def get_summary(
    days: int = Query(7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PerformanceSummary:
    """Performance overview with period comparison."""
    collector = AnalyticsCollector(db)
    return await collector.get_performance_summary(current_user.id, days)


@router.get("/content/{content_id}", response_model=list[ContentMetrics])
async def get_content_metrics(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContentMetrics]:
    """Get metric snapshots for a specific content piece."""
    collector = AnalyticsCollector(db)
    return await collector.get_content_metrics(content_id, current_user.id)


@router.get("/correlations", response_model=list[TasteCorrelation])
async def get_correlations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TasteCorrelation]:
    """Taste preference vs performance correlations."""
    collector = AnalyticsCollector(db)
    return await collector.compute_taste_correlation(current_user.id)


@router.get("/best-times", response_model=list[TimeSlot])
async def get_best_times(
    platform: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TimeSlot]:
    """Optimal posting times by platform."""
    collector = AnalyticsCollector(db)
    return await collector.get_best_posting_times(current_user.id, platform)


@router.get("/comparison", response_model=PlatformComparison)
async def get_comparison(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformComparison:
    """Cross-platform performance comparison."""
    collector = AnalyticsCollector(db)
    return await collector.get_platform_comparison(current_user.id)
