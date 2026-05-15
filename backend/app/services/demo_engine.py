from __future__ import annotations

from pydantic import BaseModel

import anthropic

from app.core.config import settings

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


class TasteTestResult(BaseModel):
    style_features: list[str]
    imitation: str
    similarity_score: float


_TASTE_TEST_PROMPT = """\
You are a writing-style analyst and imitator. The user will provide a paragraph they wrote.

Your job:
1. Identify 3-5 distinctive style features of this text (in Chinese). \
Each feature should be a short phrase (under 15 chars). Examples: \
"短句节奏感强", "善用反问", "口语化表达", "数据驱动论证".
2. Write a NEW paragraph (120-200 chars) on a DIFFERENT topic but \
perfectly imitating the author's style — tone, sentence rhythm, \
vocabulary level, rhetorical devices, everything.
3. Self-rate the similarity of your imitation on a 0-100 scale.

Reply in this EXACT JSON (no markdown fences):
{"style_features": ["...", "..."], "imitation": "...", "similarity_score": 75}
"""


class DemoEngine:
    """Public demo: analyze writing style and generate an imitation."""

    async def taste_test(self, user_text: str) -> TasteTestResult:
        """Analyze user's writing style and generate an imitation.

        Uses Claude with a specific prompt to:
        1. Extract 3-5 style features (Chinese)
        2. Generate a new paragraph on a different topic but same style
        3. Self-rate similarity (0-100)
        """
        client = _get_client()

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=_TASTE_TEST_PROMPT,
            messages=[{"role": "user", "content": user_text}],
        )

        import json

        raw = response.content[0].text.strip()
        # Strip markdown fences if model adds them despite instructions
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[: raw.rfind("```")]
            raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback when model doesn't return valid JSON
            return TasteTestResult(
                style_features=["风格独特", "表达有力", "节奏鲜明"],
                imitation="（AI 正在学习你的风格，请再试一次）",
                similarity_score=50.0,
            )

        return TasteTestResult(
            style_features=data.get("style_features", [])[:5],
            imitation=data.get("imitation", ""),
            similarity_score=max(0.0, min(100.0, float(data.get("similarity_score", 50)))),
        )
