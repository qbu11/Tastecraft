"""Pattern extractor — uses Claude to analyze edit batches and extract preference rules."""

import json
import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taste_edit import TasteEdit
from app.models.taste_preference import TastePreference
from app.services.ai_engine import _get_client
from app.services.diff_engine import DiffEngine

logger = logging.getLogger(__name__)

_PATTERN_EXTRACTION_PROMPT = """You are a taste pattern analyzer for a content creation platform.

Analyze these user edits and extract preference rules. Each edit shows what the user changed
from the AI-generated original to their preferred version.

Edits (grouped by type):
{edits_text}

Platform: {platform}

Extract preference rules as a JSON array. Each rule should have:
- "dimension": category (e.g. "title_style", "paragraph_length", "tone", "vocabulary", "structure", "emoji_usage", "opening_style", "closing_style")
- "rule": natural language rule in Chinese (e.g. "小红书标题用疑问句开头", "段落控制在3行以内")
- "evidence": brief explanation of which edits support this

Return ONLY valid JSON array, no other text. Example:
[
  {{"dimension": "title_style", "rule": "标题使用疑问句或感叹句，不超过20字", "evidence": "3次标题修改都缩短并加了问号"}},
  {{"dimension": "tone", "rule": "正文口语化，多用'其实'、'真的'等口头词", "evidence": "多次将书面表达改为口语"}}
]

If no clear patterns emerge, return an empty array: []"""


class PatternExtractor:
    """Extracts taste preference patterns from edit history using LLM analysis."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._diff_engine = DiffEngine(db)

    async def extract_from_edits(
        self,
        user_id: int,
        platform: str | None = None,
        min_edits_per_group: int = 2,
    ) -> list[TastePreference]:
        """Analyze a batch of edits and extract preference rules.

        Groups edits by type, then for each group with min_edits_per_group+ edits,
        asks Claude to identify patterns. Returns structured preferences.
        """
        edits = await self._diff_engine.get_recent_edits(user_id, platform, limit=100)
        if not edits:
            return []

        # Group edits by diff_type
        grouped: dict[str, list[TasteEdit]] = defaultdict(list)
        for edit in edits:
            grouped[edit.diff_type].append(edit)

        # Filter groups that meet minimum threshold
        eligible_groups = {
            k: v for k, v in grouped.items() if len(v) >= min_edits_per_group
        }
        if not eligible_groups:
            # If no group has enough edits, try with a single edit for immediate learning
            if edits:
                eligible_groups = {edits[0].diff_type: [edits[0]]}
            else:
                return []

        # Format edits for LLM
        edits_text = self._format_edits_for_llm(eligible_groups)
        platform_label = platform or "all platforms"

        # Call Claude for pattern extraction
        try:
            client = _get_client()
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": _PATTERN_EXTRACTION_PROMPT.format(
                            edits_text=edits_text,
                            platform=platform_label,
                        ),
                    }
                ],
            )
            raw_text = response.content[0].text.strip()
            patterns = json.loads(raw_text)
        except (json.JSONDecodeError, IndexError, Exception) as e:
            logger.warning("Pattern extraction failed: %s", e)
            return []

        # Convert to TastePreference models
        new_preferences: list[TastePreference] = []
        all_edit_ids = [e.id for e in edits]

        for pattern in patterns:
            if not isinstance(pattern, dict):
                continue
            dimension = pattern.get("dimension", "")
            rule = pattern.get("rule", "")
            if not dimension or not rule:
                continue

            # Compute confidence from number of supporting edits
            supporting_type = self._match_dimension_to_type(dimension)
            supporting_count = len(eligible_groups.get(supporting_type, []))
            confidence = self._diff_engine.compute_confidence(
                max(supporting_count, min_edits_per_group)
            )

            pref = TastePreference(
                user_id=user_id,
                project_id=None,
                platform=platform,
                dimension=dimension,
                rule=rule,
                confidence=confidence,
                source_edit_ids=all_edit_ids[:10],  # cap at 10 IDs
            )
            new_preferences.append(pref)

        return new_preferences

    async def merge_preferences(
        self,
        user_id: int,
        new_preferences: list[TastePreference],
    ) -> list[TastePreference]:
        """Merge new preferences with existing ones, handling conflicts.

        If a preference with the same dimension+platform exists:
        - If rules are similar, boost confidence
        - If rules conflict, keep higher-confidence one
        """
        if not new_preferences:
            return []

        merged: list[TastePreference] = []

        for new_pref in new_preferences:
            # Check for existing preference with same dimension + platform
            existing_result = await self._db.execute(
                select(TastePreference).where(
                    TastePreference.user_id == user_id,
                    TastePreference.dimension == new_pref.dimension,
                    TastePreference.platform == new_pref.platform,
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                # Update existing: boost confidence, update rule if new is higher confidence
                if new_pref.confidence >= existing.confidence:
                    existing.rule = new_pref.rule
                    existing.confidence = min(0.95, existing.confidence + 0.1)
                    # Merge source edit IDs
                    existing_ids = existing.source_edit_ids or []
                    new_ids = new_pref.source_edit_ids or []
                    existing.source_edit_ids = list(
                        set(existing_ids + new_ids)
                    )[:20]  # cap
                else:
                    existing.confidence = min(0.95, existing.confidence + 0.05)
                merged.append(existing)
            else:
                # Add new preference
                self._db.add(new_pref)
                merged.append(new_pref)

        await self._db.flush()
        return merged

    async def run_extraction_pipeline(
        self,
        user_id: int,
        platform: str | None = None,
    ) -> list[TastePreference]:
        """Full pipeline: extract patterns then merge with existing preferences."""
        new_prefs = await self.extract_from_edits(user_id, platform)
        if not new_prefs:
            return []
        return await self.merge_preferences(user_id, new_prefs)

    def _format_edits_for_llm(
        self, grouped_edits: dict[str, list[TasteEdit]]
    ) -> str:
        """Format grouped edits into human-readable text for the LLM."""
        sections: list[str] = []
        for edit_type, edits in grouped_edits.items():
            section = f"## Type: {edit_type} ({len(edits)} edits)\n"
            for i, edit in enumerate(edits[:5], 1):  # cap at 5 per group
                orig_preview = edit.original_text[:200].replace("\n", " ")
                mod_preview = edit.modified_text[:200].replace("\n", " ")
                section += (
                    f"\nEdit {i}:\n"
                    f"  Original: {orig_preview}\n"
                    f"  Modified: {mod_preview}\n"
                )
            sections.append(section)
        return "\n".join(sections)

    @staticmethod
    def _match_dimension_to_type(dimension: str) -> str:
        """Map a preference dimension back to the most likely edit type."""
        mapping = {
            "title_style": "title_change",
            "opening_style": "title_change",
            "tone": "tone_shift",
            "vocabulary": "vocabulary",
            "paragraph_length": "shortening",
            "structure": "restructure",
            "emoji_usage": "style_tweak",
            "closing_style": "style_tweak",
        }
        return mapping.get(dimension, "style_tweak")
