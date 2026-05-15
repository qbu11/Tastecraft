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
