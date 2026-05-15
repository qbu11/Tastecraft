"""WeChat Official Account publisher using wechatpy.

Flow: create draft -> push to user's MP draft box -> user confirms -> system publishes.

wechatpy handles access-token caching automatically (7200 s). All sync API calls
are wrapped with ``asyncio.to_thread`` so the publisher can be used from async
FastAPI handlers without blocking the event loop.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wechatpy import WeChatClient
from wechatpy.exceptions import WeChatClientException

from app.services.markdown_converter import markdown_to_wechat_html

logger = logging.getLogger(__name__)


class WeChatPublisher:
    """Thin async wrapper around :class:`wechatpy.WeChatClient`.

    Parameters
    ----------
    app_id:
        WeChat MP AppID.
    app_secret:
        WeChat MP AppSecret.
    """

    def __init__(self, app_id: str, app_secret: str) -> None:
        self.client = WeChatClient(app_id, app_secret)

    # ── Draft management ──────────────────────────────────────────────────

    async def create_draft(
        self,
        title: str,
        content_html: str,
        author: str = "",
        digest: str = "",
        thumb_media_id: str = "",
    ) -> str:
        """Create a draft article in the MP backend.

        Returns the ``media_id`` of the created draft.
        """
        article: dict[str, Any] = {
            "title": title,
            "content": content_html,
            "thumb_media_id": thumb_media_id,
            "author": author,
            "digest": digest[:120] if digest else "",
            "show_cover_pic": 0 if not thumb_media_id else 1,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
        }

        def _create() -> dict:
            return self.client.post(
                url="https://api.weixin.qq.com/cgi-bin/draft/add",
                data={"articles": [article]},
            )

        result = await asyncio.to_thread(_create)
        media_id: str = result.get("media_id", "")
        if not media_id:
            raise WeChatClientException(
                errcode=result.get("errcode", -1),
                errmsg=result.get("errmsg", "No media_id returned"),
            )
        logger.info("WeChat draft created: media_id=%s title=%s", media_id, title)
        return media_id

    async def publish_draft(self, media_id: str) -> dict:
        """Publish a draft (moves from draft to published).

        Returns the API response dict containing ``publish_id``.
        """

        def _publish() -> dict:
            return self.client.post(
                url="https://api.weixin.qq.com/cgi-bin/freepublish/submit",
                data={"media_id": media_id},
            )

        result = await asyncio.to_thread(_publish)
        logger.info("WeChat draft published: media_id=%s result=%s", media_id, result)
        return result

    async def get_draft_list(
        self, offset: int = 0, count: int = 20
    ) -> dict[str, Any]:
        """List drafts in the MP backend.

        Returns dict with ``item`` (list), ``total_count``, ``item_count``.
        """

        def _list() -> dict:
            return self.client.post(
                url="https://api.weixin.qq.com/cgi-bin/draft/batchget",
                data={"offset": offset, "count": min(count, 20), "no_content": 1},
            )

        result = await asyncio.to_thread(_list)
        return result

    async def delete_draft(self, media_id: str) -> bool:
        """Delete a draft. Returns ``True`` on success."""

        def _delete() -> dict:
            return self.client.post(
                url="https://api.weixin.qq.com/cgi-bin/draft/delete",
                data={"media_id": media_id},
            )

        result = await asyncio.to_thread(_delete)
        errcode = result.get("errcode", 0)
        if errcode and errcode != 0:
            logger.error("Delete draft failed: %s", result)
            return False
        logger.info("WeChat draft deleted: media_id=%s", media_id)
        return True

    # ── Image upload ──────────────────────────────────────────────────────

    async def upload_image(self, image_path: str) -> str:
        """Upload an image to the MP permanent material library.

        Returns the ``media_id`` of the uploaded image.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        def _upload() -> dict:
            with path.open("rb") as f:
                return self.client.material.add(media_type="image", media_file=f)

        result = await asyncio.to_thread(_upload)
        media_id: str = result.get("media_id", "")
        logger.info("Image uploaded: path=%s media_id=%s", image_path, media_id)
        return media_id

    # ── Markdown helper ───────────────────────────────────────────────────

    async def markdown_to_wechat_html(self, markdown: str) -> str:
        """Convert markdown content to WeChat-compatible HTML with inline styles."""
        return markdown_to_wechat_html(markdown)
