"""VaultInitializer — creates initial vault structure from onboarding data.

Generates the full directory tree of interconnected markdown documents
with YAML frontmatter that form the user's Taste Vault.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.services.taste_vault import VAULT_BASE, TasteVault

logger = logging.getLogger(__name__)


class VaultInitializer:
    """Creates the initial vault from onboarding data.

    Vault structure:
        vault/{user_id}/{project_slug}/
        +-- _index.md
        +-- style/
        |   +-- tone.md
        |   +-- structure.md
        |   +-- vocabulary.md
        |   +-- visual.md
        |   +-- platform-adaptations.md
        +-- preferences/
        |   +-- edits-log.md
        |   +-- patterns.md
        |   +-- explicit-rules.md
        |   +-- conflicts.md
        +-- competitors/
        |   +-- lane-trends.md
        +-- context/
        |   +-- brand.md
        |   +-- audience.md
        |   +-- topics-history.md
        +-- evolution/
            +-- changelog.md
            +-- weekly-digest.md
    """

    async def create_from_onboarding(
        self,
        user_id: str,
        project_slug: str,
        onboarding_data: dict,
    ) -> TasteVault:
        """Create vault structure from onboarding results.

        Args:
            user_id: User identifier.
            project_slug: Project slug for isolation.
            onboarding_data: Dict from onboarding flow containing:
                - tone: str (e.g., "温和但坚定的观点型")
                - structure: str (e.g., "先给结论，再解释")
                - vocabulary_level: str (e.g., "专业但不晦涩")
                - visual_style: str (e.g., "清新简约")
                - platforms: list[str] (target platforms)
                - brand_name: str
                - brand_description: str
                - target_audience: str
                - content_topics: list[str]
                - explicit_rules: list[str]
                - competitors: list[dict]
                - style_analysis: dict (from content import)

        Returns:
            Initialized TasteVault instance.
        """
        vault = TasteVault(user_id=user_id, project_slug=project_slug)
        root = vault.root

        # Ensure directory structure
        dirs = [
            root / "style",
            root / "preferences",
            root / "competitors",
            root / "context",
            root / "evolution",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()
        source_tag = "onboarding"

        # Generate all documents
        await self._write_index(root, onboarding_data, now)
        await self._write_style_docs(root, onboarding_data, now, source_tag)
        await self._write_preference_docs(root, onboarding_data, now, source_tag)
        await self._write_competitor_docs(root, onboarding_data, now, source_tag)
        await self._write_context_docs(root, onboarding_data, now, source_tag)
        await self._write_evolution_docs(root, now, source_tag)

        logger.info("Vault initialized for user=%s project=%s", user_id, project_slug)
        return vault

    # ── Document Writers ──────────────────────────────────────────────────────

    async def _write_index(self, root: Path, data: dict, now: str) -> None:
        """Write the vault index document."""
        content = self._frontmatter(
            type="index", last_updated=now, confidence=1.0, sources=["onboarding"]
        )
        content += f"""# Taste Vault

**Project**: {data.get('brand_name', 'Untitled')}
**Created**: {now}
**Platforms**: {', '.join(data.get('platforms', ['xiaohongshu']))}

## Structure

- `style/` — Writing style, tone, structure, vocabulary
- `preferences/` — User edits, patterns, explicit rules
- `competitors/` — Lane trends, competitor insights
- `context/` — Brand, audience, topic history
- `evolution/` — Change log, weekly digests
"""
        (root / "_index.md").write_text(content, encoding="utf-8")

    async def _write_style_docs(
        self, root: Path, data: dict, now: str, source: str
    ) -> None:
        """Write style directory documents."""
        # tone.md
        tone = data.get("tone", "专业但亲和")
        style_analysis = data.get("style_analysis", {})
        tone_content = self._frontmatter(
            type="style", last_updated=now, confidence=0.85, sources=[source]
        )
        tone_content += f"""# Tone Profile

{tone}

## Key Characteristics

- 语气: {tone}
- 情感倾向: {style_analysis.get('tone', '中性偏积极')}
- 幽默程度: 适度
- 正式程度: 半正式

## Examples

(Will be populated from content imports and edits)
"""
        (root / "style" / "tone.md").write_text(tone_content, encoding="utf-8")

        # structure.md
        structure = data.get("structure", "先给结论，再解释")
        structure_content = self._frontmatter(
            type="style", last_updated=now, confidence=0.80, sources=[source]
        )
        structure_content += f"""# Structure Preferences

{structure}

## Patterns

