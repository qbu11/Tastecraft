"""Core diff learning engine — captures edits and extracts taste signals.

v2: Adds confidence decay, conflict detection, and conflict resolution.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from difflib import SequenceMatcher

import anthropic
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.taste_edit import TasteEdit
from app.models.taste_preference import TastePreference
from app.schemas.diff import EditClassification, EditType, PreferenceConflict

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

    # ── v2: Confidence Decay ──────────────────────────────────────────────

    async def apply_confidence_decay(self, user_id: str) -> int:
        """Apply time-based confidence decay to all preferences.

        Preferences unused for 30+ days decay by 10% per week.
        User-confirmed preferences are exempt from decay.
        Returns number of preferences affected.
        """
        cutoff = datetime.utcnow() - timedelta(days=30)

        # Fetch non-confirmed preferences that haven't been updated in 30+ days
        result = await self._db.execute(
            select(TastePreference).where(
                TastePreference.user_id == int(user_id),
                TastePreference.confirmed.is_(False),
                TastePreference.updated_at < cutoff,
                TastePreference.confidence > 0.05,  # Don't decay near-zero
            )
        )
        stale_prefs = list(result.scalars().all())

        affected = 0
        now = datetime.utcnow()
        for pref in stale_prefs:
            # Calculate weeks since last update
            days_stale = (now - pref.updated_at).days
            weeks_stale = max(0, (days_stale - 30) // 7)
            if weeks_stale <= 0:
                continue

            # Decay 10% per week, compounding
            decay_factor = 0.9 ** weeks_stale
            new_confidence = max(0.05, pref.confidence * decay_factor)

            if abs(new_confidence - pref.confidence) > 0.001:
                pref.confidence = round(new_confidence, 4)
                pref.updated_at = now
                affected += 1

        if affected:
            await self._db.flush()

        logger.info(
            "Applied confidence decay for user %s: %d preferences affected",
            user_id,
            affected,
        )
        return affected

    # ── v2: Conflict Detection ─────────────────────────────────────────────

    async def detect_conflicts(self, user_id: str) -> list[PreferenceConflict]:
        """Find contradictory preferences.

        e.g., edit #5 shortened paragraphs but edit #12 expanded them.
        Uses Claude to determine if two preferences truly conflict.
        """
        result = await self._db.execute(
            select(TastePreference)
            .where(
                TastePreference.user_id == int(user_id),
                TastePreference.confidence > 0.2,  # Only consider meaningful prefs
            )
            .order_by(TastePreference.dimension, TastePreference.created_at)
        )
        preferences = list(result.scalars().all())

        if len(preferences) < 2:
            return []

        # Group by dimension — conflicts are most likely within same dimension
        by_dimension: dict[str, list[TastePreference]] = {}
        for p in preferences:
            by_dimension.setdefault(p.dimension, []).append(p)

        # Collect candidate pairs (same dimension, different rules)
        candidate_pairs: list[tuple[TastePreference, TastePreference]] = []
        for dim_prefs in by_dimension.values():
            if len(dim_prefs) < 2:
                continue
            for i, a in enumerate(dim_prefs):
                for b in dim_prefs[i + 1 :]:
                    if a.rule != b.rule:
                        candidate_pairs.append((a, b))

        if not candidate_pairs:
            return []

        # Use Claude to assess which pairs are true conflicts
        conflicts: list[PreferenceConflict] = []
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        # Batch pairs for efficient AI evaluation (max 10 pairs at a time)
        for pair_batch in _chunks(candidate_pairs, 10):
            pairs_text = "\n".join(
                f"Pair {i+1}: Dimension={a.dimension}, "
                f"Rule A (edit #{','.join(str(x) for x in (a.source_edit_ids or []))})=\"{a.rule}\" "
                f"vs Rule B (edit #{','.join(str(x) for x in (b.source_edit_ids or []))})=\"{b.rule}\", "
                f"Platform A={a.platform or 'any'}, Platform B={b.platform or 'any'}"
                for i, (a, b) in enumerate(pair_batch)
            )

            system = """你是品味偏好分析专家。判断以下偏好对是否存在矛盾。

