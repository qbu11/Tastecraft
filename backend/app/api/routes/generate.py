"""Content generation streaming endpoints."""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.schemas.generate import (
    ContentVariant,
    ExpandVariantRequest,
    VariantRequest,
    VariantResponse,
)
from app.services.streaming import StreamingGenerator
from app.services.variant_generator import VariantGenerator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generate", tags=["generate"])

_generator: StreamingGenerator | None = None
_variant_generator: VariantGenerator | None = None


def _get_generator() -> StreamingGenerator:
    global _generator
    if _generator is None:
        _generator = StreamingGenerator()
    return _generator


def _get_variant_generator() -> VariantGenerator:
    global _variant_generator
    if _variant_generator is None:
        _variant_generator = VariantGenerator()
    return _variant_generator


# ── Request/Response Models ──


class StreamGenerateRequest(BaseModel):
    topic: str | None = None
    direction: str | None = None
    platform: str = "xiaohongshu"
    taste_context_ids: list[str] = []
    system_prompt: str | None = None
    user_prompt: str | None = None


class RewriteRequest(BaseModel):
    content_id: str
    original_text: str
    instruction: str


class StyleParams(BaseModel):
    formality: float = 50.0
    length: float = 50.0
    emotion: float = 50.0
    expertise: float = 50.0


class AdjustStyleRequest(BaseModel):
    content_id: str
    style_params: StyleParams


class ChatRequest(BaseModel):
    content_id: str | None = None
    message: str
    editor_content: str | None = None
    platform: str = "xiaohongshu"


# ── Endpoints ──


@router.post("/stream")
async def generate_stream(request: StreamGenerateRequest) -> StreamingResponse:
    """Start streaming content generation. Returns Server-Sent Events."""
    generator = _get_generator()

    # Build prompt from topic/direction or raw user_prompt
    if request.user_prompt:
        prompt = request.user_prompt
    elif request.topic:
        prompt = f"请为以下选题创作一篇{request.platform}内容：\n\n选题：{request.topic}"
        if request.direction:
            prompt += f"\n方向：{request.direction}"
    else:
        raise HTTPException(status_code=400, detail="Must provide topic or user_prompt")

    # TODO: resolve taste_context_ids to actual taste profiles
    taste_context = ""

    async def event_stream():
        try:
            async for chunk in generator.generate_stream(
                user_prompt=prompt,
                platform=request.platform,
                taste_context=taste_context,
                system_prompt=request.system_prompt,
            ):
                # SSE format: data: JSON\n\n
                import json
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Stream generation error: %s", e)
            import json
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/rewrite")
async def rewrite_section(request: RewriteRequest) -> dict:
    """Rewrite a specific section of content based on instruction."""
    generator = _get_generator()

    try:
        rewritten = await generator.rewrite_section(
            original=request.original_text,
            instruction=request.instruction,
        )
        return {"rewritten": rewritten}
    except Exception as e:
        logger.error("Rewrite error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adjust-style")
async def adjust_style(request: AdjustStyleRequest) -> dict:
    """Regenerate content with adjusted style parameters."""
    generator = _get_generator()

    # For adjust-style, we need the current content.
    # In a real implementation, we'd fetch it from DB using content_id.
    # For now, return an error if no content context is available.
    # The frontend should send the content in a future iteration.
    try:
        # TODO: fetch content from DB by content_id
        # For now, use a placeholder
        result = await generator.adjust_style(
            content="",  # Would come from DB
            style_params=request.style_params.model_dump(),
        )
        return {"content": result}
    except Exception as e:
        logger.error("Adjust style error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def creative_chat(request: ChatRequest) -> dict:
    """Process a creative chat message in the workspace context."""
    generator = _get_generator()

    try:
        result = await generator.creative_chat(
            message=request.message,
            editor_content=request.editor_content or "",
            platform=request.platform,
        )
        return result
    except Exception as e:
        logger.error("Creative chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Variant Generation Endpoints ──


@router.post("/variants", response_model=VariantResponse)
async def generate_variants(request: VariantRequest) -> VariantResponse:
    """Generate 2-3 different content approaches for a topic.

    Each variant includes an angle, opening hook, outline, and tone descriptor.
    The user picks their favorite, then calls /expand-variant to get full content.
    """
    vg = _get_variant_generator()

    # TODO: resolve taste_context_ids to actual taste profiles
    taste_context = ""

    try:
        variants = await vg.generate_variants(
            topic=request.topic,
            direction=request.direction,
            platform=request.platform,
            taste_context=taste_context,
            num_variants=request.num_variants,
        )
    except Exception as e:
        logger.error("Variant generation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return VariantResponse(
        topic=request.topic,
        platform=request.platform,
        variants=variants,
    )


@router.post("/expand-variant")
async def expand_variant(request: ExpandVariantRequest) -> StreamingResponse:
    """Expand a chosen variant into full content. Returns Server-Sent Events."""
    vg = _get_variant_generator()

    # TODO: resolve taste_context_ids to actual taste profiles
    taste_context = ""

    async def event_stream():
        try:
            async for chunk in vg.expand_variant(
                topic=request.topic,
                angle=request.angle,
                hook=request.hook,
                outline=request.outline,
                tone=request.tone,
                platform=request.platform,
                taste_context=taste_context,
            ):
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Variant expansion error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
