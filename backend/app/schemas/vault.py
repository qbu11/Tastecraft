"""Vault schemas — data models for Taste Vault health and context preview."""

from datetime import datetime

from pydantic import BaseModel, Field


class VaultHealth(BaseModel):
    """Vault completeness and freshness status."""

    completeness_pct: float = Field(..., ge=0, le=100, description="Vault completeness percentage")
    last_updated: datetime | None = Field(None, description="Last vault document update time")
    document_count: int = Field(0, ge=0, description="Total documents in vault")
    stale_documents: list[str] = Field(
        default_factory=list, description="Documents not updated in 14+ days"
    )


class ContextPreview(BaseModel):
    """Preview of context that would be injected into a generation call."""

    assembled_context: str = Field(..., description="The full assembled context string")
    token_count: int = Field(..., ge=0, description="Estimated token count of context")
    documents_used: list[str] = Field(
        default_factory=list, description="Vault documents included in context"
    )


class ContextPreviewRequest(BaseModel):
    """Request body for context preview endpoint."""

    platform: str = Field("xiaohongshu", description="Target platform")
    topic: str | None = Field(None, description="Content topic for context selection")
    content_type: str = Field("post", description="Content type (post, article, thread)")
