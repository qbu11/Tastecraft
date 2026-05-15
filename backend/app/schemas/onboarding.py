"""Onboarding schemas — request/response models for the conversational onboarding flow."""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Request Models ──────────────────────────────────────────────────────────


class OnboardingStart(BaseModel):
    """Start an onboarding session."""

    project_name: str | None = Field(None, description="Optional project name to associate")


class OnboardingMessage(BaseModel):
    """User message during onboarding conversation."""

    session_id: str
    message: str = Field(..., min_length=1, max_length=5000)


class ContentImportRequest(BaseModel):
    """Import user's existing content for style analysis.

    v2: If profile_url is provided, auto-import all recent posts from the profile.
    Otherwise, fall back to individual URL analysis.
    """

    session_id: str
    urls: list[str] = Field(default_factory=list, max_length=20)
    profile_url: str | None = Field(None, description="User profile URL for auto-import (v2)")
    platform: str | None = Field(None, description="Platform hint when using profile_url")


class CompetitorAddRequest(BaseModel):
    """Add competitor accounts for async analysis."""

    session_id: str
    urls: list[str] = Field(..., min_length=1, max_length=10)
    notes: str | None = None


class OnboardingComplete(BaseModel):
    """Finalize onboarding and build taste vault."""

    session_id: str


# ── Response Models ─────────────────────────────────────────────────────────


class AIResponse(BaseModel):
    """AI response in onboarding conversation."""

    message: str
    current_step: str
    step_index: int
    total_steps: int = 5
    quick_replies: list[str] = Field(default_factory=list)
    show_import_ui: bool = False
    show_competitor_ui: bool = False
    is_complete: bool = False
    generated_content: str | None = None


class OnboardingStatus(BaseModel):
    """Current onboarding progress."""

    session_id: str
    current_step: str
    step_index: int
    total_steps: int = 5
    completion_percent: int
    imported_content_count: int = 0
    competitors_added: int = 0
    is_complete: bool = False


class StyleAnalysis(BaseModel):
    """Result of analyzing imported content for style patterns."""

    sentence_avg_length: float
    paragraph_avg_length: float
    tone: str
    vocabulary_level: str
    structure_preference: str
    topic_distribution: dict[str, float] = Field(default_factory=dict)
    signature_phrases: list[str] = Field(default_factory=list)
    summary: str


class OnboardingSessionResponse(BaseModel):
    """Response when starting an onboarding session."""

    session_id: str
    first_message: str
    current_step: str
    step_index: int = 0
    total_steps: int = 5
    quick_replies: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportResult(BaseModel):
    """Result of auto-importing content from a user profile (v2)."""

    success: bool
    post_count: int = 0
    style_analysis: StyleAnalysis | None = None
    style_features: list[str] = Field(default_factory=list)
    error: str | None = None
