"""Onboarding API routes — conversational onboarding flow for building taste vaults."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.onboarding_session import OnboardingSession
from app.models.user import User
from app.schemas.onboarding import (
    AIResponse,
    CompetitorAddRequest,
    ContentImportRequest,
    OnboardingComplete,
    OnboardingMessage,
    OnboardingSessionResponse,
    OnboardingStart,
    OnboardingStatus,
    StyleAnalysis,
)
from app.services.onboarding_engine import onboarding_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/start", response_model=OnboardingSessionResponse)
async def start_onboarding(
    payload: OnboardingStart,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingSessionResponse:
    """Initialize a new onboarding session for the current user."""
    # Check for existing incomplete session
    result = await db.execute(
        select(OnboardingSession).where(
            OnboardingSession.user_id == current_user.id,
            OnboardingSession.completed_at.is_(None),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Return existing session instead of creating new one
        messages = existing.messages or []
        last_ai_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                last_ai_msg = msg["content"]
                break

        return OnboardingSessionResponse(
            session_id=existing.id,
            first_message=last_ai_msg or "让我们继续上次的对话吧！",
            current_step=existing.current_step,
            step_index=existing.step_index,
            quick_replies=[],
            created_at=existing.created_at,
        )

    # Start new session
    session_result = await onboarding_engine.start_session(current_user.id)

    # Persist to database
    session = OnboardingSession(
        id=session_result["session_id"],
        user_id=current_user.id,
        current_step=session_result["session_data"]["current_step"],
        step_index=0,
        messages=session_result["session_data"]["messages"],
        collected_data={},
        imported_content_urls=[],
        imported_content_count=0,
        competitors_added=0,
        competitor_urls=[],
    )
    db.add(session)
    await db.flush()

    return OnboardingSessionResponse(
        session_id=session.id,
        first_message=session_result["first_message"],
        current_step=session.current_step,
        step_index=0,
        quick_replies=session_result["quick_replies"],
        created_at=session.created_at,
    )


@router.post("/message", response_model=AIResponse)
async def send_message(
    payload: OnboardingMessage,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AIResponse:
    """Process a user message and return AI's next response."""
    session = await _get_session(payload.session_id, current_user.id, db)

    # Build session_data dict from model for the engine
    session_data = {
        "current_step": session.current_step,
        "step_index": session.step_index,
        "messages": session.messages or [],
        "collected_data": session.collected_data or {},
    }

    # Process through AI engine
    response = await onboarding_engine.process_message(session_data, payload.message)

    # Persist updated state back to database
    session.current_step = session_data["current_step"]
    session.step_index = session_data["step_index"]
    session.messages = session_data["messages"]
    session.collected_data = session_data["collected_data"]
    session.updated_at = datetime.utcnow()

    await db.flush()
    return response


@router.post("/import-content", response_model=StyleAnalysis)
async def import_content(
    payload: ContentImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StyleAnalysis:
    """Accept content URLs for style analysis."""
    session = await _get_session(payload.session_id, current_user.id, db)

    # TODO: In production, fetch actual content from URLs via TikHub API
    # For now, use URLs as-is for analysis placeholder
    contents = payload.urls  # Would be fetched content in production

    # Run style analysis
    analysis = await onboarding_engine.analyze_imported_content(contents)

    # Update session
    session.imported_content_urls = (session.imported_content_urls or []) + payload.urls
    session.imported_content_count = len(session.imported_content_urls)
    session.style_analysis = analysis.model_dump()
    session.updated_at = datetime.utcnow()

    await db.flush()
    return analysis


@router.post("/add-competitors")
async def add_competitors(
    payload: CompetitorAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add competitor account URLs for async analysis."""
    session = await _get_session(payload.session_id, current_user.id, db)

    session.competitor_urls = (session.competitor_urls or []) + payload.urls
    session.competitors_added = len(session.competitor_urls)
    session.updated_at = datetime.utcnow()

    await db.flush()

    return {
        "success": True,
        "competitors_added": session.competitors_added,
        "message": f"已添加 {len(payload.urls)} 个竞品账号，将在后台分析",
    }


@router.get("/status", response_model=OnboardingStatus)
async def get_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatus:
    """Get current onboarding progress."""
    session = await _get_session(session_id, current_user.id, db)

    # Calculate completion percentage
    step_weights = {
        "lane_positioning": 20,
        "style_dialogue": 30,
        "content_import": 15,
        "competitor_setup": 10,
        "first_generation": 25,
    }

    completed_percent = 0
    for i, step in enumerate(["lane_positioning", "style_dialogue", "content_import", "competitor_setup", "first_generation"]):
        if i < session.step_index:
            completed_percent += step_weights.get(step, 20)
        elif i == session.step_index:
            # Partial credit for current step
            completed_percent += step_weights.get(step, 20) // 2

    if session.completed_at:
        completed_percent = 100

    return OnboardingStatus(
        session_id=session.id,
        current_step=session.current_step,
        step_index=session.step_index,
        completion_percent=min(completed_percent, 100),
        imported_content_count=session.imported_content_count,
        competitors_added=session.competitors_added,
        is_complete=session.completed_at is not None,
    )


@router.post("/complete")
async def complete_onboarding(
    payload: OnboardingComplete,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Finalize onboarding and trigger vault construction."""
    session = await _get_session(payload.session_id, current_user.id, db)

    if session.completed_at:
        raise HTTPException(status_code=400, detail="Onboarding already completed")

    # Build session data for vault construction
    session_data = {
        "collected_data": session.collected_data or {},
        "style_analysis": session.style_analysis,
        "competitor_urls": session.competitor_urls or [],
    }

    # Build the initial taste vault
    vault = await onboarding_engine.build_initial_vault(session_data)

    # Generate first content as aha moment
    style_analysis = None
    if session.style_analysis:
        style_analysis = StyleAnalysis(**session.style_analysis)

    first_content = await onboarding_engine.generate_first_content(
        collected_data=session.collected_data or {},
        style_analysis=style_analysis,
    )

    # Mark session complete
    session.completed_at = datetime.utcnow()
    session.first_generated_content = first_content
    session.updated_at = datetime.utcnow()

    await db.flush()

    return {
        "success": True,
        "vault": vault,
        "first_content": first_content,
        "message": "品味画像建立完成！这是为你生成的第一篇内容。",
    }


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _get_session(
    session_id: str, user_id: int, db: AsyncSession
) -> OnboardingSession:
    """Fetch and validate an onboarding session belongs to the user."""
    result = await db.execute(
        select(OnboardingSession).where(
            OnboardingSession.id == session_id,
            OnboardingSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Onboarding session not found")
    return session
