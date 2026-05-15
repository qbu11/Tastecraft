"""
Session Manager — Camoufox browser profile management

Manages browser profiles and session health for all platform connections.
Each user+platform pair gets an isolated profile directory containing
cookies, localStorage, and Camoufox/Firefox profile data.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default location for browser profiles
DEFAULT_PROFILES_DIR = Path("data/browser_profiles")


class SessionHealth(str, Enum):
    """Session health states."""
    ACTIVE = "active"          # Session is valid
    EXPIRING = "expiring"      # Session exists but may expire soon (< 24h)
    EXPIRED = "expired"        # Session has expired
    NOT_FOUND = "not_found"    # No session exists
    ERROR = "error"            # Could not determine status


class SessionStatus:
    """Status of a single platform session."""

    def __init__(
        self,
        user_id: str,
        platform: str,
        health: SessionHealth,
        last_verified: datetime | None = None,
        expires_at: datetime | None = None,
        profile_dir: str | None = None,
        error: str | None = None,
    ) -> None:
        self.user_id = user_id
        self.platform = platform
        self.health = health
        self.last_verified = last_verified
        self.expires_at = expires_at
        self.profile_dir = profile_dir
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "platform": self.platform,
            "health": self.health.value,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "profile_dir": self.profile_dir,
            "error": self.error,
        }


class SessionManager:
    """
    Manages Camoufox browser profiles and sessions for all users.

    Directory structure:
        data/browser_profiles/
        ├── <user_id>/
        │   ├── xiaohongshu/
        │   │   ├── cookies.json
        │   │   ├── local_storage.json
        │   │   └── <firefox profile files>
        │   └── wechat/
        │       └── ...
        └── _metadata/
            └── sessions.json   # session health metadata
    """

    SUPPORTED_PLATFORMS = ["xiaohongshu", "wechat", "weibo"]

    def __init__(self, profiles_dir: Path | None = None) -> None:
        self.profiles_dir = profiles_dir or DEFAULT_PROFILES_DIR
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_dir = self.profiles_dir / "_metadata"
        self._metadata_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_path = self._metadata_dir / "sessions.json"

    # ── Profile management ───────────────────────────────────────

    async def get_or_create_profile(self, user_id: str, platform: str) -> str:
        """
        Get profile directory path for a user+platform pair.
        Creates the directory if it doesn't exist.

        Returns:
            Absolute path to the profile directory.
        """
        profile_path = self.profiles_dir / str(user_id) / platform
        profile_path.mkdir(parents=True, exist_ok=True)
        logger.info("Profile dir: %s", profile_path)
        return str(profile_path.resolve())

    # ── Session health ───────────────────────────────────────────

    async def check_session_health(
        self, user_id: str, platform: str
    ) -> SessionStatus:
        """
        Check if a session is alive, expiring soon, or expired.

        Strategy:
        1. Check if profile dir exists and has cookies
        2. Check cookie expiry timestamps
        3. Check metadata for last verified time
        """
        profile_path = self.profiles_dir / str(user_id) / platform
        cookies_path = profile_path / "cookies.json"

        # No profile at all
        if not profile_path.exists():
            return SessionStatus(
                user_id=user_id,
                platform=platform,
                health=SessionHealth.NOT_FOUND,
                profile_dir=str(profile_path),
            )

        # No cookies file
        if not cookies_path.exists():
            return SessionStatus(
                user_id=user_id,
                platform=platform,
                health=SessionHealth.NOT_FOUND,
                profile_dir=str(profile_path),
            )

        # Parse cookies and check expiry
        try:
            raw = cookies_path.read_text(encoding="utf-8")
            cookies = json.loads(raw)

            if not cookies:
                return SessionStatus(
                    user_id=user_id,
                    platform=platform,
                    health=SessionHealth.EXPIRED,
                    profile_dir=str(profile_path),
                )

            now = time.time()
            # Check the minimum expiry among session-critical cookies
            min_expiry = float("inf")
            session_cookies_found = False

            for cookie in cookies:
                expires = cookie.get("expires", -1)
                if expires == -1:
                    # Session cookie (no expiry) — treat as "might work"
                    session_cookies_found = True
                    continue
                if expires < now:
                    continue  # Already expired, skip
                min_expiry = min(min_expiry, expires)
                session_cookies_found = True

            if not session_cookies_found:
                return SessionStatus(
                    user_id=user_id,
                    platform=platform,
                    health=SessionHealth.EXPIRED,
                    profile_dir=str(profile_path),
                )

            expires_at = None
            if min_expiry < float("inf"):
                expires_at = datetime.fromtimestamp(min_expiry, tz=timezone.utc)
                remaining_hours = (min_expiry - now) / 3600

                if remaining_hours < 0:
                    health = SessionHealth.EXPIRED
                elif remaining_hours < 24:
                    health = SessionHealth.EXPIRING
                else:
                    health = SessionHealth.ACTIVE
            else:
                # Only session cookies (no expiry timestamps)
                health = SessionHealth.ACTIVE

            # Check metadata for last_verified
            metadata = self._load_metadata()
            meta_key = f"{user_id}:{platform}"
            last_verified = None
            if meta_key in metadata:
                ts = metadata[meta_key].get("last_verified")
                if ts:
                    last_verified = datetime.fromisoformat(ts)

            return SessionStatus(
                user_id=user_id,
                platform=platform,
                health=health,
                last_verified=last_verified,
                expires_at=expires_at,
                profile_dir=str(profile_path),
            )

        except (json.JSONDecodeError, OSError) as exc:
            return SessionStatus(
                user_id=user_id,
                platform=platform,
                health=SessionHealth.ERROR,
                profile_dir=str(profile_path),
                error=str(exc),
            )

    async def update_session_verified(self, user_id: str, platform: str) -> None:
        """Mark a session as recently verified (login confirmed working)."""
        metadata = self._load_metadata()
        meta_key = f"{user_id}:{platform}"
        metadata[meta_key] = {
            "last_verified": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "platform": platform,
        }
        self._save_metadata(metadata)

    async def invalidate_session(self, user_id: str, platform: str) -> None:
        """
        Mark session as invalid (needs re-login).

        Removes cookies but keeps the profile directory for re-use.
        """
        profile_path = self.profiles_dir / str(user_id) / platform
        cookies_path = profile_path / "cookies.json"

        if cookies_path.exists():
            cookies_path.unlink()
            logger.info("Session invalidated for %s/%s", user_id, platform)

        # Update metadata
        metadata = self._load_metadata()
        meta_key = f"{user_id}:{platform}"
        if meta_key in metadata:
            metadata[meta_key]["invalidated_at"] = datetime.now(timezone.utc).isoformat()
            metadata[meta_key]["last_verified"] = None
            self._save_metadata(metadata)

    async def get_all_sessions(self, user_id: str) -> list[SessionStatus]:
        """List all platform sessions for a user."""
        sessions: list[SessionStatus] = []
        for platform in self.SUPPORTED_PLATFORMS:
            status = await self.check_session_health(user_id, platform)
            sessions.append(status)
        return sessions

    # ── Internal helpers ─────────────────────────────────────────

    def _load_metadata(self) -> dict[str, Any]:
        """Load session metadata from disk."""
        if not self._metadata_path.exists():
            return {}
        try:
            raw = self._metadata_path.read_text(encoding="utf-8")
            return json.loads(raw)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_metadata(self, metadata: dict[str, Any]) -> None:
        """Persist session metadata to disk."""
        try:
            self._metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Failed to save session metadata: %s", exc)
