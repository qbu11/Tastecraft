"""Onboarding engine — conversational AI for building user taste vaults.

Orchestrates a structured-but-adaptive interview flow:
1. Lane Positioning — platforms, domain, audience, desired CTA
2. Style Dialogue — tone samples, banned expressions, structure prefs
3. Content Import — fetch & analyze existing content via TikHub
4. Competitor Setup — async competitor analysis
5. Aha Moment — generate first content piece with collected signals
"""

import json
import logging
import uuid
from datetime import datetime

import anthropic

from app.core.config import settings
from app.schemas.onboarding import AIResponse, StyleAnalysis

logger = logging.getLogger(__name__)

STEPS = [
    "lane_positioning",
    "style_dialogue",
    "content_import",
    "competitor_setup",
    "first_generation",
]

STEP_LABELS = {
    "lane_positioning": "赛道定位",
    "style_dialogue": "风格对话",
    "content_import": "内容导入",
    "competitor_setup": "竞品设置",
    "first_generation": "首篇生成",
}

# System prompt for the onboarding conversation
ONBOARDING_SYSTEM_PROMPT = """你是 TasteCraft 的品味顾问，正在通过对话帮助用户建立个人品味画像。

你的目标：
- 用自然、温暖的对话方式了解用户的内容创作偏好
- 不要像表单一样逐个问问题，要像朋友聊天一样自然过渡
- 根据用户的回答灵活调整后续问题
- 每次回复控制在 2-3 句话内，简洁有力
- 全程使用中文

当前处于 {step_label} 阶段。

{step_instructions}

已收集的信息：
{collected_data}

对话历史：
{conversation_history}

请根据用户最新的回复，给出下一个自然的回应和引导问题。
如果当前阶段的关键信息已收集完毕，在回复末尾加上 [STEP_COMPLETE] 标记。

输出格式（JSON）：
{{
  "message": "你的回复内容",
  "collected_fields": {{"field_name": "extracted_value"}},
  "quick_replies": ["建议回复1", "建议回复2"],
  "step_complete": false
}}"""

STEP_INSTRUCTIONS = {
    "lane_positioning": """赛道定位阶段需要了解：
- platforms: 用户活跃的平台（小红书/微信公众号/微博/知乎/抖音/B站）
- domain: 内容领域（科技/生活/商业/教育/健康等）
- target_audience: 目标读者画像和痛点
- desired_action: 希望读者看完后做什么

如果用户的回答已涵盖以上所有要素，标记 step_complete = true。
开场白要简短有力，直奔主题。""",
    "style_dialogue": """风格对话阶段需要了解：
- tone_preference: 语气偏好（犀利/温和/幽默/严肃/亲和）
- banned_expressions: 绝对不用的表达方式或词汇
- structure_preference: 结构偏好（先结论后展开 / 层层递进 / 故事引入）
- paragraph_length: 段落长度偏好（短句连发 / 中等 / 长段深度）
- style_sample_choice: 最接近的风格样本

先给出 4 个风格样本让用户选择，然后深入追问。
风格样本：
A) 干货流 — 直接给答案，条理清晰，数据说话
B) 故事流 — 以亲身经历切入，感性共鸣，最后点题
C) 观点流 — 犀利洞察，敢于反共识，金句频出
D) 教程流 — 手把手拆解，step by step，小白友好

在 quick_replies 中提供选项。""",
    "content_import": """内容导入阶段（可选）：
- 提醒用户可以导入已有内容（小红书主页链接、微信文章链接等）
- 说明导入的好处：AI 会分析写作风格，让生成内容更像本人
- 如果用户选择跳过，直接标记 step_complete = true
- 在 quick_replies 中提供"跳过这一步"选项""",
    "competitor_setup": """竞品设置阶段（可选）：
- 询问用户有没有欣赏或想对标的同领域账号
- 说明好处：分析竞品风格帮助找到差异化方向
- 如果用户选择跳过，直接标记 step_complete = true
- 在 quick_replies 中提供"暂时跳过"选项""",
    "first_generation": """首篇生成阶段：
- 总结前面收集到的所有品味信息
- 告知用户即将基于品味画像生成第一篇内容
- 询问用户想要生成什么主题的内容
- 标记 step_complete = true 当用户确认主题后""",
}

