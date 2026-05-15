"""Publishing API routes — platform-agnostic interface with WeChat MP + XHS support.

Endpoints
---------
POST /api/v1/publish/wechat/draft         — Create draft on WeChat MP
POST /api/v1/publish/wechat/publish/{id}   — Publish a draft
GET  /api/v1/publish/wechat/drafts         — List drafts
POST /api/v1/publish/wechat/upload-image   — Upload image
DELETE /api/v1/publish/wechat/{media_id}   — Delete draft
POST /api/v1/publish/xhs/draft             — Save to XHS draft box
POST /api/v1/publish/xhs/publish           — Publish directly to XHS
GET  /api/v1/publish/xhs/session-status    — Check XHS login status
POST /api/v1/publish/xhs/init-login        — Start XHS login flow
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.publish import (
    ImageUploadResponse,
    InitLoginResponse,
    LoginStatusResponse,
    PublishStatus,
    PublishStatusEnum,
    Platform,
    WeChatDraftCreate,
    WeChatDraftList,
    WeChatDraftListItem,
    WeChatDraftResponse,
    WeiboPublishRequest,
    WeiboPublishResponse,
    XHSPublishRequest,
    XHSPublishResponse,
)
from app.tools.platform.session_manager import SessionManager
from app.tools.platform.wechat import WeChatPublisher
from app.tools.platform.weibo import WeiboPublisher
from app.tools.platform.xiaohongshu import XHSPublisher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/publish", tags=["publish"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_wechat_publisher() -> WeChatPublisher:
    """Instantiate a :class:`WeChatPublisher` from application settings."""
    app_id = getattr(settings, "wechat_app_id", None)
    app_secret = getattr(settings, "wechat_app_secret", None)
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=503,
            detail="WeChat MP credentials not configured (WECHAT_APP_ID / WECHAT_APP_SECRET)",
        )
    return WeChatPublisher(app_id=app_id, app_secret=app_secret)


# ── WeChat Draft CRUD ─────────────────────────────────────────────────────────


@router.post("/wechat/draft", response_model=WeChatDraftResponse, status_code=201)
async def create_wechat_draft(
    payload: WeChatDraftCreate,
    current_user: User = Depends(get_current_user),
) -> WeChatDraftResponse:
    """Create a draft article in the WeChat MP backend.

    The article is converted from Markdown to WeChat-compatible HTML
    (inline styles, no external CSS).
    """
    publisher = _get_wechat_publisher()

    content_html = await publisher.markdown_to_wechat_html(payload.content_md)

    try:
        media_id = await publisher.create_draft(
            title=payload.title,
            content_html=content_html,
            author=payload.author,
            digest=payload.digest,
            thumb_media_id=payload.thumb_media_id,
        )
    except Exception as exc:
        logger.exception("Failed to create WeChat draft")
        raise HTTPException(status_code=502, detail=f"WeChat API error: {exc}") from exc

    return WeChatDraftResponse(
        media_id=media_id,
        title=payload.title,
        created_at=datetime.now(timezone.utc),
    )


@router.post("/wechat/publish/{media_id}", response_model=PublishStatus)
async def publish_wechat_draft(
    media_id: str,
    current_user: User = Depends(get_current_user),
) -> PublishStatus:
    """Publish a draft (moves it from draft box to published articles)."""
    publisher = _get_wechat_publisher()

    try:
        result = await publisher.publish_draft(media_id)
    except Exception as exc:
        logger.exception("Failed to publish WeChat draft %s", media_id)
        return PublishStatus(
            status=PublishStatusEnum.FAILED,
            platform=Platform.WECHAT,
            media_id=media_id,
            error=str(exc),
        )

    return PublishStatus(
        status=PublishStatusEnum.SUCCESS,
        platform=Platform.WECHAT,
        media_id=media_id,
        published_url="https://mp.weixin.qq.com",
    )


@router.get("/wechat/drafts", response_model=WeChatDraftList)
async def list_wechat_drafts(
    offset: int = 0,
    count: int = 20,
    current_user: User = Depends(get_current_user),
) -> WeChatDraftList:
    """List drafts stored in the WeChat MP backend."""
    publisher = _get_wechat_publisher()

    try:
        result = await publisher.get_draft_list(offset=offset, count=count)
    except Exception as exc:
        logger.exception("Failed to list WeChat drafts")
        raise HTTPException(status_code=502, detail=f"WeChat API error: {exc}") from exc

    items: list[WeChatDraftListItem] = []
    for raw_item in result.get("item", []):
        news = raw_item.get("content", {}).get("news_item", [{}])
        first_article = news[0] if news else {}
        items.append(
            WeChatDraftListItem(
                media_id=raw_item.get("media_id", ""),
                title=first_article.get("title", ""),
                digest=first_article.get("digest", ""),
                update_time=raw_item.get("update_time", 0),
            )
        )

    return WeChatDraftList(
        items=items,
        total_count=result.get("total_count", 0),
        item_count=result.get("item_count", 0),
    )


@router.post("/wechat/upload-image", response_model=ImageUploadResponse)
async def upload_wechat_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> ImageUploadResponse:
    """Upload an image to the WeChat MP permanent material library."""
    import tempfile
    from pathlib import Path

    publisher = _get_wechat_publisher()

    # Write upload to a temp file so wechatpy can read it
    suffix = Path(file.filename or "image.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        media_id = await publisher.upload_image(tmp_path)
    except Exception as exc:
        logger.exception("Failed to upload image to WeChat")
        raise HTTPException(status_code=502, detail=f"WeChat API error: {exc}") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return ImageUploadResponse(media_id=media_id)


@router.delete("/wechat/{media_id}", status_code=204)
async def delete_wechat_draft(
    media_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a draft from the WeChat MP backend."""
    publisher = _get_wechat_publisher()

    ok = await publisher.delete_draft(media_id)
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to delete WeChat draft")


