import logging

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "tastecraft",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="tastecraft.generate_content", bind=True, max_retries=2)
def generate_content_task(self, content_id: int, prompt: str, platform: str) -> dict:
    """Generate content via AI engine. Runs synchronously in Celery worker."""
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.models.content import Content
    from app.services.ai_engine import generate_content

    async def _run() -> dict:
        engine = create_async_engine(settings.database_url)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            result = await db.execute(select(Content).where(Content.id == content_id))
            content = result.scalar_one_or_none()
            if not content:
                return {"error": "Content not found"}

            try:
                generated = await generate_content(prompt, platform)
                lines = generated.strip().split("\n", 1)
                content.title = lines[0].lstrip("# ").strip()[:500]
                content.body = lines[1].strip() if len(lines) > 1 else ""
                content.status = "reviewing"
                await db.commit()
                return {"content_id": content_id, "status": "reviewing"}
            except Exception as exc:
                content.status = "failed"
                await db.commit()
                logger.exception("Content generation failed for %d", content_id)
                raise self.retry(exc=exc)
        await engine.dispose()

    return asyncio.run(_run())


@celery_app.task(name="tastecraft.publish_content", bind=True, max_retries=2)
def publish_content_task(self, content_id: int, platform: str) -> dict:
    """Publish content to platform. Placeholder for browser automation."""
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.models.content import Content

    async def _run() -> dict:
        engine = create_async_engine(settings.database_url)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            result = await db.execute(select(Content).where(Content.id == content_id))
            content = result.scalar_one_or_none()
            if not content:
                return {"error": "Content not found"}

            try:
                # TODO: integrate actual platform publishing (Playwright + cookie_manager)
                logger.info("Publishing content %d to %s", content_id, platform)
                content.status = "published"
                from datetime import datetime, timezone
                content.published_at = datetime.now(timezone.utc)
                await db.commit()
                return {"content_id": content_id, "status": "published", "platform": platform}
            except Exception as exc:
                content.status = "failed"
                await db.commit()
                logger.exception("Publish failed for %d", content_id)
                raise self.retry(exc=exc)
        await engine.dispose()

    return asyncio.run(_run())


@celery_app.task(name="tastecraft.sync_competitors", bind=True, max_retries=1)
def sync_competitors_task(self, user_id: int | None = None) -> dict:
    """Daily task: sync all competitor accounts.

    If user_id is provided, sync only that user's competitors.
    Otherwise, sync all users' competitors.
    """
    import asyncio

    from sqlalchemy import select as sa_select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.models.competitor import Competitor
    from app.services.competitor_tracker import CompetitorTracker

    async def _run() -> dict:
        db_engine = create_async_engine(settings.database_url)
        factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            tracker = CompetitorTracker(db)

            if user_id:
                results = await tracker.sync_all_for_user(user_id)
            else:
                user_ids_result = await db.execute(
                    sa_select(Competitor.user_id).distinct()
                )
                user_ids = [row[0] for row in user_ids_result.all()]
                results = []
                for uid in user_ids:
                    user_results = await tracker.sync_all_for_user(uid)
                    results.extend(user_results)

            await db.commit()

            summary = {
                "total_competitors": len(results),
                "successful": sum(1 for r in results if r.error is None),
                "failed": sum(1 for r in results if r.error is not None),
                "new_posts": sum(r.new_posts for r in results),
                "viral_detected": sum(r.viral_detected for r in results),
            }
            logger.info("Competitor sync complete: %s", summary)
            return summary

        await db_engine.dispose()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("Competitor sync task failed")
        raise self.retry(exc=exc)


@celery_app.task(name="tastecraft.analyze_trends", bind=True, max_retries=1)
def analyze_trends_task(self, user_id: int, project_id: int | None = None) -> dict:
    """After sync, run trend analysis for a user's competitors."""
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.services.competitor_tracker import CompetitorTracker

    async def _run() -> dict:
        db_engine = create_async_engine(settings.database_url)
        factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            tracker = CompetitorTracker(db)
            report = await tracker.analyze_trends(
                user_id=user_id, project_id=project_id
            )
            await db.commit()

            return {
                "user_id": user_id,
                "project_id": project_id,
                "topics_found": len(report.top_topics),
                "viral_posts": len(report.viral_posts),
                "posts_analyzed": report.total_posts_analyzed,
                "summary": report.summary,
            }

        await db_engine.dispose()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("Trend analysis task failed for user %d", user_id)
        raise self.retry(exc=exc)


# ── Analytics & Notification Tasks ──


