from __future__ import annotations

from pydantic import BaseModel, Field


class CardStyleSchema(BaseModel):
    """Visual style configuration for carousel cards."""

    background_color: str = Field(
        default="#1a1a2e",
        description="Card background hex colour (dark blue-black default)",
    )
    accent_color: str = Field(
        default="#c2714f",
        description="Accent / highlight hex colour (terracotta default)",
    )
    text_color: str = Field(
        default="#ffffff",
        description="Primary text hex colour",
    )
    font_name: str = Field(
        default="NotoSansSC",
        description="Font family name (must exist in assets/fonts)",
    )
    title_size: int = Field(default=72, ge=24, le=120)
    body_size: int = Field(default=36, ge=16, le=72)
    card_width: int = Field(default=1080, description="XHS standard width")
    card_height: int = Field(default=1440, description="3:4 ratio height")
    padding: int = Field(default=80, ge=20, le=200)


# ── Request schemas ──


class CarouselRequest(BaseModel):
    """Request body for full carousel generation."""

    content_id: int = Field(..., description="ID of the content record to visualise")
    num_slides: int = Field(default=5, ge=2, le=9, description="Total slides including cover & CTA")
    style: CardStyleSchema | None = Field(
        default=None,
        description="Optional style override; uses defaults when omitted",
    )


class PreviewSlideRequest(BaseModel):
    """Request body for single-slide preview."""

    text: str = Field(..., min_length=1, max_length=500)
    subtitle: str | None = None
    slide_type: str = Field(
        default="content",
        pattern="^(cover|content|cta)$",
        description="Slide type: cover, content, or cta",
    )
    style: CardStyleSchema | None = None


class UploadImageRequest(BaseModel):
    """Metadata for user-uploaded images."""

    name: str = Field(..., min_length=1, max_length=128)
    usage: str = Field(
        default="background",
        pattern="^(background|overlay|logo)$",
    )


# ── Response schemas ──


class SlideInfo(BaseModel):
    """Info about a single generated slide."""

    index: int
    image_url: str
    text_content: str


class CarouselResponse(BaseModel):
    """Response for carousel generation."""

    slides: list[SlideInfo]
    total_slides: int
    style_used: CardStyleSchema


class StylePreset(BaseModel):
    """A named preset style."""

    name: str
    label: str
    description: str
    style: CardStyleSchema


class StyleListResponse(BaseModel):
    """Available preset styles."""

    styles: list[StylePreset]