# ── XHS Helpers ──────────────────────────────────────────────────────────────

_session_manager = SessionManager()


async def _get_xhs_publisher(user_id: int) -> XHSPublisher:
    """Create an XHSPublisher with the user's profile directory."""
    profile_dir = await _session_manager.get_or_create_profile(str(user_id), "xiaohongshu")
    return XHSPublisher(profile_dir=profile_dir)


# ── XHS Endpoints ────────────────────────────────────────────────────────────


@router.post("/xhs/draft", response_model=XHSPublishResponse, status_code=201)
async def save_xhs_draft(
    payload: XHSPublishRequest,
    current_user: User = Depends(get_current_user),
) -> XHSPublishResponse:
    """Save a note to the XHS draft box (does not publish directly)."""
    publisher = await _get_xhs_publisher(current_user.id)

    try:
        result = await publisher.save_as_draft(
            title=payload.title,
            content=payload.content,
            images=payload.images,
            tags=payload.tags,
        )
    except Exception as exc:
        logger.exception("XHS save draft failed")
        return XHSPublishResponse(success=False, error=str(exc))
    finally:
        await publisher.close()

    return XHSPublishResponse(**result)


@router.post("/xhs/publish", response_model=XHSPublishResponse)
async def publish_xhs_note(
    payload: XHSPublishRequest,
    current_user: User = Depends(get_current_user),
) -> XHSPublishResponse:
    """Publish a note directly to Xiaohongshu."""
    publisher = await _get_xhs_publisher(current_user.id)

    try:
        result = await publisher.publish_note(
            title=payload.title,
            content=payload.content,
            images=payload.images,
            tags=payload.tags,
        )
    except Exception as exc:
        logger.exception("XHS publish failed")
        return XHSPublishResponse(success=False, error=str(exc))
    finally:
        await publisher.close()

    return XHSPublishResponse(**result)


@router.get("/xhs/session-status", response_model=LoginStatusResponse)
async def xhs_session_status(
    current_user: User = Depends(get_current_user),
) -> LoginStatusResponse:
    """Check whether the XHS login session is still valid."""
    publisher = await _get_xhs_publisher(current_user.id)

    try:
        logged_in = await publisher.check_login_status()
        if logged_in:
            await _session_manager.update_session_verified(str(current_user.id), "xiaohongshu")
    except Exception as exc:
        logger.warning("XHS session check failed: %s", exc)
        return LoginStatusResponse(
            logged_in=False, platform="xiaohongshu", message=f"Check failed: {exc}"
        )
    finally:
        await publisher.close()

    return LoginStatusResponse(
        logged_in=logged_in,
        platform="xiaohongshu",
        message="Session is valid" if logged_in else "Session expired — please re-login",
    )


