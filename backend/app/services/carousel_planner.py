"""AI-powered carousel structure planner.

Uses Claude to break long-form content into carousel slide text
and suggest a visual style that matches the user's taste vault.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.core.config import settings
from app.services.visual_engine import CardStyle, PRESET_STYLES

logger = logging.getLogger(__name__)


@dataclass
class CarouselPlan:
    """Structured plan for a carousel."""

    cover_title: str
    cover_subtitle: str
    slides: list[dict]  # [{text, subtitle?}]
    cta_text: str


_PLAN_SYSTEM = """\
You are a carousel planning assistant for Chinese social media (Xiaohongshu).
Given article content, break it into a carousel of 4-6 slides.

Return JSON with this exact structure (no markdown, no wrapping):
{
  "cover_title": "短标题（10字以内）",
  "cover_subtitle": "副标题",
  "slides": [
    {"text": "第1页正文（每页50-80字）", "subtitle": "可选小标题"},
    ...
  ],
  "cta_text": "行动号召语（如：关注我获取更多干货）"
}

Rules:
- Each slide text should be 50-80 Chinese characters max.
- Cover title should be punchy and concise (under 10 chars).
- CTA should encourage follow / like / save.
- Output ONLY valid JSON, no extra text.
"""

_STYLE_SYSTEM = """\
You are a visual style advisor for Chinese social media carousel cards.
Given the content topic and optional taste vault data, suggest a visual style.

Return JSON with this exact structure (no markdown, no wrapping):
{
  "preset": "dark_elegant|warm_cream|ocean_blue|forest_green",
  "accent_color": "#hexcode",
  "reasoning": "一句话解释选择理由"
}

Available presets: dark_elegant (深色高级), warm_cream (暖色温馨), ocean_blue (蓝色科技), forest_green (绿色自然).
Pick the one most appropriate for the content topic and taste.
Output ONLY valid JSON, no extra text.
"""


class CarouselPlanner:
    """Uses Claude to plan carousel structure from content."""

    def __init__(self) -> None:
        self._client: object | None = None

    def _get_client(self):
        """Lazy-init Anthropic async client."""
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def plan_carousel(
        self,
        content: str,
        platform: str = "xiaohongshu",
        num_slides: int = 5,
    ) -> CarouselPlan:
        """Use Claude to break content into carousel slides.

        Returns a :class:`CarouselPlan` with cover title, slide texts, and CTA.
        """
        client = self._get_client()

        user_msg = (
            f"平台: {platform}\n"
            f"目标页数: {num_slides}（不含封面和CTA页）\n\n"
            f"文章内容:\n{content[:3000]}"
        )

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=_PLAN_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )

        raw = response.content[0].text.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("CarouselPlanner: failed to parse JSON, using fallback")
            return self._fallback_plan(content, num_slides)

        return CarouselPlan(
            cover_title=data.get("cover_title", "精彩内容"),
            cover_subtitle=data.get("cover_subtitle", ""),
            slides=data.get("slides", [{"text": content[:200]}]),
            cta_text=data.get("cta_text", "关注我，获取更多精彩内容"),
        )

    async def suggest_visual_style(
        self,
        content: str,
        taste_vault: dict | None = None,
    ) -> CardStyle:
        """Suggest visual style based on content and user's taste."""
        client = self._get_client()

        taste_ctx = ""
        if taste_vault:
            taste_ctx = f"\n\n用户品味画像:\n{json.dumps(taste_vault, ensure_ascii=False)[:500]}"

        user_msg = f"内容摘要:\n{content[:500]}{taste_ctx}"

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            system=_STYLE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )

        raw = response.content[0].text.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Style suggestion parse failed; using dark_elegant")
            return PRESET_STYLES["dark_elegant"]

        preset_name = data.get("preset", "dark_elegant")
        base = PRESET_STYLES.get(preset_name, PRESET_STYLES["dark_elegant"])

        # Apply suggested accent colour override
        accent = data.get("accent_color")
        if accent and isinstance(accent, str) and accent.startswith("#") and len(accent) == 7:
            return CardStyle(
                background_color=base.background_color,
                accent_color=accent,
                text_color=base.text_color,
                font_name=base.font_name,
                title_size=base.title_size,
                body_size=base.body_size,
                card_width=base.card_width,
                card_height=base.card_height,
                padding=base.padding,
            )

        return base

    @staticmethod
    def _fallback_plan(content: str, num_slides: int) -> CarouselPlan:
        """Deterministic fallback when AI parsing fails."""
        # Split content evenly across slides
        chunk_size = max(len(content) // max(num_slides, 1), 50)
        slides = []
        for i in range(num_slides):
            start = i * chunk_size
            text = content[start : start + chunk_size]
            if text:
                slides.append({"text": text})
        if not slides:
            slides = [{"text": content[:200]}]

        return CarouselPlan(
            cover_title="精彩内容",
            cover_subtitle="",
            slides=slides,
            cta_text="关注我，获取更多精彩内容",
        )
