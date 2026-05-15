"""Onboarding engine — conversational AI for building user taste vaults.

Orchestrates a structured-but-adaptive interview flow:
1. Lane Positioning — platforms, domain, audience, desired CTA
2. Style Dialogue — tone samples, banned expressions, structure prefs
3. Content Import — fetch & analyze existing content via TikHub (v2: auto-import from profile)
4. Competitor Setup — async competitor analysis
5. Aha Moment — generate first content piece with collected signals
"""

import json
import logging
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

import anthropic

from app.core.config import settings
from app.schemas.onboarding import AIResponse, ImportResult, StyleAnalysis

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

    # ── v2: Auto-Import from Profile ───────────────────────────────────────

    async def auto_import_from_profile(
        self, platform: str, profile_url: str
    ) -> ImportResult:
        """Auto-fetch user's recent posts from their profile URL via TikHub.

        Steps:
        1. Parse profile URL to extract user_id (platform-specific)
        2. Fetch recent posts (last 50) via TikHub
        3. Analyze all posts for style patterns
        4. Generate comprehensive style analysis
        5. Return analysis + post count + style features
        """
        from tikhub import Client as TikHubClient

        parsed_id = self._parse_profile_url(platform, profile_url)
        if not parsed_id:
            return ImportResult(
                success=False,
                post_count=0,
                style_analysis=None,
                style_features=[],
                error=f"无法从链接中提取用户 ID: {profile_url}",
            )

        # Fetch posts via TikHub
        client = TikHubClient(api_key=settings.tikhub_api_key)
        posts: list[str] = []

        try:
            if platform == "xiaohongshu":
                resp = await client.xiaohongshu_web.get_user_notes_v2(user_id=parsed_id)
                for note in (resp.get("data", {}).get("notes", []) or [])[:50]:
                    title = note.get("display_title", "")
                    desc = note.get("desc", "")
                    posts.append(f"{title}\n{desc}" if title else desc)
            elif platform == "weibo":
                resp = await client.weibo_web.fetch_user_posts(uid=parsed_id)
                for item in (resp.get("data", {}).get("list", []) or [])[:50]:
                    posts.append(item.get("text_raw", "") or item.get("text", ""))
            elif platform == "zhihu":
                resp = await client.zhihu_web.fetch_user_articles(user_url_token=parsed_id)
                for article in (resp.get("data", []) or [])[:50]:
                    title = article.get("title", "")
                    excerpt = article.get("excerpt", "")
                    posts.append(f"{title}\n{excerpt}" if title else excerpt)
            elif platform == "douyin":
                resp = await client.douyin_web.fetch_user_posts(sec_uid=parsed_id)
                for video in (resp.get("data", {}).get("aweme_list", []) or [])[:50]:
                    posts.append(video.get("desc", ""))
            else:
                return ImportResult(
                    success=False,
                    post_count=0,
                    style_analysis=None,
                    style_features=[],
                    error=f"不支持自动导入的平台: {platform}",
                )
        except Exception as e:
            logger.error("TikHub fetch failed for %s/%s: %s", platform, parsed_id, e)
            return ImportResult(
                success=False,
                post_count=0,
                style_analysis=None,
                style_features=[],
                error=f"获取内容失败: {e}",
            )

        # Filter empty posts
        posts = [p.strip() for p in posts if p and p.strip()]
        if not posts:
            return ImportResult(
                success=False,
                post_count=0,
                style_analysis=None,
                style_features=[],
                error="未找到任何内容，请确认主页链接是否正确",
            )

        # Compute bulk style features locally
        style_features = self._compute_bulk_style_features(posts)

        # AI-powered deep analysis on combined content
        style_analysis = await self.analyze_imported_content(posts)

        return ImportResult(
            success=True,
            post_count=len(posts),
            style_analysis=style_analysis,
            style_features=style_features,
            error=None,
        )

    def _parse_profile_url(self, platform: str, url: str) -> str | None:
        """Extract user ID from a profile URL based on platform."""
        url = url.strip()

        if platform == "xiaohongshu":
            # https://www.xiaohongshu.com/user/profile/5a1234567890abcdef
            m = re.search(r"xiaohongshu\.com/user/profile/([a-zA-Z0-9]+)", url)
            if m:
                return m.group(1)
            # Short links: https://xhslink.com/xxxxx — return raw for TikHub resolution
            m = re.search(r"xhslink\.com/([a-zA-Z0-9]+)", url)
            if m:
                return m.group(1)

        elif platform == "weibo":
            # https://weibo.com/u/1234567890
            m = re.search(r"weibo\.com/u/(\d+)", url)
            if m:
                return m.group(1)
            # https://weibo.com/custom_name
            m = re.search(r"weibo\.com/([a-zA-Z0-9_]+)", url)
            if m:
                return m.group(1)

        elif platform == "zhihu":
            # https://www.zhihu.com/people/some-url-token
            m = re.search(r"zhihu\.com/people/([a-zA-Z0-9_-]+)", url)
            if m:
                return m.group(1)

        elif platform == "douyin":
            # https://www.douyin.com/user/MS4wLjAB...
            m = re.search(r"douyin\.com/user/([a-zA-Z0-9_-]+)", url)
            if m:
                return m.group(1)

        return None

    def _compute_bulk_style_features(self, posts: list[str]) -> list[str]:
        """Compute statistical style features from a batch of posts."""
        features: list[str] = []

        # Average paragraph length
        all_paragraphs = []
        for post in posts:
            paragraphs = [p.strip() for p in post.split("\n") if p.strip()]
            all_paragraphs.extend(paragraphs)
        if all_paragraphs:
            avg_para_len = sum(len(p) for p in all_paragraphs) / len(all_paragraphs)
            if avg_para_len < 50:
                features.append("短段落偏好（平均 < 50 字）")
            elif avg_para_len > 150:
                features.append("长段落偏好（平均 > 150 字）")
            else:
                features.append(f"中等段落长度（平均 {avg_para_len:.0f} 字）")

        # Title patterns
        question_count = 0
        number_list_count = 0
        statement_count = 0
        for post in posts:
            first_line = post.split("\n")[0].strip()
            if "？" in first_line or "?" in first_line:
                question_count += 1
            elif re.search(r"\d+\s*(个|条|步|招|种|大|小)", first_line):
                number_list_count += 1
            else:
                statement_count += 1

        title_patterns = []
        if question_count > len(posts) * 0.3:
            title_patterns.append("提问式")
        if number_list_count > len(posts) * 0.3:
            title_patterns.append("数字列表式")
        if statement_count > len(posts) * 0.3:
            title_patterns.append("陈述式")
        if title_patterns:
            features.append(f"标题偏好: {', '.join(title_patterns)}")

        # Common opening words/phrases (first 10 chars of each post)
        openers = Counter()
        for post in posts:
            first_line = post.split("\n")[0].strip()
            if len(first_line) >= 4:
                openers[first_line[:4]] += 1
        frequent_openers = [k for k, v in openers.most_common(5) if v >= 2]
        if frequent_openers:
            features.append(f"常用开头: {'、'.join(frequent_openers)}")

        # Vocabulary uniqueness — words appearing >= 3 times across posts
        all_text = " ".join(posts)
        # Simple Chinese word frequency (2-4 char segments)
        word_freq: Counter = Counter()
        for post in posts:
            for length in range(2, 5):
                for i in range(len(post) - length + 1):
                    segment = post[i : i + length]
                    if segment.strip() and not segment.isspace():
                        word_freq[segment] += 1
        # Filter to meaningful frequent terms (appear in >= 3 posts)
        post_presence: Counter = Counter()
        for word, _ in word_freq.most_common(200):
            count_in_posts = sum(1 for p in posts if word in p)
            if count_in_posts >= 3:
                post_presence[word] = count_in_posts
        signature_words = [w for w, _ in post_presence.most_common(10)]
        if signature_words:
            features.append(f"高频词汇: {'、'.join(signature_words[:8])}")

        # Content structure distribution
        has_list = sum(1 for p in posts if re.search(r"[1-9][.、）)]", p))
        has_emoji = sum(1 for p in posts if re.search(r"[\U0001F300-\U0001FAFF]", p))
        has_hashtag = sum(1 for p in posts if "#" in p)
        struct_notes = []
        if has_list > len(posts) * 0.3:
            struct_notes.append(f"列表结构 ({has_list}/{len(posts)})")
        if has_emoji > len(posts) * 0.3:
            struct_notes.append(f"使用 emoji ({has_emoji}/{len(posts)})")
        if has_hashtag > len(posts) * 0.3:
            struct_notes.append(f"使用话题标签 ({has_hashtag}/{len(posts)})")
        if struct_notes:
            features.append(f"内容结构: {', '.join(struct_notes)}")

        return features

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