- 开头风格: 直接切入主题
- 段落长度: {style_analysis.get('paragraph_avg_length', '3-5句')}
- 句子长度: {style_analysis.get('sentence_avg_length', '15-25字')}
- 结尾风格: 总结或call-to-action
- 列表偏好: 适度使用
"""
        (root / "style" / "structure.md").write_text(structure_content, encoding="utf-8")

        # vocabulary.md
        vocab = data.get("vocabulary_level", "专业但不晦涩")
        vocabulary_content = self._frontmatter(
            type="style", last_updated=now, confidence=0.75, sources=[source]
        )
        vocabulary_content += f"""# Vocabulary Profile

**Level**: {vocab}

## Signature Phrases

{self._format_list(style_analysis.get('signature_phrases', []))}

## Avoid

- 过度网络用语
- 低俗表达
- 无意义的语气词堆砌

## Domain Terminology

(Will be populated from content analysis)
"""
        (root / "style" / "vocabulary.md").write_text(vocabulary_content, encoding="utf-8")

        # visual.md
        visual = data.get("visual_style", "清新简约")
        visual_content = self._frontmatter(
            type="style", last_updated=now, confidence=0.70, sources=[source]
        )
        visual_content += f"""# Visual Style

**Aesthetic**: {visual}

## Image Preferences

- 配图风格: {visual}
- 排版偏好: 简洁留白
- emoji 使用: 适度点缀

## Platform-specific Visual

(Will be populated per platform)
"""
        (root / "style" / "visual.md").write_text(visual_content, encoding="utf-8")

        # platform-adaptations.md
        platforms = data.get("platforms", ["xiaohongshu"])
        adaptations_content = self._frontmatter(
            type="style", last_updated=now, confidence=0.70, sources=[source]
        )
        adaptations_content += "# Platform Adaptations\n\n"

        platform_defaults = {
            "xiaohongshu": "短句、emoji点缀、话题标签、口语化、分行排版",
            "wechat": "长文章、深度分析、正式语气、段落清晰",
            "weibo": "简短有力、热点关联、话题标签",
            "zhihu": "专业深度、数据支撑、逻辑严密",
            "douyin": "口语化、节奏感、悬念开头",
            "bilibili": "年轻化、梗文化、互动感",
        }

        for platform in platforms:
            default_style = platform_defaults.get(platform, "标准风格")
            adaptations_content += f"""## {platform}

{default_style}

- 标题风格: 待学习
- 正文长度: 平台默认
- 互动策略: 待学习

"""
        (root / "style" / "platform-adaptations.md").write_text(
            adaptations_content, encoding="utf-8"
        )

    async def _write_preference_docs(
        self, root: Path, data: dict, now: str, source: str
    ) -> None:
        """Write preferences directory documents."""
        # edits-log.md
        edits_content = self._frontmatter(
            type="preference", last_updated=now, confidence=1.0, sources=[source]
        )
        edits_content += """# Edit Log

Records of user edits to AI-generated content. Used to learn preferences over time.

---

"""
        (root / "preferences" / "edits-log.md").write_text(edits_content, encoding="utf-8")

        # patterns.md
        patterns_content = self._frontmatter(
            type="preference", last_updated=now, confidence=0.60, sources=[source]
        )
        patterns_content += """# Learned Patterns

Patterns extracted from repeated user edits. Higher confidence = more consistent behavior.

## High Confidence (>0.8)

(None yet — will be populated from edits)

## Medium Confidence (0.5-0.8)

(None yet)

## Low Confidence (<0.5)

(None yet)
"""
        (root / "preferences" / "patterns.md").write_text(patterns_content, encoding="utf-8")

        # explicit-rules.md
        rules = data.get("explicit_rules", [])
        rules_content = self._frontmatter(
            type="preference", last_updated=now, confidence=1.0, sources=[source]
        )
        rules_content += "# Explicit Rules\n\nHard rules that must ALWAYS be followed.\n\n"
        if rules:
            for rule in rules:
                rules_content += f"- {rule}\n"
        else:
            rules_content += "(No explicit rules set during onboarding)\n"
        (root / "preferences" / "explicit-rules.md").write_text(
            rules_content, encoding="utf-8"
        )

        # conflicts.md
        conflicts_content = self._frontmatter(
            type="preference", last_updated=now, confidence=0.50, sources=[source]
        )
        conflicts_content += """# Conflicts & Contradictions

Records cases where user edits contradict previous patterns.
Used to detect evolving preferences vs. one-off exceptions.

---

