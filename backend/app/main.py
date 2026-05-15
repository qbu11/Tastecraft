import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.calendar import router as calendar_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.content import router as content_router
from app.api.routes.generate import router as generate_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.onboarding import router as onboarding_router
from app.api.routes.publish import router as publish_router
from app.api.routes.session import router as session_router
from app.api.routes.taste import router as taste_router
from app.api.routes.vault import router as vault_router
from app.api.routes.visual import router as visual_router
from app.core.config import settings
from app.core.database import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("TasteCraft backend starting — env=%s", settings.app_env)
    yield
    await engine.dispose()
    logger.info("TasteCraft backend shutdown complete")


app = FastAPI(
    title="TasteCraft API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(calendar_router, prefix="/api/v1")
app.include_router(competitors_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(generate_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(publish_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")
app.include_router(taste_router, prefix="/api/v1")
app.include_router(vault_router, prefix="/api/v1")
app.include_router(visual_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
