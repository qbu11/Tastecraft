"""Celery app with fallback for dev mode (no Redis required).

When Redis is unavailable, tasks run as synchronous no-op stubs
so the app can start and be tested without a broker.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_USE_CELERY = True

try:
    import redis as redis_lib

    # Quick connectivity check — does not block long
    _r = redis_lib.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
    _r.ping()
    _r.close()
except Exception:
    _USE_CELERY = False
    logger.warning(
        "Redis unavailable at %s — Celery disabled, tasks will be no-op stubs.",
        settings.redis_url,
    )


if _USE_CELERY:
    from celery import Celery

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
        """Daily task: sync all competitor accounts."""
        return {"status": "skipped", "reason": "placeholder"}

    @celery_app.task(name="tastecraft.analyze_trends", bind=True, max_retries=1)
    def analyze_trends_task(self, user_id: int, project_id: int | None = None) -> dict:
        """After sync, run trend analysis for a user's competitors."""
        return {"status": "skipped", "reason": "placeholder"}

    @celery_app.task(name="tastecraft.collect_metrics", bind=True, max_retries=2)
    def collect_metrics_task(
        self, content_id: int, platform: str, collection_type: str
    ) -> dict:
        """Collect metrics for a content piece."""
        return {"status": "skipped", "reason": "placeholder"}

    @celery_app.task(name="tastecraft.send_daily_digest")
    def send_daily_digest_task(user_id: int) -> dict:
        return {"status": "skipped", "reason": "placeholder"}

    @celery_app.task(name="tastecraft.send_weekly_evolution")
    def send_weekly_evolution_task(user_id: int) -> dict:
        return {"status": "skipped", "reason": "placeholder"}

    @celery_app.task(name="tastecraft.check_session_expiry")
    def check_session_expiry_task(user_id: int) -> dict:
        return {"status": "skipped", "reason": "placeholder"}

    @celery_app.task(name="tastecraft.apply_decay", bind=True)
    def apply_decay_task(self) -> dict:
        return {"status": "skipped", "reason": "placeholder"}

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
            "schedule": {"hour": 3, "minute": 0, "day_of_week": 1},
            "args": [],
        },
    }

else:
    # ── Dev-mode stubs: no Redis, tasks are synchronous no-ops ──

    class _FakeCeleryApp:
        """Minimal stub so imports like `from app.tasks.celery_app import celery_app` work."""

        conf = type("Conf", (), {"beat_schedule": {}, "update": lambda self, **kw: None})()

        def task(self, *args, **kwargs):
            def decorator(fn):
                fn.delay = lambda *a, **kw: logger.info(
                    "DEV STUB: %s called (no-op)", fn.__name__
                )
                fn.apply_async = fn.delay
                return fn

            return decorator

    celery_app = _FakeCeleryApp()  # type: ignore[assignment]

    def generate_content_task(content_id: int, prompt: str, platform: str) -> dict:
        logger.info("DEV STUB: generate_content_task(%d) — skipped", content_id)
        return {"status": "dev_stub"}

    generate_content_task.delay = lambda *a, **kw: None  # type: ignore[attr-defined]
    generate_content_task.apply_async = generate_content_task.delay  # type: ignore[attr-defined]

    def publish_content_task(content_id: int, platform: str) -> dict:
        logger.info("DEV STUB: publish_content_task(%d) — skipped", content_id)
        return {"status": "dev_stub"}

    publish_content_task.delay = lambda *a, **kw: None  # type: ignore[attr-defined]
    publish_content_task.apply_async = publish_content_task.delay  # type: ignore[attr-defined]

    def sync_competitors_task(user_id: int | None = None) -> dict:
        return {"status": "dev_stub"}

    sync_competitors_task.delay = lambda *a, **kw: None  # type: ignore[attr-defined]

    def analyze_trends_task(user_id: int, project_id: int | None = None) -> dict:
        return {"status": "dev_stub"}

    analyze_trends_task.delay = lambda *a, **kw: None  # type: ignore[attr-defined]

    def collect_metrics_task(content_id: int, platform: str, collection_type: str) -> dict:
        return {"status": "dev_stub"}

    collect_metrics_task.delay = lambda *a, **kw: None  # type: ignore[attr-defined]

    def send_daily_digest_task(user_id: int) -> dict:
        return {"status": "dev_stub"}

    send_daily_digest_task.delay = lambda *a, **kw: None  # type: ignore[attr-defined]

    def send_weekly_evolution_task(user_id: int) -> dict:
        return {"status": "dev_stub"}

    send_weekly_evolution_task.delay = lambda *a, **kw: None  # type: ignore[attr-defined]

    def check_session_expiry_task(user_id: int) -> dict:
        return {"status": "dev_stub"}

    check_session_expiry_task.delay = lambda *a, **kw: None  # type: ignore[attr-defined]

    def apply_decay_task() -> dict:
        return {"status": "dev_stub"}

    apply_decay_task.delay = lambda *a, **kw: None  # type: ignore[attr-defined]
