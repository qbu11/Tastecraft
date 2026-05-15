"""Schemas for multi-variant content generation."""

from pydantic import BaseModel, Field


class VariantRequest(BaseModel):
    """Request body for generating multiple content variants."""

    topic: str = Field(..., min_length=1, description="The topic to generate variants for")
    direction: str = Field(default="", description="Optional creative direction or angle hint")
    platform: str = Field(default="xiaohongshu", description="Target platform")
    num_variants: int = Field(default=3, ge=2, le=3, description="Number of variants (2-3)")
    taste_context_ids: list[str] = Field(
        default_factory=list, description="Optional taste vault context IDs"
    )


class ContentVariant(BaseModel):
    """A single content variant/approach."""

    id: str = Field(..., description="Unique variant ID")
    angle: str = Field(..., description="The creative angle or approach title")
    hook: str = Field(..., description="The opening hook (first 1-2 lines)")
    outline: list[str] = Field(..., description="Content outline as bullet points")
    tone: str = Field(..., description="Estimated tone descriptor (e.g. '专业理性', '轻松口语')")


class VariantResponse(BaseModel):
    """Response containing generated variants."""

    topic: str
    platform: str
    variants: list[ContentVariant]


class ExpandVariantRequest(BaseModel):
    """Request body for expanding a chosen variant into full content."""

    variant_id: str = Field(..., description="ID of the variant to expand")
    topic: str = Field(..., description="The original topic")
    angle: str = Field(..., description="The chosen variant's angle")
    hook: str = Field(..., description="The chosen variant's hook")
    outline: list[str] = Field(..., description="The chosen variant's outline")
    tone: str = Field(..., description="The chosen variant's tone")
    platform: str = Field(default="xiaohongshu", description="Target platform")
    taste_context_ids: list[str] = Field(
        default_factory=list, description="Optional taste vault context IDs"
    )
