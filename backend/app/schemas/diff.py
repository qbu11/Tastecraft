from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EditType(StrEnum):
    TITLE_CHANGE = "title_change"
    TONE_SHIFT = "tone_shift"
    SHORTENING = "shortening"
    EXPANSION = "expansion"
    RESTRUCTURE = "restructure"
    VOCABULARY = "vocabulary"
    DELETION = "deletion"
    STYLE_TWEAK = "style_tweak"


class EditCapture(BaseModel):
    """Request body for capturing an edit."""

    original: str
    modified: str
    platform: str
    content_line_id: int | None = None


class EditClassification(BaseModel):
    """Classification result for a single edit."""

    edit_type: EditType
    details: str = ""
    word_count_delta: int = 0
    similarity_ratio: float = 0.0


class TastePreferenceResponse(BaseModel):
    """Response for a single taste preference."""

    id: int
    dimension: str
    rule: str
    confidence: float = Field(ge=0.0, le=1.0)
    platform: str | None
    edit_count: int
    confirmed: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TasteSummary(BaseModel):
    """Complete taste summary for a user."""

    preferences: list[TastePreferenceResponse]
    total_edits: int
    taste_score: float = Field(ge=0.0, le=100.0)
    platforms: list[str]
    dimensions_covered: int


class CaptureEditResponse(BaseModel):
    """Response after capturing an edit."""

    edit_id: int
    classification: EditClassification
    new_preferences_extracted: int = 0
    total_edits: int = 0


# ── v2: Conflict Detection & Resolution ────────────────────────────────────


class PreferenceConflict(BaseModel):
    """A detected conflict between two taste preferences."""

    id: str = Field(description="Unique conflict ID")
    preference_a_id: int
    preference_b_id: int
    preference_a_rule: str
    preference_b_rule: str
    preference_a_platform: str | None = None
    preference_b_platform: str | None = None
    dimension: str
    context: str = Field(default="", description="AI-generated explanation of the conflict")
    suggested_resolution: str = Field(
        default="keep_second",
        description="Suggested resolution: keep_first | keep_second | context_split",
    )


class ConflictResolution(BaseModel):
    """Request to resolve a detected conflict."""

    conflict_id: str
    preference_a_id: int
    preference_b_id: int
    resolution: str = Field(
        description="Resolution choice: keep_first | keep_second | context_split"
    )
    context_note: str | None = Field(
        None,
        description="Optional note, e.g. platform context for context_split",
    )
