"""Xiaohongshu platform tool — wraps existing xiaohongshu.py logic."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from tastecraft.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Import the real XHS tool from the old codebase (src/tools/platform/)
# The old code lives at C:\11Projects\Crew\src\tools\platform\xiaohongshu.py
_XHSTool = None
_ContentType = None
_PublishContent = None


def _ensure_old_tools_importable() -> None:
    """Add the project src/ to sys.path so old tools are importable."""
    global _XHSTool, _ContentType, _PublishContent
    if _XHSTool is not None:
        return

    # Find project root: tastecraft lives under src/tastecraft/,
    # old tools live under src/tools/platform/
    src_dir = Path(__file__).resolve().parents[3]  # src/tastecraft/tools/platform -> src/
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    try:
        from tools.platform.xiaohongshu import XiaohongshuTool
        from tools.platform.base import ContentType, PublishContent

        _XHSTool = XiaohongshuTool()
        _ContentType = ContentType
        _PublishContent = PublishContent
    except ImportError as e:
        logger.warning("Cannot import old XHS tool: %s", e)


class PublishXiaohongshuTool(BaseTool):
    """
    Publish a content draft to Xiaohongshu (Little Red Book).

    Uses CDP (Chrome DevTools Protocol) via Playwright to drive a real browser,
    inheriting the user's login session for bot-detection avoidance.

    Prerequisites:
    - Chrome launched with: --remote-debugging-port=9222
    - User logged into xiaohongshu.com
    - CDP endpoint accessible at localhost:9222
    """

    name = "publish_xiaohongshu"
    description = (
        "Publish a content draft to Xiaohongshu (Little Red Book). "
        "Requires Chrome running with --remote-debugging-port=9222 and user logged in. "
        "Provide title (max 20 chars), body (max 1000 chars), optional image paths/URLs, "
        "and hashtags (max 10). Returns publish result with post URL on success."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Post title (max 20 characters, XHS limit)",
            },
            "body": {
                "type": "string",
                "description": "Post body text (max 1000 characters, XHS limit)",
            },
            "images": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Image paths or URLs (1-18 images supported)",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Hashtags without # prefix (max 10 tags)",
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
        images: list[str] | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        _ensure_old_tools_importable()

        if _XHSTool is None or _ContentType is None or _PublishContent is None:
            return ToolResult(
                success=False,
                error=(
                    "Xiaohongshu publish tool not available. "
                    "Ensure src/tools/platform/xiaohongshu.py exists and Playwright is installed."
                ),
            )

        if not self._check_rate_limit():
            return ToolResult(
                success=False,
                error="Rate limit exceeded. Wait before next post (min 60s interval, max 10/day).",
            )

        content = _PublishContent(
            title=title[:20],
            body=body[:1000],
            content_type=_ContentType.IMAGE_TEXT if images else _ContentType.TEXT,
            images=images or [],
            tags=tags or [],
        )

        try:
            result = await asyncio.get_running_loop().run_in_executor(
                None, _XHSTool.publish, content,
            )
            if result.is_success():
                return ToolResult(
                    success=True,
                    data={
                        "platform": "xiaohongshu",
                        "post_id": result.data.get("post_id", ""),
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
        # TODO: implement persistent rate limit tracking (file-based or DB)
        return True


class CollectXiaohongshuMetricsTool(BaseTool):
    """Collect post performance metrics from Xiaohongshu via CDP scraping."""

    name = "collect_xhs_metrics"
    description = (
        "Collect performance metrics for a Xiaohongshu post. "
        "Provide the post URL or post ID. Returns views, likes, comments, "
        "shares, saves, and engagement rate."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "post_url": {
                "type": "string",
                "description": "URL of the Xiaohongshu post",
            },
            "post_id": {
                "type": "string",
                "description": "Post ID (alternative to post_url)",
            },
        },
        "required": [],
    }

    async def execute(
        self, post_url: str = "", post_id: str = "", **kwargs: Any,
    ) -> ToolResult:
        if not post_url and not post_id:
            return ToolResult(
                success=False,
                error="Either post_url or post_id is required.",
            )

        url = post_url or f"https://www.xiaohongshu.com/explore/{post_id}"

        try:
            metrics = await asyncio.get_running_loop().run_in_executor(
                None, self._scrape_metrics, url,
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
                    "views": 0, "likes": 0, "comments": 0,
                    "shares": 0, "saves": 0, "engagement_rate": 0.0,
                },
                metadata={"tool": self.name},
            )

    def _scrape_metrics(self, url: str) -> dict[str, Any]:
        """Scrape XHS post metrics via Playwright CDP."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "views": 0, "likes": 0, "comments": 0,
                "shares": 0, "saves": 0, "engagement_rate": 0.0,
                "error": "Playwright not installed",
            }

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_over_cdp("http://localhost:9222")
            page = browser.contexts[0].new_page() if browser.contexts else browser.new_page()

            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)

            # Extract engagement metrics from the post page
            metrics = {
                "views": self._extract_number(page, '[class*="view"], [class*="read"]'),
                "likes": self._extract_number(page, '[class*="like-count"], [class*="like"] span'),
                "comments": self._extract_number(page, '[class*="comment-count"], [class*="chat"] span'),
                "shares": self._extract_number(page, '[class*="share-count"], [class*="share"] span'),
                "saves": self._extract_number(page, '[class*="collect-count"], [class*="collect"] span'),
            }

            total_engagement = metrics["likes"] + metrics["comments"] + metrics["shares"] + metrics["saves"]
            views = metrics["views"] or 1
            metrics["engagement_rate"] = round(total_engagement / views, 4) if views > 0 else 0.0

            page.close()
            return metrics
        finally:
            pw.stop()

    @staticmethod
    def _extract_number(page: Any, selector: str) -> int:
        """Extract a numeric value from a page element."""
        try:
            el = page.query_selector(selector)
            if el:
                text = el.inner_text().strip()
                # Handle Chinese number suffixes: 1.2万 -> 12000
                if "万" in text:
                    return int(float(text.replace("万", "")) * 10000)
                if "w" in text.lower():
                    return int(float(text.lower().replace("w", "")) * 10000)
                # Strip non-numeric chars
                import re
                nums = re.findall(r"[\d.]+", text)
                return int(float(nums[0])) if nums else 0
        except Exception:
            pass
        return 0
