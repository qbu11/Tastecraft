"""Session management API routes — browser profile health for all platforms.

Endpoints
---------
GET    /api/v1/sessions/                    — List all sessions for the current user
GET    /api/v1/sessions/{platform}/status   — Check session health for a platform
POST   /api/v1/sessions/{platform}/refresh  — Attempt session refresh (re-verify)
DELETE /api/v1/sessions/{platform}          — Invalidate a session (force re-login)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.publish import SessionListResponse, SessionStatusResponse
from app.tools.platform.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])

_session_manager = SessionManager()


# ── List all sessions ────────────────────────────────────────────────────────


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
) -> SessionListResponse:
    """List all platform sessions for the current user."""
    statuses = await _session_manager.get_all_sessions(str(current_user.id))
    return SessionListResponse(
        sessions=[
            SessionStatusResponse(
                user_id=s.user_id,
                platform=s.platform,
                health=s.health.value,
                last_verified=s.last_verified,
                expires_at=s.expires_at,
                error=s.error,
            )
            for s in statuses
        ]
    )


# ── Single platform status ───────────────────────────────────────────────────


@router.get("/{platform}/status", response_model=SessionStatusResponse)
async def session_status(
    platform: str,
    current_user: User = Depends(get_current_user),
) -> SessionStatusResponse:
    """Check session health for a specific platform."""
    if platform not in SessionManager.SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform: {platform}. "
            f"Supported: {', '.join(SessionManager.SUPPORTED_PLATFORMS)}",
        )

    status = await _session_manager.check_session_health(str(current_user.id), platform)
    return SessionStatusResponse(
        user_id=status.user_id,
        platform=status.platform,
        health=status.health.value,
        last_verified=status.last_verified,
        expires_at=status.expires_at,
        error=status.error,
    )


# ── Refresh session ──────────────────────────────────────────────────────────


@router.post("/{platform}/refresh", response_model=SessionStatusResponse)
async def refresh_session(
    platform: str,
    current_user: User = Depends(get_current_user),
) -> SessionStatusResponse:
    """Attempt to refresh/re-verify a session.

    For browser-based platforms this launches the browser, loads saved cookies,
    and navigates to the platform to check if the session is still alive.
    """
    if platform not in SessionManager.SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform: {platform}",
        )

    user_id_str = str(current_user.id)

    # Platform-specific verification
    if platform == "xiaohongshu":
        from app.tools.platform.xiaohongshu import XHSPublisher

        profile_dir = await _session_manager.get_or_create_profile(user_id_str, platform)
        publisher = XHSPublisher(profile_dir=profile_dir)
        try:
            loaded = await publisher.load_session()
            if not loaded:
                status = await _session_manager.check_session_health(user_id_str, platform)
                return SessionStatusResponse(
                    user_id=status.user_id,
                    platform=status.platform,
                    health="expired",
                    error="No saved session to restore",
                )

            is_valid = await publisher.check_login_status()
            if is_valid:
                await _session_manager.update_session_verified(user_id_str, platform)
        except Exception as exc:
            logger.warning("Session refresh failed for %s/%s: %s", user_id_str, platform, exc)
            return SessionStatusResponse(
                user_id=user_id_str,
                platform=platform,
                health="error",
                error=str(exc),
            )
        finally:
            await publisher.close()
    else:
        # For other platforms, just re-check the cookie health
        pass

    status = await _session_manager.check_session_health(user_id_str, platform)
    return SessionStatusResponse(
        user_id=status.user_id,
        platform=status.platform,
        health=status.health.value,
        last_verified=status.last_verified,
        expires_at=status.expires_at,
        error=status.error,
    )


# ── Invalidate session ──────────────────────────────────────────────────────


@router.delete("/{platform}", status_code=204)
async def invalidate_session(
    platform: str,
    current_user: User = Depends(get_current_user),
) -> None:
    """Invalidate a session (removes cookies, forces re-login)."""
    if platform not in SessionManager.SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform: {platform}",
        )

    await _session_manager.invalidate_session(str(current_user.id), platform)
    logger.info("Session invalidated: user=%s platform=%s", current_user.id, platform)