@router.post("/xhs/init-login", response_model=InitLoginResponse)
async def init_xhs_login(
    current_user: User = Depends(get_current_user),
) -> InitLoginResponse:
    """Start the XHS login flow.

    For MVP this returns a QR code URL that the user can scan.
    Phase 2 will integrate Guacamole/noVNC for remote browser streaming.
    """
    publisher = await _get_xhs_publisher(current_user.id)

    try:
        qr_url = await publisher.get_login_qr_url()
    except Exception as exc:
        logger.exception("XHS init-login failed")
        return InitLoginResponse(
            message=f"Failed to start login: {exc}",
        )

    # NOTE: ws_url is a placeholder for Phase 2 noVNC integration
    return InitLoginResponse(
        qr_url=qr_url or None,
        ws_url=None,
        message="Scan the QR code with the XHS mobile app to login"
        if qr_url
        else "Could not extract QR code — try opening the browser manually",
    )


# ── Weibo Helpers ──────────────────────────────────────────────────────────


async def _get_weibo_publisher(user_id: int) -> WeiboPublisher:
    """Create a WeiboPublisher with the user's profile directory."""
    profile_dir = await _session_manager.get_or_create_profile(str(user_id), "weibo")
    return WeiboPublisher(profile_dir=profile_dir)


# ── Weibo Endpoints ────────────────────────────────────────────────────────


@router.post("/weibo/draft", response_model=WeiboPublishResponse, status_code=201)
async def save_weibo_draft(
    payload: WeiboPublishRequest,
    current_user: User = Depends(get_current_user),
) -> WeiboPublishResponse:
    """Save a post to the Weibo draft box (does not publish directly)."""
    publisher = await _get_weibo_publisher(current_user.id)

    try:
        result = await publisher.save_as_draft(
            content=payload.content,
            images=payload.images or None,
        )
    except Exception as exc:
        logger.exception("Weibo save draft failed")
        return WeiboPublishResponse(success=False, error=str(exc))
    finally:
        await publisher.close()

    return WeiboPublishResponse(**result)


@router.post("/weibo/publish", response_model=WeiboPublishResponse)
async def publish_weibo_post(
    payload: WeiboPublishRequest,
    current_user: User = Depends(get_current_user),
) -> WeiboPublishResponse:
    """Publish a post directly to Weibo."""
    publisher = await _get_weibo_publisher(current_user.id)

    try:
        result = await publisher.publish_post(
            content=payload.content,
            images=payload.images or None,
        )
    except Exception as exc:
        logger.exception("Weibo publish failed")
        return WeiboPublishResponse(success=False, error=str(exc))
    finally:
        await publisher.close()

    return WeiboPublishResponse(**result)


@router.get("/weibo/session-status", response_model=LoginStatusResponse)
async def weibo_session_status(
    current_user: User = Depends(get_current_user),
) -> LoginStatusResponse:
    """Check whether the Weibo login session is still valid."""
    publisher = await _get_weibo_publisher(current_user.id)

    try:
        logged_in = await publisher.check_login_status()
        if logged_in:
            await _session_manager.update_session_verified(str(current_user.id), "weibo")
    except Exception as exc:
        logger.warning("Weibo session check failed: %s", exc)
        return LoginStatusResponse(
            logged_in=False, platform="weibo", message=f"Check failed: {exc}"
        )
    finally:
        await publisher.close()

    return LoginStatusResponse(
        logged_in=logged_in,
        platform="weibo",
        message="Session is valid" if logged_in else "Session expired — please re-login",
    )


@router.post("/weibo/init-login", response_model=InitLoginResponse)
async def init_weibo_login(
    current_user: User = Depends(get_current_user),
) -> InitLoginResponse:
    """Start the Weibo login flow.

    Returns a QR code URL that the user can scan with the Weibo mobile app.
    """
    publisher = await _get_weibo_publisher(current_user.id)

    try:
        qr_url = await publisher.get_login_qr_url()
    except Exception as exc:
        logger.exception("Weibo init-login failed")
        return InitLoginResponse(
            message=f"Failed to start login: {exc}",
        )

    return InitLoginResponse(
        qr_url=qr_url or None,
        ws_url=None,
        message="Scan the QR code with the Weibo mobile app to login"
        if qr_url
        else "Could not extract QR code — try opening the browser manually",
    )
