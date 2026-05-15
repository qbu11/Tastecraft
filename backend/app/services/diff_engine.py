"""Core diff learning engine — captures edits and extracts taste signals."""

import logging
from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taste_edit import TasteEdit
from app.models.taste_preference import TastePreference
from app.schemas.diff import EditClassification, EditType

logger = logging.getLogger(__name__)

# Thresholds for classification heuristics
_SHORTENING_RATIO = 0.75  # modified < 75% of original length → shortening
_EXPANSION_RATIO = 1.25  # modified > 125% of original length → expansion
_SIMILARITY_HIGH = 0.85  # above this → style_tweak
_SIMILARITY_LOW = 0.40  # below this → restructure


class DiffEngine:
    """Captures edits, classifies them, and drives preference extraction."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def capture_edit(
        self,
        content_id: int,
        user_id: int,
        original: str,
        modified: str,
        platform: str,
        content_line_id: int | None = None,
    ) -> TasteEdit:
        """Capture a single edit, classify it, and persist."""
        classification = self.classify_edit(original, modified)

        edit = TasteEdit(
            content_id=content_id,
            user_id=user_id,
            original_text=original,
            modified_text=modified,
            diff_type=classification.edit_type.value,
            platform=platform,
        )
        self._db.add(edit)
        await self._db.flush()
        await self._db.refresh(edit)

        logger.info(
            "Captured edit #%d for user %d: %s (similarity=%.2f)",
            edit.id,
            user_id,
            classification.edit_type.value,
            classification.similarity_ratio,
        )

        return edit

    async def get_user_edit_count(self, user_id: int, platform: str | None = None) -> int:
        """Get total edit count for a user, optionally filtered by platform."""
        query = select(func.count()).select_from(TasteEdit).where(
            TasteEdit.user_id == user_id
        )
        if platform:
            query = query.where(TasteEdit.platform == platform)
        result = await self._db.execute(query)
        return result.scalar_one()

    async def get_recent_edits(
        self,
        user_id: int,
        platform: str | None = None,
        limit: int = 50,
    ) -> list[TasteEdit]:
        """Fetch recent edits for pattern extraction."""
        query = (
            select(TasteEdit)
            .where(TasteEdit.user_id == user_id)
            .order_by(TasteEdit.created_at.desc())
            .limit(limit)
        )
        if platform:
            query = query.where(TasteEdit.platform == platform)
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_preference_summary(self, user_id: int) -> dict:
        """Get human-readable preference summary for the user."""
        pref_result = await self._db.execute(
            select(TastePreference)
            .where(TastePreference.user_id == user_id)
            .order_by(TastePreference.confidence.desc())
        )
        preferences = list(pref_result.scalars().all())

        edit_count = await self.get_user_edit_count(user_id)

        # Compute taste score as average confidence * coverage factor
        if preferences:
            avg_confidence = sum(p.confidence for p in preferences) / len(preferences)
            coverage = min(len(preferences) / 10.0, 1.0)  # max out at 10 prefs
            taste_score = round(avg_confidence * coverage * 100, 1)
        else:
            taste_score = 0.0

        # Gather unique platforms
        platforms_result = await self._db.execute(
            select(TasteEdit.platform)
            .where(TasteEdit.user_id == user_id)
            .where(TasteEdit.platform.isnot(None))
            .distinct()
        )
        platforms = [row[0] for row in platforms_result.all()]

        dimensions = {p.dimension for p in preferences}

        return {
            "preferences": preferences,
            "total_edits": edit_count,
            "taste_score": taste_score,
            "platforms": platforms,
            "dimensions_covered": len(dimensions),
        }

    def compute_confidence(self, edit_count: int) -> float:
        """Compute confidence score (0-1) for a pattern based on supporting edit count.

        - 1 edit → 0.3 (immediate but low confidence)
        - 2 edits → 0.5
        - 3 edits → 0.7 (high confidence threshold)
        - 5+ edits → 0.9
        - 10+ edits → 0.95
        """
        if edit_count <= 0:
            return 0.0
        if edit_count == 1:
            return 0.3
        if edit_count == 2:
            return 0.5
        if edit_count == 3:
            return 0.7
        if edit_count <= 5:
            return 0.8
        if edit_count <= 10:
            return 0.9
        return 0.95

    def classify_edit(self, original: str, modified: str) -> EditClassification:
        """Classify what type of edit was made using heuristics."""
        if not original and not modified:
            return EditClassification(
                edit_type=EditType.STYLE_TWEAK,
                details="empty content",
                similarity_ratio=1.0,
            )

        # Handle deletion case
        if not modified.strip():
            return EditClassification(
                edit_type=EditType.DELETION,
                details="entire content deleted",
                word_count_delta=-len(original.split()),
                similarity_ratio=0.0,
            )

        matcher = SequenceMatcher(None, original, modified)
        similarity = matcher.ratio()
        orig_len = len(original)
        mod_len = len(modified)
        word_delta = len(modified.split()) - len(original.split())

        # Check title change (first line differs, rest similar)
        orig_lines = original.strip().split("\n")
        mod_lines = modified.strip().split("\n")
        if len(orig_lines) > 1 and len(mod_lines) > 1:
            title_sim = SequenceMatcher(None, orig_lines[0], mod_lines[0]).ratio()
            body_sim = SequenceMatcher(
                None, "\n".join(orig_lines[1:]), "\n".join(mod_lines[1:])
            ).ratio()
            if title_sim < 0.6 and body_sim > 0.85:
                return EditClassification(
                    edit_type=EditType.TITLE_CHANGE,
                    details=f"title changed from '{orig_lines[0][:50]}' to '{mod_lines[0][:50]}'",
                    word_count_delta=word_delta,
                    similarity_ratio=similarity,
                )

        # Shortening
        if orig_len > 0 and mod_len / orig_len < _SHORTENING_RATIO:
            return EditClassification(
                edit_type=EditType.SHORTENING,
                details=f"reduced from {orig_len} to {mod_len} chars ({mod_len*100//orig_len}%)",
                word_count_delta=word_delta,
                similarity_ratio=similarity,
            )

        # Expansion
        if orig_len > 0 and mod_len / orig_len > _EXPANSION_RATIO:
            return EditClassification(
                edit_type=EditType.EXPANSION,
                details=f"expanded from {orig_len} to {mod_len} chars ({mod_len*100//orig_len}%)",
                word_count_delta=word_delta,
                similarity_ratio=similarity,
            )

        # Restructure (low similarity but similar length)
        if similarity < _SIMILARITY_LOW:
            return EditClassification(
                edit_type=EditType.RESTRUCTURE,
                details="significant reorganization",
                word_count_delta=word_delta,
                similarity_ratio=similarity,
            )

        # Vocabulary replacement detection
        vocab_changes = self._detect_vocabulary_changes(original, modified, matcher)
        if vocab_changes:
            return EditClassification(
                edit_type=EditType.VOCABULARY,
                details=f"word replacements: {', '.join(vocab_changes[:5])}",
                word_count_delta=word_delta,
                similarity_ratio=similarity,
            )

        # Tone shift (similar structure, different words — moderate similarity)
        if _SIMILARITY_LOW <= similarity < _SIMILARITY_HIGH:
            return EditClassification(
                edit_type=EditType.TONE_SHIFT,
                details="tone or style adjusted while preserving structure",
                word_count_delta=word_delta,
                similarity_ratio=similarity,
            )

        # Default: style tweak (high similarity, minor changes)
        return EditClassification(
            edit_type=EditType.STYLE_TWEAK,
            details="minor wording adjustments",
            word_count_delta=word_delta,
            similarity_ratio=similarity,
        )

    def _detect_vocabulary_changes(
        self,
        original: str,
        modified: str,
        matcher: SequenceMatcher,
    ) -> list[str]:
        """Detect specific word-level replacements."""
        replacements: list[str] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                orig_segment = original[i1:i2].strip()
                mod_segment = modified[j1:j2].strip()
                # Only count as vocabulary if segments are single words or short phrases
                if (
                    len(orig_segment.split()) <= 3
                    and len(mod_segment.split()) <= 3
                    and orig_segment
                    and mod_segment
                ):
                    replacements.append(f"'{orig_segment}'→'{mod_segment}'")
        return replacements