@celery_app.task(name="tastecraft.collect_metrics", bind=True, max_retries=2)
def collect_metrics_task(
    self, content_id: int, platform: str, collection_type: str
) -> dict:
    """Collect metrics for a content piece. Scheduled at T+24h/T+72h/T+7d."""
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.services.analytics_collector import AnalyticsCollector

    async def _run() -> dict:
        eng = create_async_engine(settings.database_url)
        factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            try:
                collector = AnalyticsCollector(db)
                metrics = await collector.collect_metrics(
                    content_id, platform, collection_type
                )
                await db.commit()
                return {
                    "content_id": content_id,
                    "collection_type": collection_type,
                    "views": metrics.views,
                    "likes": metrics.likes,
                }
            except Exception as exc:
                await db.rollback()
                logger.exception(
                    "Metrics collection failed for content %d (%s)",
                    content_id,
                    collection_type,
                )
                raise self.retry(exc=exc)
        await eng.dispose()

    return asyncio.run(_run())


@celery_app.task(name="tastecraft.send_daily_digest")
def send_daily_digest_task(user_id: int) -> dict:
    """Generate and send daily digest. Runs daily at 08:30."""
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.services.notification_service import NotificationService

    async def _run() -> dict:
        eng = create_async_engine(settings.database_url)
        factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            svc = NotificationService(db)
            notif = await svc.send_daily_digest(user_id)
            await db.commit()
            return {"notification_id": notif.id, "type": "daily_digest"}
        await eng.dispose()

    return asyncio.run(_run())


@celery_app.task(name="tastecraft.send_weekly_evolution")
def send_weekly_evolution_task(user_id: int) -> dict:
    """Weekly taste evolution summary. Runs Sunday 20:00."""
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.services.notification_service import NotificationService

    async def _run() -> dict:
        eng = create_async_engine(settings.database_url)
        factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            svc = NotificationService(db)
            notif = await svc.send_evolution_weekly(user_id)
            await db.commit()
            return {"notification_id": notif.id, "type": "taste_evolution"}
        await eng.dispose()

    return asyncio.run(_run())


@celery_app.task(name="tastecraft.check_session_expiry")
def check_session_expiry_task(user_id: int) -> dict:
    """Check platform sessions and warn if expiring within 2 days."""
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.services.notification_service import NotificationService

    async def _run() -> dict:
        eng = create_async_engine(settings.database_url)
        factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            svc = NotificationService(db)
            warnings: list[str] = []
            for plat in ("xiaohongshu", "wechat"):
                # Placeholder: real check would inspect cookie expiry
                days_left = 999  # TODO: integrate cookie_manager
                if days_left <= 2:
                    await svc.send_session_expiry(user_id, plat, days_left)
                    warnings.append(plat)
            await db.commit()
            return {"warnings": warnings}
        await eng.dispose()

    return asyncio.run(_run())


# ── v2: Confidence Decay Task ──


@celery_app.task(name="tastecraft.apply_decay", bind=True)
def apply_decay_task(self) -> dict:
    """Apply confidence decay to all users' preferences.

    Runs weekly — preferences unused for 30+ days decay by 10% per week.
    User-confirmed preferences are exempt.
    """
    import asyncio

    from sqlalchemy import select as sa_select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.models.user import User
    from app.services.diff_engine import DiffEngine

    async def _run() -> dict:
        db_engine = create_async_engine(settings.database_url)
        factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

        total_affected = 0
        users_processed = 0

        async with factory() as db:
            result = await db.execute(sa_select(User.id))
            user_ids = [row[0] for row in result.all()]

            diff_engine = DiffEngine(db)
            for uid in user_ids:
                try:
                    affected = await diff_engine.apply_confidence_decay(str(uid))
                    total_affected += affected
                    users_processed += 1
                except Exception as exc:
                    logger.warning("Decay failed for user %d: %s", uid, exc)

            await db.commit()

        await db_engine.dispose()
        logger.info(
            "Decay task complete: %d users processed, %d preferences decayed",
            users_processed,
            total_affected,
        )
        return {
            "users_processed": users_processed,
            "total_preferences_affected": total_affected,
        }

    return asyncio.run(_run())


# ── Celery beat schedule ──

celery_app.conf.beat_schedule = {
    "daily-digest-0830": {
        "task": "tastecraft.send_daily_digest",
        "schedule": {"hour": 8, "minute": 30},
        "args": [],
    },
    "weekly-evolution-sunday-2000": {
        "task": "tastecraft.send_weekly_evolution",
        "schedule": {"hour": 20, "minute": 0, "day_of_week": 0},
        "args": [],
    },
    "check-session-expiry-daily": {
        "task": "tastecraft.check_session_expiry",
        "schedule": {"hour": 10, "minute": 0},
        "args": [],
    },
    "weekly-confidence-decay": {
        "task": "tastecraft.apply_decay",
        "schedule": {"hour": 3, "minute": 0, "day_of_week": 1},  # Monday 03:00
        "args": [],
    },
}
