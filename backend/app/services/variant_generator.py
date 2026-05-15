"""Multi-variant content generation service.

Generates 2-3 different creative approaches for a given topic,
then expands the chosen variant into full content via streaming.
"""

import json
import logging
import uuid
from collections.abc import AsyncIterator

import anthropic

from app.core.config import settings
from app.schemas.generate import ContentVariant
from app.services.streaming import PLATFORM_GUIDES, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


VARIANT_SYSTEM_PROMPT = """You are TasteCraft, an AI content strategist for Chinese social media.
Your job is to propose multiple creative angles for a given topic.
Each angle should be distinctly different in approach, tone, or perspective.
Always respond in Chinese. Return valid JSON only, no markdown fences."""

VARIANT_USER_TEMPLATE = """请为以下选题提出 {num_variants} 个不同的创作方向。

选题：{topic}
{direction_line}
目标平台：{platform}
{taste_line}

每个方向需要包含：
- angle: 创作角度的标题（简短有力，10字以内）
- hook: 开头钩子（吸引读者的前1-2句话）
- outline: 内容大纲（3-5个要点的列表）
- tone: 风格描述（如"专业理性"、"轻松口语"、"故事叙事"等）

请以 JSON 数组格式返回，每个元素包含 angle, hook, outline, tone 四个字段。
示例格式：
[
  {{"angle": "...", "hook": "...", "outline": ["...", "..."], "tone": "..."}}
]"""

EXPAND_SYSTEM_TEMPLATE = """You are TasteCraft, an AI content co-creator for Chinese social media.
You are expanding a content outline into a full piece.
Write in Chinese. Be creative, engaging, and authentic.
Follow the specified angle, tone, and outline closely.

Creative angle: {angle}
Tone: {tone}
{platform_guide}
{taste_context}"""

EXPAND_USER_TEMPLATE = """请将以下大纲扩展为完整的{platform}内容。

选题：{topic}
开头钩子：{hook}

大纲：
{outline_text}

请直接输出完整内容，不要输出标题或元数据。保持"{tone}"的风格。"""


class VariantGenerator:
    """Generates multiple content approaches and expands the chosen one."""

    def __init__(self) -> None:
        self.client = _get_client()

    async def generate_variants(
        self,
        topic: str,
        direction: str,
        platform: str,
        taste_context: str,
        num_variants: int = 3,
    ) -> list[ContentVariant]:
        """Generate multiple content approaches for a topic.

        Each variant has: angle, hook, outline, estimated_tone.

        Args:
            topic: The content topic.
            direction: Optional creative direction hint.
            platform: Target platform (xiaohongshu, wechat, weibo).
            taste_context: User taste profile context string.
            num_variants: Number of variants to generate (2-3).

        Returns:
            List of ContentVariant objects.
        """
        direction_line = f"创作方向提示：{direction}" if direction else ""
        taste_line = f"用户品味画像：\n{taste_context}" if taste_context else ""

        platform_guide = PLATFORM_GUIDES.get(platform, "")
        system = VARIANT_SYSTEM_PROMPT
        if platform_guide:
            system += f"\n\n平台指南（{platform}）：{platform_guide}"

        user_prompt = VARIANT_USER_TEMPLATE.format(
            num_variants=num_variants,
            topic=topic,
            direction_line=direction_line,
            platform=platform,
            taste_line=taste_line,
        )

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw_text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()

            variants_data = json.loads(raw_text)

            variants: list[ContentVariant] = []
            for item in variants_data[:num_variants]:
                variant = ContentVariant(
                    id=f"var_{uuid.uuid4().hex[:8]}",
                    angle=item.get("angle", ""),
                    hook=item.get("hook", ""),
                    outline=item.get("outline", []),
                    tone=item.get("tone", ""),
                )
                variants.append(variant)

            return variants

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error("Failed to parse variant response: %s", e)
            # Return a single fallback variant
            return [
                ContentVariant(
                    id=f"var_{uuid.uuid4().hex[:8]}",
                    angle="默认角度",
                    hook=f"关于{topic}，你可能不知道的事...",
                    outline=[f"深入探讨{topic}"],
                    tone="均衡",
                )
            ]
        except anthropic.APIError as e:
            logger.error("Anthropic API error generating variants: %s", e)
            raise

    async def expand_variant(
        self,
        topic: str,
        angle: str,
        hook: str,
        outline: list[str],
        tone: str,
        platform: str,
        taste_context: str = "",
    ) -> AsyncIterator[str]:
        """Expand a chosen variant into full content via streaming.

        Args:
            topic: The original topic.
            angle: The chosen variant's creative angle.
            hook: The chosen variant's opening hook.
            outline: The chosen variant's outline points.
            tone: The chosen variant's tone descriptor.
            platform: Target platform.
            taste_context: User taste profile context.

        Yields:
            Text chunks as they are generated.
        """
        platform_guide = PLATFORM_GUIDES.get(platform, "")
        platform_guide_text = (
            f"平台指南（{platform}）：{platform_guide}" if platform_guide else ""
        )
        taste_text = f"用户品味画像：\n{taste_context}" if taste_context else ""

        system = EXPAND_SYSTEM_TEMPLATE.format(
            angle=angle,
            tone=tone,
            platform_guide=platform_guide_text,
            taste_context=taste_text,
        )

        outline_text = "\n".join(f"- {point}" for point in outline)

        user_prompt = EXPAND_USER_TEMPLATE.format(
            platform=platform,
            topic=topic,
            hook=hook,
            outline_text=outline_text,
            tone=tone,
        )

        try:
            async with self.client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.APIError as e:
            logger.error("Anthropic API error during variant expansion: %s", e)
            raise