FIRST_MESSAGES = {
    "lane_positioning": (
        "你好！我是你的品味顾问。接下来几分钟，"
        "我会通过对话了解你的创作风格，帮你建立专属的品味画像。\n\n"
        "先聊聊基础的 —— 你平时主要在哪些平台发内容？"
    ),
}


class OnboardingEngine:
    """Conversational AI engine for user onboarding."""

    def __init__(self) -> None:
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    # ── Public API ──────────────────────────────────────────────────────────

    async def start_session(self, user_id: int) -> dict:
        """Initialize a new onboarding session and return first AI message."""
        session_id = str(uuid.uuid4())
        first_message = FIRST_MESSAGES["lane_positioning"]
        quick_replies = ["小红书", "微信公众号", "小红书 + 公众号", "其他平台"]

        session_data = {
            "id": session_id,
            "user_id": user_id,
            "current_step": STEPS[0],
            "step_index": 0,
            "messages": [{"role": "assistant", "content": first_message}],
            "collected_data": {},
            "imported_content_urls": [],
            "imported_content_count": 0,
            "competitors_added": 0,
            "competitor_urls": [],
            "created_at": datetime.utcnow().isoformat(),
        }

        return {
            "session_id": session_id,
            "session_data": session_data,
            "first_message": first_message,
            "current_step": STEPS[0],
            "quick_replies": quick_replies,
        }

    async def process_message(
        self,
        session_data: dict,
        user_message: str,
    ) -> AIResponse:
        """Process user message and generate AI response."""
        # Add user message to history
        session_data["messages"].append({"role": "user", "content": user_message})

        current_step = session_data["current_step"]
        step_index = session_data["step_index"]

        # Build conversation history string
        conversation_history = self._format_conversation(session_data["messages"][-10:])
        collected_data = json.dumps(session_data.get("collected_data", {}), ensure_ascii=False)

        # Call Claude to generate response
        step_label = STEP_LABELS.get(current_step, current_step)
        instructions = STEP_INSTRUCTIONS.get(current_step, "")

        system = ONBOARDING_SYSTEM_PROMPT.format(
            step_label=step_label,
            step_instructions=instructions,
            collected_data=collected_data,
            conversation_history=conversation_history,
        )

        response_text = await self._call_claude(system, user_message)
        parsed = self._parse_ai_response(response_text)

        # Update collected data
        if parsed.get("collected_fields"):
            session_data.setdefault("collected_data", {}).update(parsed["collected_fields"])

        # Check if step is complete
        ai_message = parsed.get("message", "让我们继续吧！")
        quick_replies = parsed.get("quick_replies", [])
        step_complete = parsed.get("step_complete", False)

        show_import_ui = False
        show_competitor_ui = False

        if step_complete:
            # Advance to next step
            next_index = step_index + 1
            if next_index < len(STEPS):
                session_data["current_step"] = STEPS[next_index]
                session_data["step_index"] = next_index

                # Generate transition message for new step
                new_step = STEPS[next_index]
                if new_step == "content_import":
                    show_import_ui = True
                elif new_step == "competitor_setup":
                    show_competitor_ui = True
            else:
                # All steps done
                session_data["current_step"] = "completed"

        # Add assistant message to history
        session_data["messages"].append({"role": "assistant", "content": ai_message})

        is_complete = session_data["current_step"] == "completed"

        return AIResponse(
            message=ai_message,
            current_step=session_data["current_step"],
            step_index=session_data.get("step_index", step_index),
            quick_replies=quick_replies,
            show_import_ui=show_import_ui,
            show_competitor_ui=show_competitor_ui,
            is_complete=is_complete,
        )

    async def analyze_imported_content(self, contents: list[str]) -> StyleAnalysis:
        """Analyze imported content URLs/text for style patterns."""
        # Combine content for analysis
        combined = "\n---\n".join(contents[:5])  # Limit to 5 pieces

        system = """你是一个内容风格分析专家。分析以下内容的写作风格特征。

输出 JSON 格式：
{
  "sentence_avg_length": 15.5,
  "paragraph_avg_length": 80.0,
  "tone": "专业且亲和",
  "vocabulary_level": "中等偏上",
  "structure_preference": "先结论后展开",
  "topic_distribution": {"科技": 0.4, "商业": 0.3, "生活": 0.3},
  "signature_phrases": ["说白了", "本质上"],
  "summary": "一句话总结这个人的写作风格"
}"""

        response = await self._call_claude(system, f"分析以下内容的风格：\n\n{combined[:8000]}")
        parsed = self._parse_json_response(response)

        return StyleAnalysis(
            sentence_avg_length=parsed.get("sentence_avg_length", 15.0),
            paragraph_avg_length=parsed.get("paragraph_avg_length", 80.0),
            tone=parsed.get("tone", "待分析"),
            vocabulary_level=parsed.get("vocabulary_level", "中等"),
            structure_preference=parsed.get("structure_preference", "混合"),
            topic_distribution=parsed.get("topic_distribution", {}),
            signature_phrases=parsed.get("signature_phrases", []),
            summary=parsed.get("summary", "风格分析完成"),
        )

    async def generate_first_content(
        self,
        collected_data: dict,
        style_analysis: StyleAnalysis | None = None,
        topic: str | None = None,
    ) -> str:
        """Generate the first piece of content using collected taste signals (aha moment)."""
        taste_context = json.dumps(collected_data, ensure_ascii=False)
        style_info = ""
        if style_analysis:
            style_info = f"\n\n风格分析结果：{style_analysis.model_dump_json()}"

        platform = collected_data.get("platforms", "小红书")
        if isinstance(platform, list):
            platform = platform[0] if platform else "小红书"

        domain = collected_data.get("domain", "通用")
        target_topic = topic or f"{domain}领域的实用内容"

        system = f"""你是 TasteCraft 内容创作引擎。根据用户的品味画像生成一篇高质量内容。

用户品味画像：
{taste_context}
{style_info}

目标平台：{platform}
内容领域：{domain}

要求：
- 严格匹配用户偏好的语气和结构
- 内容要有干货、有洞察
- 适合 {platform} 平台的格式和长度
- 标题要有吸引力
- 如果是小红书，加入适当的 emoji 和话题标签"""

        content = await self._call_claude(system, f"请为我写一篇关于「{target_topic}」的内容")
        return content

    async def build_initial_vault(self, session_data: dict) -> dict:
        """Construct the initial taste vault from all collected signals."""
        collected = session_data.get("collected_data", {})
        style_analysis = session_data.get("style_analysis")

        vault = {
            "version": 1,
            "created_at": datetime.utcnow().isoformat(),
            "platforms": collected.get("platforms", []),
            "domain": collected.get("domain", ""),
            "target_audience": collected.get("target_audience", ""),
            "desired_action": collected.get("desired_action", ""),
            "tone": {
                "preference": collected.get("tone_preference", ""),
                "banned_expressions": collected.get("banned_expressions", []),
            },
            "structure": {
                "preference": collected.get("structure_preference", ""),
                "paragraph_length": collected.get("paragraph_length", ""),
            },
            "style_sample_choice": collected.get("style_sample_choice", ""),
            "imported_style_analysis": style_analysis,
            "competitors": session_data.get("competitor_urls", []),
        }

        return vault

    # ── Private Methods ─────────────────────────────────────────────────────

    async def _call_claude(self, system: str, user_message: str) -> str:
        """Call Claude API and return text response."""
        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error("Claude API call failed: %s", e)
            return json.dumps({
                "message": "抱歉，我需要想一想。能再说一次吗？",
                "collected_fields": {},
                "quick_replies": [],
                "step_complete": False,
            })

    def _format_conversation(self, messages: list[dict]) -> str:
        """Format message history for prompt context."""
        lines = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "AI"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def _parse_ai_response(self, text: str) -> dict:
        """Parse AI response JSON, with fallback."""
        parsed = self._parse_json_response(text)
        if parsed:
            return parsed
        # Fallback: treat entire text as message
        return {
            "message": text.replace("[STEP_COMPLETE]", "").strip(),
            "collected_fields": {},
            "quick_replies": [],
            "step_complete": "[STEP_COMPLETE]" in text,
        }

    def _parse_json_response(self, text: str) -> dict:
        """Extract JSON from text response."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON block
        import re

        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {}


# Module-level singleton
onboarding_engine = OnboardingEngine()
