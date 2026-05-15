"""Competitor monitoring API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.competitor import Competitor
from app.models.competitor_post import CompetitorPost
from app.models.user import User
from app.schemas.competitor import (
    CompetitorCreate,
    CompetitorList,
    CompetitorPostList,
    CompetitorPostResponse,
    CompetitorResponse,
    SyncResult,
    TrendReport,
    ViralAlert,
)
from app.services.competitor_tracker import CompetitorTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.post("/", response_model=CompetitorResponse, status_code=201)
async def add_competitor(
    payload: CompetitorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Competitor:
    """Add a competitor account to track."""
    competitor = Competitor(
        user_id=current_user.id,
        project_id=payload.project_id,
        platform=payload.platform,
        account_id=payload.account_id,
        account_name=payload.account_name,
        account_url=payload.account_url,
    )
    db.add(competitor)
    await db.flush()
    await db.refresh(competitor)
    return competitor


@router.get("/", response_model=CompetitorList)
async def list_competitors(
    project_id: int | None = Query(None),
    platform: str | None = Query(None),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List user's competitors with last sync time."""
    query = select(Competitor).where(Competitor.user_id == current_user.id)
    count_query = select(func.count()).select_from(Competitor).where(
        Competitor.user_id == current_user.id
    )

    if project_id is not None:
        query = query.where(Competitor.project_id == project_id)
        count_query = count_query.where(Competitor.project_id == project_id)
    if platform:
        query = query.where(Competitor.platform == platform)
        count_query = count_query.where(Competitor.platform == platform)

    query = query.order_by(Competitor.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    total_result = await db.execute(count_query)

    return {"items": list(result.scalars().all()), "total": total_result.scalar_one()}


@router.delete("/{competitor_id}", status_code=204)
async def remove_competitor(
    competitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a competitor (cascades to posts)."""
    result = await db.execute(
        select(Competitor).where(
            Competitor.id == competitor_id,
            Competitor.user_id == current_user.id,
        )
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    await db.delete(competitor)
    await db.flush()


@router.post("/{competitor_id}/sync", response_model=SyncResult)
async def sync_competitor(
    competitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncResult:
    """Force sync a specific competitor now."""
    # Verify ownership
    result = await db.execute(
        select(Competitor).where(
            Competitor.id == competitor_id,
            Competitor.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Competitor not found")

    tracker = CompetitorTracker(db)
    return await tracker.sync_competitor(competitor_id)


@router.post("/sync-all", response_model=list[SyncResult])
async def sync_all_competitors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SyncResult]:
    """Sync all competitors for the current user."""
    tracker = CompetitorTracker(db)
    return await tracker.sync_all_for_user(current_user.id)


@router.get("/trends", response_model=TrendReport)
async def get_trends(
    project_id: int | None = Query(None),
    period_days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrendReport:
    """Get current lane trend report."""
    tracker = CompetitorTracker(db)
    return await tracker.analyze_trends(
        user_id=current_user.id,
        project_id=project_id,
        period_days=period_days,
    )


@router.get("/viral", response_model=list[ViralAlert])
async def get_viral_posts(
    project_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ViralAlert]:
    """Get all viral posts across competitors."""
    query = (
        select(CompetitorPost)
        .join(Competitor)
        .where(
            Competitor.user_id == current_user.id,
            CompetitorPost.is_viral.is_(True),
        )
    )
    if project_id is not None:
        query = query.where(Competitor.project_id == project_id)

    query = query.order_by(
        (CompetitorPost.likes + CompetitorPost.comments + CompetitorPost.shares).desc()
    ).limit(limit)

    result = await db.execute(query)
    posts = list(result.scalars().all())

    # Build alerts with competitor info
    alerts = []
    for post in posts:
        comp_result = await db.execute(
            select(Competitor).where(Competitor.id == post.competitor_id)
        )
        competitor = comp_result.scalar_one_or_none()

        tracker = CompetitorTracker(db)
        avg = await tracker._get_avg_engagement(post.competitor_id)
        engagement = post.likes + post.comments + post.shares
        ratio = engagement / avg if avg > 0 else 0.0

        alerts.append(
            ViralAlert(
                post_id=post.id,
                competitor_name=competitor.account_name if competitor else "Unknown",
                platform=competitor.platform if competitor else "unknown",
                title=post.title,
                likes=post.likes,
                comments=post.comments,
                shares=post.shares,
                views=post.views,
                published_at=post.published_at,
                engagement_ratio=ratio,
            )
        )

    return alerts


@router.get("/{competitor_id}/posts", response_model=CompetitorPostList)
async def get_competitor_posts(
    competitor_id: int,
    skip: int = 0,
    limit: int = 20,
    viral_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get tracked posts for a specific competitor."""
    # Verify ownership
    comp_result = await db.execute(
        select(Competitor).where(
            Competitor.id == competitor_id,
            Competitor.user_id == current_user.id,
        )
    )
    if not comp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Competitor not found")

    query = select(CompetitorPost).where(CompetitorPost.competitor_id == competitor_id)
    count_query = select(func.count()).select_from(CompetitorPost).where(
        CompetitorPost.competitor_id == competitor_id
    )

    if viral_only:
        query = query.where(CompetitorPost.is_viral.is_(True))
        count_query = count_query.where(CompetitorPost.is_viral.is_(True))

    query = query.order_by(CompetitorPost.fetched_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    total_result = await db.execute(count_query)

    return {"items": list(result.scalars().all()), "total": total_result.scalar_one()}
