"""WeChat platform tool — wraps existing wechat.py logic."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

from tastecraft.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Import the real WeChat tool from the old codebase
_WechatTool = None
_ContentType = None
_PublishContent = None


def _ensure_old_tools_importable() -> None:
    """Add the project src/ to sys.path so old tools are importable."""
    global _WechatTool, _ContentType, _PublishContent
    if _WechatTool is not None:
        return

    src_dir = Path(__file__).resolve().parents[3]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    try:
        from tools.platform.wechat import WechatTool
        from tools.platform.base import ContentType, PublishContent

        _WechatTool = WechatTool()
        _ContentType = ContentType
        _PublishContent = PublishContent
    except ImportError as e:
        logger.warning("Cannot import old WeChat tool: %s", e)


class PublishWechatTool(BaseTool):
    """
    Publish a content draft to WeChat Official Account (微信公众号).

    Supports two methods:
    - API method (primary): Fast, requires AppID + AppSecret
    - Browser method: Uses CDP for cases not covered by API

    Prerequisites:
    - AppID and AppSecret configured in config or environment
    - WeChat Official Account with publishing permissions
    """

    name = "publish_wechat"
    description = (
        "Publish a content draft to WeChat Official Account (微信公众号). "
        "Requires AppID and AppSecret configured. Supports article posting with "
        "HTML content. Returns publish result with article URL on success."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Article title (max 64 characters, WeChat limit)",
            },
            "body": {
                "type": "string",
                "description": "Article body (HTML or plain text)",
            },
            "author": {
                "type": "string",
                "description": "Author name (optional, defaults to account setting)",
            },
            "digest": {
                "type": "string",
                "description": "Article summary/digest (max 120 chars, auto-generated if empty)",
            },
            "cover_image": {
                "type": "string",
                "description": "Cover image URL or path",
            },
            "need_open_comment": {
                "type": "boolean",
                "description": "Whether to open comments (default: true)",
            },
        },
        "required": ["title", "body"],
    }

    def __init__(self, project_id: str = "") -> None:
        self._project_id = project_id

    async def execute(
        self,
        title: str,
        body: str,
        author: str = "",
        digest: str = "",
        cover_image: str = "",
        need_open_comment: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        _ensure_old_tools_importable()

        if _WechatTool is None:
            return ToolResult(
                success=False,
                error=(
                    "WeChat publish tool not available. "
                    "Ensure src/tools/platform/wechat.py exists and WECHAT_APP_ID/WECHAT_APP_SECRET are set."
                ),
            )

        if not self._check_rate_limit():
            return ToolResult(
                success=False,
                error="Rate limit exceeded. WeChat allows 1 push per day via API.",
            )

        html_body = self._to_html(body)

        content = _PublishContent(
            title=title[:64],
            body=html_body,
            content_type=_ContentType.ARTICLE,
            images=[],
            tags=[],
        )

        try:
            result = await asyncio.get_running_loop().run_in_executor(
                None, _WechatTool.publish, content,
            )
            if result.is_success():
                return ToolResult(
                    success=True,
                    data={
                        "platform": "wechat",
                        "media_id": result.data.get("media_id", ""),
                        "url": result.data.get("url", ""),
                        "status": result.status,
                    },
                    metadata={"tool": self.name},
                )
            return ToolResult(
                success=False,
                error=result.error or "Publish failed",
                data=result.data,
                metadata={"tool": self.name},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                metadata={"tool": self.name},
            )

    def _check_rate_limit(self) -> bool:
        # TODO: implement persistent rate limit tracking
        return True

    def _to_html(self, text: str) -> str:
        """Convert plain text to basic HTML for WeChat."""
        paragraphs = text.split("\n\n")
        html_parts = [
            f"<p>{p.replace(chr(10), '<br/>')}</p>"
            for p in paragraphs
            if p.strip()
        ]
        return (
            "<!DOCTYPE html><html><body>"
            + "".join(html_parts)
            + "</body></html>"
        )


class CollectWechatMetricsTool(BaseTool):
    """Collect post performance metrics from WeChat Official Account via datacube API."""

    name = "collect_wechat_metrics"
    description = (
        "Collect performance metrics for a WeChat Official Account article. "
        "Uses WeChat datacube API to fetch article summary stats. "
        "Returns views, reads, likes, comments, shares, and completion rate."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "article_id": {
                "type": "string",
                "description": "Article media ID from WeChat API",
            },
            "article_url": {
                "type": "string",
                "description": "Article URL (alternative to article_id)",
            },
        },
        "required": [],
    }

    async def execute(
        self, article_id: str = "", article_url: str = "", **kwargs: Any,
    ) -> ToolResult:
        if not article_id and not article_url:
            return ToolResult(
                success=False,
                error="Either article_id or article_url is required.",
            )

        try:
            metrics = await asyncio.get_running_loop().run_in_executor(
                None, self._fetch_metrics, article_id,
            )
            return ToolResult(
                success=True,
                data=metrics,
                metadata={"tool": self.name},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Metrics collection failed: {type(e).__name__}: {e}",
                data={
                    "views": 0, "reads": 0, "likes": 0,
                    "comments": 0, "shares": 0, "completion_rate": 0.0,
                },
                metadata={"tool": self.name},
            )

    def _fetch_metrics(self, article_id: str) -> dict[str, Any]:
        """Fetch article metrics via WeChat datacube API."""
        app_id = os.environ.get("WECHAT_APP_ID", "")
        app_secret = os.environ.get("WECHAT_APP_SECRET", "")

        if not app_id or not app_secret:
            return {
                "views": 0, "reads": 0, "likes": 0,
                "comments": 0, "shares": 0, "completion_rate": 0.0,
                "error": "WECHAT_APP_ID and WECHAT_APP_SECRET env vars required",
            }

        # Step 1: Get access token
        token_url = (
            f"https://api.weixin.qq.com/cgi-bin/token"
            f"?grant_type=client_credential&appid={app_id}&secret={app_secret}"
        )
        try:
            with urllib.request.urlopen(token_url, timeout=10) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
            access_token = token_data.get("access_token")
            if not access_token:
                return {
                    "views": 0, "reads": 0, "likes": 0,
                    "comments": 0, "shares": 0, "completion_rate": 0.0,
                    "error": f"Token error: {token_data.get('errmsg', 'unknown')}",
                }
        except Exception as e:
            return {
                "views": 0, "reads": 0, "likes": 0,
                "comments": 0, "shares": 0, "completion_rate": 0.0,
                "error": f"Token fetch failed: {e}",
            }

        # Step 2: Get article data stats via getarticlesummary
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y-%m-%d")
        begin_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        stats_url = (
            f"https://api.weixin.qq.com/datacube/getarticlesummary"
            f"?access_token={access_token}"
        )
        payload = json.dumps({
            "begin_date": begin_date,
            "end_date": end_date,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                stats_url, data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                stats_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {
                "views": 0, "reads": 0, "likes": 0,
                "comments": 0, "shares": 0, "completion_rate": 0.0,
                "error": f"Stats fetch failed: {e}",
            }

        # Aggregate metrics from response
        total_views = 0
        total_reads = 0
        total_likes = 0
        total_shares = 0

        for item in stats_data.get("list", []):
            total_views += item.get("int_page_read_user", 0)
            total_reads += item.get("int_page_read_count", 0)
            total_likes += item.get("like_user", 0)
            total_shares += item.get("share_user", 0)

        completion_rate = round(total_reads / total_views, 4) if total_views > 0 else 0.0

        return {
            "views": total_views,
            "reads": total_reads,
            "likes": total_likes,
            "comments": 0,  # datacube API doesn't provide comment counts directly
            "shares": total_shares,
            "completion_rate": completion_rate,
        }
