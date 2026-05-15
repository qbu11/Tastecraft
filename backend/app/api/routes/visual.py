"""Visual content API — carousel generation, preview, and style management."""

from __future__ import annotations

import base64
import hashlib
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.content import Content
from app.models.user import User
from app.schemas.visual import (
    CardStyleSchema,
    CarouselRequest,
    CarouselResponse,
    PreviewSlideRequest,
    SlideInfo,
    StyleListResponse,
    StylePreset,
)
from app.services.carousel_planner import CarouselPlanner
from app.services.visual_engine import CardStyle, PRESET_STYLES, VisualEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visual", tags=["visual"])

# Persist generated images here (simple local storage for MVP)
_OUTPUT_DIR = Path("backend/generated_images")
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_engine = VisualEngine()
_planner = CarouselPlanner()


def _schema_to_style(schema: CardStyleSchema | None) -> CardStyle:
    """Convert Pydantic schema to dataclass, or return default."""
    if schema is None:
        return PRESET_STYLES["dark_elegant"]
    return CardStyle(
        background_color=schema.background_color,
        accent_color=schema.accent_color,
        text_color=schema.text_color,
        font_name=schema.font_name,
        title_size=schema.title_size,
        body_size=schema.body_size,
        card_width=schema.card_width,
        card_height=schema.card_height,
        padding=schema.padding,
    )


def _style_to_schema(style: CardStyle) -> CardStyleSchema:
    """Convert dataclass back to Pydantic schema."""
    return CardStyleSchema(
        background_color=style.background_color,
        accent_color=style.accent_color,
        text_color=style.text_color,
        font_name=style.font_name,
        title_size=style.title_size,
        body_size=style.body_size,
        card_width=style.card_width,
        card_height=style.card_height,
        padding=style.padding,
    )


def _save_slide(png_bytes: bytes, prefix: str, index: int) -> str:
    """Save PNG bytes to disk and return a relative URL."""
    digest = hashlib.md5(png_bytes).hexdigest()[:8]
    filename = f"{prefix}_{index}_{digest}.png"
    path = _OUTPUT_DIR / filename
    path.write_bytes(png_bytes)
    return f"/generated_images/{filename}"


# ── Endpoints ──


@router.post("/generate-carousel", response_model=CarouselResponse)
async def generate_carousel(
    payload: CarouselRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CarouselResponse:
    """Generate a full carousel from a content record.

    1. Fetches the content body from the database.
    2. Uses AI to plan slide structure.
    3. Renders each slide as a PNG image.
    """
    result = await db.execute(
        select(Content).where(
            Content.id == payload.content_id,
            Content.user_id == current_user.id,
        )
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    body_text = content.body or ""
    if not body_text.strip():
        raise HTTPException(status_code=400, detail="Content body is empty")

    style = _schema_to_style(payload.style)

    # Plan carousel structure via AI
    plan = await _planner.plan_carousel(
        content=body_text,
        platform=content.platform,
        num_slides=max(payload.num_slides - 2, 1),  # minus cover + CTA
    )

    # Render images
    png_list = await _engine.generate_carousel(
        title=plan.cover_title,
        slides=plan.slides,
        style=style,
    )

    # Persist and build response
    prefix = f"carousel_{content.id}_{int(time.time())}"
    slides: list[SlideInfo] = []
    slide_texts = (
        [plan.cover_title]
        + [s.get("text", "") for s in plan.slides]
        + [plan.cta_text]
    )

    for idx, png_bytes in enumerate(png_list):
        url = _save_slide(png_bytes, prefix, idx)
        slides.append(
            SlideInfo(
                index=idx,
                image_url=url,
                text_content=slide_texts[idx] if idx < len(slide_texts) else "",
            )
        )

    return CarouselResponse(
        slides=slides,
        total_slides=len(slides),
        style_used=_style_to_schema(style),
    )


@router.post("/preview-slide")
async def preview_slide(
    payload: PreviewSlideRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Preview a single slide and return it as base64-encoded PNG."""
    style = _schema_to_style(payload.style)

    if payload.slide_type == "cover":
        png = await _engine.generate_cover(payload.text, payload.subtitle or "", style)
    elif payload.slide_type == "cta":
        png = await _engine.generate_cta_slide(payload.text, style)
    else:
        png = await _engine.generate_content_slide(
            text=payload.text, slide_number=1, style=style
        )

    encoded = base64.b64encode(png).decode("ascii")
    return {"image_base64": encoded, "format": "png"}


@router.get("/styles", response_model=StyleListResponse)
async def list_styles() -> StyleListResponse:
    """List available preset card styles."""
    presets: list[StylePreset] = []

    labels = {
        "dark_elegant": ("深色高级", "深蓝黑底 + 陶土色点缀，质感大气"),
        "warm_cream": ("暖色温馨", "奶油底 + 暖棕点缀，亲切自然"),
        "ocean_blue": ("蓝色科技", "深蓝底 + 冰蓝点缀，科技感十足"),
        "forest_green": ("绿色自然", "深绿底 + 嫩绿点缀，清新环保"),
    }

    for name, style in PRESET_STYLES.items():
        label, desc = labels.get(name, (name, ""))
        presets.append(
            StylePreset(
                name=name,
                label=label,
                description=desc,
                style=_style_to_schema(style),
            )
        )

    return StyleListResponse(styles=presets)


@router.post("/upload")
async def upload_image(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload a user image for use in cards (backgrounds, overlays, logos)."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted")

    max_size = 10 * 1024 * 1024  # 10 MB
    data = await file.read()
    if len(data) > max_size:
        raise HTTPException(status_code=400, detail="Image exceeds 10 MB limit")

    digest = hashlib.md5(data).hexdigest()[:12]
    ext = Path(file.filename or "image.png").suffix or ".png"
    filename = f"upload_{current_user.id}_{digest}{ext}"
    dest = _OUTPUT_DIR / filename
    dest.write_bytes(data)

    return {
        "filename": filename,
        "url": f"/generated_images/{filename}",
        "size_bytes": len(data),
    }
