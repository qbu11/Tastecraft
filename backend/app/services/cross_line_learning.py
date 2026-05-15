"""CrossLineLearning — share applicable preferences across content lines.

When a user operates multiple content lines (projects), some preferences
are global (e.g., tone, formatting style) while others are line-specific
(e.g., topic focus, audience persona). This service identifies global
preferences and propagates them to other lines.
"""

from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taste_preference import TastePreference

logger = logging.getLogger(__name__)

# Dimensions that are typically global across all content lines
_GLOBAL_DIMENSIONS = frozenset({
    "tone",
    "formality",
    "formatting",
    "punctuation",
    "emoji_usage",
    "sentence_length",
    "paragraph_structure",
    "language_style",
})

# Dimensions that are typically line-specific
_LOCAL_DIMENSIONS = frozenset({
    "topic_focus",
    "audience_persona",
    "hashtag_style",
    "platform_adaptation",
    "content_type",
    "niche_terminology",
})


class CrossLineLearning:
    """Share applicable preferences across content lines."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def identify_global_preferences(
        self, user_id: int
    ) -> list[TastePreference]:
        """Find preferences that apply across ALL content lines.

        A preference is considered global if:
          1. Its dimension is in the global dimension set, OR
          2. It appears with similar rules across 2+ projects.

        Returns preferences that should be propagated.
        """
        result = await self.db.execute(
            select(TastePreference)
            .where(
                TastePreference.user_id == user_id,
                TastePreference.confidence >= 0.6,
            )
            .order_by(TastePreference.confidence.desc())
        )
        all_prefs = list(result.scalars().all())

        global_prefs: list[TastePreference] = []
        for pref in all_prefs:
            classification = await self.detect_global_vs_local(pref)
            if classification == "global":
                global_prefs.append(pref)

        return global_prefs

    async def propagate_to_line(
        self, preference_id: int, target_project_id: int, user_id: int
    ) -> TastePreference | None:
        """Copy a global preference to another content line's vault.

        Checks for duplicates before copying. If a similar preference already
        exists in the target project, it updates confidence instead of creating
        a new one.

        Returns the new or updated preference, or None if already exists.
        """
        # Fetch source preference
        result = await self.db.execute(
            select(TastePreference).where(TastePreference.id == preference_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            logger.warning("Source preference %d not found", preference_id)
            return None

        # Check if similar preference already exists in target project
        result = await self.db.execute(
            select(TastePreference).where(
                TastePreference.user_id == user_id,
                TastePreference.project_id == target_project_id,
                TastePreference.dimension == source.dimension,
                TastePreference.rule == source.rule,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Boost confidence of existing preference
            existing.confidence = min(1.0, existing.confidence + 0.1)
            await self.db.flush()
            logger.info(
                "Boosted existing preference %d in project %d (confidence=%.2f)",
                existing.id,
                target_project_id,
                existing.confidence,
            )
            return existing

        # Create new preference in target project
        new_pref = TastePreference(
            user_id=user_id,
            project_id=target_project_id,
            platform=source.platform,
            dimension=source.dimension,
            rule=source.rule,
            confidence=source.confidence * 0.8,  # Slightly lower confidence for propagated
            source_edit_ids=source.source_edit_ids,
            confirmed=False,
        )
        self.db.add(new_pref)
        await self.db.flush()
        await self.db.refresh(new_pref)

        logger.info(
            "Propagated preference '%s' to project %d (new id=%d)",
            source.dimension,
            target_project_id,
            new_pref.id,
        )
        return new_pref

    async def detect_global_vs_local(
        self, preference: TastePreference
    ) -> Literal["global", "local", "uncertain"]:
        """Classify if a preference is global or line-specific.

        Classification logic:
          1. Known global dimensions -> "global"
          2. Known local dimensions -> "local"
          3. High confidence + confirmed -> lean "global"
          4. Otherwise -> "uncertain"
        """
        dimension = preference.dimension.lower().strip()

        # Check against known dimension sets
        if dimension in _GLOBAL_DIMENSIONS:
            return "global"
        if dimension in _LOCAL_DIMENSIONS:
            return "local"

        # Check if this preference (same dimension + similar rule) exists across
        # multiple projects for this user
        result = await self.db.execute(
            select(TastePreference.project_id)
            .where(
                TastePreference.user_id == preference.user_id,
                TastePreference.dimension == preference.dimension,
            )
            .distinct()
        )
        project_ids = [row[0] for row in result.all() if row[0] is not None]

        if len(project_ids) >= 2:
            return "global"

        if preference.confirmed and preference.confidence >= 0.8:
            return "global"

        return "uncertain"
