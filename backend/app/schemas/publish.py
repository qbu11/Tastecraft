"""Publish-related Pydantic schemas for the TasteCraft publishing pipeline."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Platform(str, Enum):
    WECHAT = "wechat"
    XIAOHONGSHU = "xiaohongshu"
    WEIBO = "weibo"


class PublishStatusEnum(str, Enum):
    QUEUED = "queued"
    PUBLISHING = "publishing"
    SUCCESS = "success"
    FAILED = "failed"


# ── WeChat Draft ──────────────────────────────────────────────────────────────


class WeChatDraftCreate(BaseModel):
    """Request body for creating a WeChat MP draft article."""

    title: str = Field(..., max_length=64, description="Article title (max 64 chars)")
    content_md: str = Field(..., description="Article body in Markdown")
    author: str = Field(default="", max_length=32, description="Author name shown on article")
    digest: str = Field(default="", max_length=120, description="Article summary / excerpt")
    thumb_media_id: str = Field(
        default="",
        description="Cover image media_id (from upload-image endpoint)",
    )


class WeChatDraftResponse(BaseModel):
    """Response after creating a WeChat MP draft."""

    media_id: str
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    manage_url: str = "https://mp.weixin.qq.com"


class WeChatDraftListItem(BaseModel):
    """Single item in the draft list."""

    media_id: str
    title: str
    digest: str = ""
    update_time: int = 0


class WeChatDraftList(BaseModel):
    """Paginated list of WeChat MP drafts."""

    items: list[WeChatDraftListItem]
    total_count: int
    item_count: int


# ── Image Upload ──────────────────────────────────────────────────────────────


class ImageUploadResponse(BaseModel):
    """Response after uploading an image to WeChat MP material library."""

    media_id: str
    url: str = ""


# ── Generic Publish ───────────────────────────────────────────────────────────


class PublishRequest(BaseModel):
    """Platform-agnostic publish request."""

    content_id: int = Field(..., description="ID of Content record to publish")
    platform: Platform = Field(..., description="Target platform")


class PublishStatus(BaseModel):
    """Current status of a publish operation."""

    status: PublishStatusEnum
    platform: Platform
    media_id: str = ""
    published_url: str = ""
    error: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── XHS Publish ──────────────────────────────────────────────────────────────


class XHSPublishRequest(BaseModel):
    """Request body for publishing a note to Xiaohongshu."""

    title: str = Field(..., max_length=20, description="Note title (max 20 chars)")
    content: str = Field(..., max_length=1000, description="Note body (max 1000 chars)")
    images: list[str] = Field(
        ..., min_length=1, max_length=18, description="Image file paths (1-18)"
    )
    tags: list[str] = Field(
        default_factory=list, max_length=10, description="Hashtags (max 10)"
    )


class XHSPublishResponse(BaseModel):
    """Response from an XHS publish or draft-save operation."""

    success: bool
    note_id: str | None = None
    url: str | None = None
    status: str | None = None
    error: str | None = None


# ── Session Management ───────────────────────────────────────────────────────


class SessionStatusResponse(BaseModel):
    """Health status of a single platform session."""

    user_id: str
    platform: str
    health: str  # active | expiring | expired | not_found | error
    last_verified: datetime | None = None
    expires_at: datetime | None = None
    error: str | None = None


class SessionListResponse(BaseModel):
    """All platform sessions for a user."""

    sessions: list[SessionStatusResponse]


class InitLoginResponse(BaseModel):
    """Response when initiating a login flow."""

    qr_url: str | None = None
    ws_url: str | None = None  # Placeholder for noVNC WebSocket URL (Phase 2)
    message: str


class LoginStatusResponse(BaseModel):
    """Current login status for a platform."""

    logged_in: bool
    platform: str
    message: str


# ── Weibo Publish ──────────────────────────────────────────────────────────


class WeiboPublishRequest(BaseModel):
    """Request body for publishing a post to Weibo."""

    content: str = Field(
        ..., max_length=140, description="Post text (max 140 chars for regular posts)"
    )
    images: list[str] = Field(
        default_factory=list, max_length=9, description="Image file paths (0-9)"
    )


class WeiboPublishResponse(BaseModel):
    """Response from a Weibo publish or draft-save operation."""

    success: bool
    post_id: str | None = None
    draft_id: str | None = None
    url: str | None = None
    status: str | None = None
    error: str | None = None
