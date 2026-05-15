"""Version schemas — request/response models for version history API."""

from datetime import datetime

from pydantic import BaseModel, Field


class ContentVersionResponse(BaseModel):
    """Response model for a single content version."""

    id: int
    content_id: int
    version_number: int
    title: str
    body: str
    platform: str
    created_by: str = Field(
        ...,
        description="Who created this version: ai_generated | user_edited | style_adjusted | variant_expanded",
    )
    created_at: datetime

    model_config = {"from_attributes": True}


class DiffLineResponse(BaseModel):
    """A single line in a diff."""

    type: str = Field(..., description="addition | deletion | unchanged")
    content: str
    line_number_old: int | None = None
    line_number_new: int | None = None


class VersionDiffResponse(BaseModel):
    """Diff between two content versions."""

    version_from: int
    version_to: int
    title_changed: bool
    body_lines: list[DiffLineResponse]
    additions: int
    deletions: int


class RollbackRequest(BaseModel):
    """Request to rollback content to a specific version."""

    # No body needed — version number is in the URL path
    pass


class PartialRollbackRequest(BaseModel):
    """Request to partially rollback content using sections from an older version."""

    from_version: int = Field(..., description="Version number to take sections from")
    sections: list[str] = Field(
        ...,
        description="Section names to take from the source version (e.g., 'opening', 'body', 'closing', 'title')",
    )
