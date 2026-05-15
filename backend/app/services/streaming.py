"""Streaming content generation service using Anthropic SDK."""

import logging
from collections.abc import AsyncIterator

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


SYSTEM_PROMPT = """You are TasteCraft, an AI content co-creator for Chinese social media.
You generate high-quality content tailored to specific platforms and user taste profiles.
Always write in Chinese unless explicitly told otherwise.
Adapt your tone, structure, and style to match the target platform.
Be creative, engaging, and authentic — avoid generic or formulaic content."""

PLATFORM_GUIDES = {
    "xiaohongshu": (
        "小红书风格：开头用反常识/反问句吸引注意；段落短小精悍（2-3句）；"
        "善用emoji但不过度；结尾引导互动；标题控制20字以内。"
    ),
    "wechat": (
        "微信公众号风格：深度长文；逻辑清晰分段；小标题辅助阅读；"
        "引用数据/故事增强说服力；结尾升华主题。"
    ),
}


class StreamingGenerator:
    """Handles streaming content generation via Anthropic SDK."""

    def __init__(self) -> None:
        self.client = _get_client()

    async def generate_stream(
        self,
        user_prompt: str,
        platform: str = "xiaohongshu",
        taste_context: str = "",
        system_prompt: str | None = None,
        user_id: str | None = None,
        project_slug: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream content generation via Anthropic SDK.

        If user_id and project_slug are provided but taste_context is empty,
        automatically assembles context from the user's Taste Vault.

        Yields chunks of text as they are generated.
        """
        # Auto-assemble vault context if not provided explicitly
        if not taste_context and user_id and project_slug:
            from app.services.taste_vault import TasteVault

            vault = TasteVault(user_id=user_id, project_slug=project_slug)
            if vault.exists():
                taste_context = await vault.get_context_for_generation(
                    platform=platform,
                    topic=user_prompt[:100],
                )

        system = system_prompt or SYSTEM_PROMPT

        if taste_context:
            system += f"\n\n## User Taste Profile\n{taste_context}"

        platform_guide = PLATFORM_GUIDES.get(platform, "")
        if platform_guide:
            system += f"\n\n## Platform Guidelines ({platform})\n{platform_guide}"

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
            logger.error("Anthropic API error during streaming: %s", e)
            raise

    async def rewrite_section(
        self,
        original: str,
        instruction: str,
        taste_context: str = "",
        platform: str = "xiaohongshu",
    ) -> str:
        """Rewrite a section based on natural language instruction.

        Args:
            original: The original text to rewrite.
            instruction: Natural language instruction (e.g., "更口语化", "缩短", "换反问句").
            taste_context: User's taste profile for reference.
            platform: Target platform.

        Returns:
            The rewritten text.
        """
        system = (
            "You are a content editor. Rewrite the given text according to the instruction. "
            "Return ONLY the rewritten text, no explanations or markup. "
            "Maintain the original language (Chinese)."
        )

        if taste_context:
            system += f"\n\nUser taste context:\n{taste_context}"

        platform_guide = PLATFORM_GUIDES.get(platform, "")
        if platform_guide:
            system += f"\n\nPlatform: {platform}\n{platform_guide}"

        prompt = (
            f"Original text:\n{original}\n\n"
            f"Instruction: {instruction}\n\n"
            "Rewritten text:"
        )

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

    async def adjust_style(
        self,
        content: str,
        style_params: dict[str, float],
        platform: str = "xiaohongshu",
        taste_context: str = "",
    ) -> str:
        """Regenerate content with adjusted style parameters.

        Args:
            content: The current content to adjust.
            style_params: Dict with keys formality, length, emotion, expertise (0-100 each).
            platform: Target platform.
            taste_context: User's taste profile.

        Returns:
            The adjusted content.
        """
        # Interpret style parameters
        style_instructions = []

        formality = style_params.get("formality", 50)
        if formality < 30:
            style_instructions.append("非常正式、书面化的语言")
        elif formality > 70:
            style_instructions.append("非常随意、口语化的表达")

        length_param = style_params.get("length", 50)
        if length_param < 30:
            style_instructions.append("保持较长篇幅，展开详细论述")
        elif length_param > 70:
            style_instructions.append("尽量精简，删除冗余")

        emotion = style_params.get("emotion", 50)
        if emotion < 30:
            style_instructions.append("理性客观，多用数据和逻辑")
        elif emotion > 70:
            style_instructions.append("感性动人，注重情感共鸣")

        expertise = style_params.get("expertise", 50)
        if expertise < 30:
            style_instructions.append("专业术语，面向行业人士")
        elif expertise > 70:
            style_instructions.append("通俗易懂，面向普通读者")

        if not style_instructions:
            style_instructions.append("保持均衡的风格")

        system = (
            "You are a content style adjuster. Rewrite the content to match the requested style. "
            "Return ONLY the adjusted content, no explanations. Maintain Chinese."
        )

        if taste_context:
            system += f"\n\nUser taste:\n{taste_context}"

        platform_guide = PLATFORM_GUIDES.get(platform, "")
        if platform_guide:
            system += f"\n\nPlatform: {platform}\n{platform_guide}"

        prompt = (
            f"Current content:\n{content}\n\n"
            f"Style adjustments:\n- " + "\n- ".join(style_instructions) + "\n\n"
            "Adjusted content:"
        )

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

    async def creative_chat(
        self,
        message: str,
        editor_content: str = "",
        platform: str = "xiaohongshu",
        taste_context: str = "",
    ) -> dict[str, str | dict | None]:
        """Process a creative chat message and return AI response.

        Returns:
            Dict with 'reply' and optional 'suggestion'.
        """
        system = (
            "You are TasteCraft, a creative writing partner. "
            "You help users refine their content through conversation. "
            "Always respond in Chinese. Be concise and actionable. "
            "If you suggest changes to the content, include a suggestion action."
        )

        if taste_context:
            system += f"\n\nUser taste:\n{taste_context}"

        context_parts = []
        if editor_content:
            context_parts.append(f"Current editor content:\n{editor_content[:2000]}")
        context_parts.append(f"Target platform: {platform}")

        prompt = "\n\n".join(context_parts) + f"\n\nUser message: {message}"

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        reply_text = response.content[0].text.strip()

        # Simple heuristic: if reply contains change indicators, add a suggestion
        suggestion = None
        change_keywords = ["已修改", "已重写", "建议改为", "可以改成", "试试这样"]
        if any(kw in reply_text for kw in change_keywords):
            suggestion = {
                "type": "change",
                "label": "查看变更",
                "targetSection": None,
            }

        return {"reply": reply_text, "suggestion": suggestion}
