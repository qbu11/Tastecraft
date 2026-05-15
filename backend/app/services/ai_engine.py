import anthropic

from app.core.config import settings

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


SYSTEM_PROMPT = """You are TasteCraft, an AI content co-creator for Chinese social media.
You generate high-quality content tailored to specific platforms and user taste profiles.
Always write in Chinese unless explicitly told otherwise.
Adapt your tone, structure, and style to match the target platform."""


async def generate_content(
    prompt: str,
    platform: str = "xiaohongshu",
    taste_context: str = "",
    user_id: str | None = None,
    project_slug: str | None = None,
) -> str:
    """Generate content with vault-aware taste context.

    If user_id and project_slug are provided but taste_context is empty,
    automatically assembles context from the user's Taste Vault.
    """
    client = _get_client()

    # Auto-assemble vault context if not provided explicitly
    if not taste_context and user_id and project_slug:
        from app.services.taste_vault import TasteVault

        vault = TasteVault(user_id=user_id, project_slug=project_slug)
        if vault.exists():
            taste_context = await vault.get_context_for_generation(
                platform=platform,
                topic=prompt[:100],
            )

    system = SYSTEM_PROMPT
    if taste_context:
        system += f"\n\n## User Taste Profile\n{taste_context}"

    system += f"\n\nTarget platform: {platform}"

    full_text = ""
    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            full_text += text

    return full_text


async def score_content(content: str, taste_context: str) -> float:
    """Score how well content matches the user's taste profile. Returns 0-100."""
    if not taste_context:
        return 50.0

    client = _get_client()

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        system="You are a content quality scorer. Return ONLY a number between 0 and 100.",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Rate how well this content matches the taste profile.\n\n"
                    f"Taste profile:\n{taste_context}\n\n"
                    f"Content:\n{content[:2000]}"
                ),
            }
        ],
    )

    try:
        score_text = response.content[0].text.strip()
        return max(0.0, min(100.0, float(score_text)))
    except (ValueError, IndexError):
        return 50.0