对于每一对，判断：
1. 是否真正矛盾（CONFLICT）还是可以共存（COMPATIBLE）
2. 如果矛盾，是否可能因为平台不同而合理（CONTEXT_SPLIT）
3. 建议的解决方式

输出 JSON 数组：
[
  {
    "pair_index": 1,
    "verdict": "CONFLICT" | "COMPATIBLE" | "CONTEXT_SPLIT",
    "explanation": "简短解释",
    "suggested_resolution": "keep_first" | "keep_second" | "context_split" | "merge"
  }
]"""

            try:
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system=system,
                    messages=[{"role": "user", "content": f"分析以下偏好对：\n{pairs_text}"}],
                )
                # Parse response
                import re

                text = response.content[0].text
                json_match = re.search(r"\[[\s\S]*\]", text)
                if json_match:
                    verdicts = json.loads(json_match.group())
                    for v in verdicts:
                        idx = v.get("pair_index", 0) - 1
                        if 0 <= idx < len(pair_batch) and v.get("verdict") in (
                            "CONFLICT",
                            "CONTEXT_SPLIT",
                        ):
                            a, b = pair_batch[idx]
                            conflicts.append(
                                PreferenceConflict(
                                    id=str(uuid.uuid4()),
                                    preference_a_id=a.id,
                                    preference_b_id=b.id,
                                    preference_a_rule=a.rule,
                                    preference_b_rule=b.rule,
                                    preference_a_platform=a.platform,
                                    preference_b_platform=b.platform,
                                    dimension=a.dimension,
                                    context=v.get("explanation", ""),
                                    suggested_resolution=v.get(
                                        "suggested_resolution", "keep_second"
                                    ),
                                )
                            )
            except Exception as e:
                logger.error("Conflict detection AI call failed: %s", e)
                continue

        return conflicts

    # ── v2: Conflict Resolution ────────────────────────────────────────────

    async def resolve_conflict(
        self, conflict_id: str, preference_a_id: int, preference_b_id: int,
        resolution: str, context_note: str | None = None,
    ) -> TastePreference | None:
        """Resolve a conflict based on user choice.

        resolution: 'keep_first' | 'keep_second' | 'context_split'
        - keep_first: boost A, delete B
        - keep_second: boost B, delete A
        - context_split: keep both, annotate with platform context
        """
        a_result = await self._db.execute(
            select(TastePreference).where(TastePreference.id == preference_a_id)
        )
        pref_a = a_result.scalar_one_or_none()

        b_result = await self._db.execute(
            select(TastePreference).where(TastePreference.id == preference_b_id)
        )
        pref_b = b_result.scalar_one_or_none()

        if not pref_a or not pref_b:
            return None

        now = datetime.utcnow()
        surviving: TastePreference | None = None

        if resolution == "keep_first":
            pref_a.confidence = min(0.95, pref_a.confidence + 0.15)
            pref_a.confirmed = True
            pref_a.updated_at = now
            await self._db.delete(pref_b)
            surviving = pref_a

        elif resolution == "keep_second":
            pref_b.confidence = min(0.95, pref_b.confidence + 0.15)
            pref_b.confirmed = True
            pref_b.updated_at = now
            await self._db.delete(pref_a)
            surviving = pref_b

        elif resolution == "context_split":
            # Both survive — mark them with context annotations
            if context_note:
                pref_a.rule = f"{pref_a.rule} [{context_note}]"
                pref_b.rule = f"{pref_b.rule} [{context_note}]"
            pref_a.confirmed = True
            pref_b.confirmed = True
            pref_a.updated_at = now
            pref_b.updated_at = now
            surviving = pref_a  # Return first one as representative

        await self._db.flush()
        logger.info(
            "Resolved conflict %s: %s (a=%d, b=%d)",
            conflict_id,
            resolution,
            preference_a_id,
            preference_b_id,
        )
        return surviving

    # ── Confidence Scoring ─────────────────────────────────────────────────

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


# ── Module-level Utilities ─────────────────────────────────────────────────


def _chunks(lst: list, n: int):
    """Yield successive n-sized chunks from a list."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