(No conflicts detected yet)
"""
        (root / "preferences" / "conflicts.md").write_text(
            conflicts_content, encoding="utf-8"
        )

    async def _write_competitor_docs(
        self, root: Path, data: dict, now: str, source: str
    ) -> None:
        """Write competitors directory documents."""
        competitors = data.get("competitors", [])
        lane_content = self._frontmatter(
            type="competitor", last_updated=now, confidence=0.65, sources=[source]
        )
        lane_content += "# Lane Trends\n\nCompetitor insights and lane-level trends.\n\n"

        if competitors:
            for comp in competitors:
                name = comp.get("name", comp.get("url", "Unknown"))
                platform = comp.get("platform", "unknown")
                lane_content += f"## {name} ({platform})\n\n"
                notes = comp.get("notes", "")
                if notes:
                    lane_content += f"{notes}\n\n"
                lane_content += "- Insights: (pending analysis)\n\n"
        else:
            lane_content += "(No competitors added during onboarding)\n"

        (root / "competitors" / "lane-trends.md").write_text(
            lane_content, encoding="utf-8"
        )

    async def _write_context_docs(
        self, root: Path, data: dict, now: str, source: str
    ) -> None:
        """Write context directory documents."""
        # brand.md
        brand_name = data.get("brand_name", "")
        brand_desc = data.get("brand_description", "")
        brand_content = self._frontmatter(
            type="context", last_updated=now, confidence=0.90, sources=[source]
        )
        brand_content += f"""# Brand Context

**Name**: {brand_name}

## Description

{brand_desc if brand_desc else '(Not set during onboarding)'}

## Values

(Will be refined over time)

## Voice Guidelines

(Derived from style/tone.md)
"""
        (root / "context" / "brand.md").write_text(brand_content, encoding="utf-8")

        # audience.md
        audience = data.get("target_audience", "")
        audience_content = self._frontmatter(
            type="context", last_updated=now, confidence=0.75, sources=[source]
        )
        audience_content += f"""# Audience Profile

{audience if audience else '(Not defined during onboarding)'}

## Demographics

- Age range: 待确认
- Interests: 待确认
- Pain points: 待确认

## Engagement Patterns

(Will be populated from analytics)
"""
        (root / "context" / "audience.md").write_text(audience_content, encoding="utf-8")

        # topics-history.md
        topics = data.get("content_topics", [])
        topics_content = self._frontmatter(
            type="context", last_updated=now, confidence=0.70, sources=[source]
        )
        topics_content += "# Topics History\n\nContent topics and their performance.\n\n"
        topics_content += "## Defined Topics\n\n"
        if topics:
            for topic in topics:
                topics_content += f"- {topic}\n"
        else:
            topics_content += "(No topics defined during onboarding)\n"
        topics_content += "\n## Published Topics\n\n(Will be populated after publishing)\n"
        (root / "context" / "topics-history.md").write_text(
            topics_content, encoding="utf-8"
        )

    async def _write_evolution_docs(self, root: Path, now: str, source: str) -> None:
        """Write evolution directory documents."""
        # changelog.md
        changelog_content = self._frontmatter(
            type="evolution", last_updated=now, confidence=1.0, sources=[source]
        )
        changelog_content += f"""# Taste Evolution Changelog

Records significant changes to the taste profile over time.

---

## {now[:10]} — Vault Initialized

- Initial vault created from onboarding
- All documents set to baseline confidence levels
- Awaiting user edits and content performance data
"""
        (root / "evolution" / "changelog.md").write_text(
            changelog_content, encoding="utf-8"
        )

        # weekly-digest.md
        digest_content = self._frontmatter(
            type="evolution", last_updated=now, confidence=1.0, sources=[source]
        )
        digest_content += """# Weekly Digest

Weekly summaries of taste evolution, edit patterns, and content performance.

---

(First digest will be generated after one week of activity)
"""
        (root / "evolution" / "weekly-digest.md").write_text(
            digest_content, encoding="utf-8"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _frontmatter(
        type: str,
        last_updated: str,
        confidence: float,
        sources: list[str],
    ) -> str:
        """Generate YAML frontmatter block."""
        sources_str = ", ".join(sources)
        return (
            f"---\n"
            f"type: {type}\n"
            f"last_updated: {last_updated}\n"
            f"confidence: {confidence}\n"
            f"sources: [{sources_str}]\n"
            f"---\n\n"
        )

    @staticmethod
    def _format_list(items: list[str]) -> str:
        """Format a list of items as markdown bullets."""
        if not items:
            return "(None identified yet)\n"
        return "\n".join(f"- {item}" for item in items) + "\n"
