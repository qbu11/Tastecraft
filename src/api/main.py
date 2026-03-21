"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.api.routes import health, content, tasks, analytics, dashboard, research, search
from pathlib import Path

app = FastAPI(
    title="Crew Media Ops API",
    description="Multi-agent system for social media operations",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Tailscale access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(content.router)
app.include_router(tasks.router)
app.include_router(analytics.router)
app.include_router(dashboard.router)
app.include_router(research.router)
app.include_router(search.router)

# Mount static files
static_dir = Path(__file__).parent.parent / "api" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application on startup."""
    import logging
    logging.basicConfig(level=logging.INFO)
    print(f"Crew Media Ops Dashboard starting on http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"Static files directory: {static_dir}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on shutdown."""
    print("Crew Media Ops shutting down")
