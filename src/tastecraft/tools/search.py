"""Search tools for trending topics and competitor analysis."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from tastecraft.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Paths to union-search skill scripts
_SKILL_DIR = Path.home() / ".claude" / "skills" / "union-search-skill"
_UNION_SEARCH_SCRIPT = _SKILL_DIR / "scripts" / "union_search" / "union_search.py"
_RSS_SEARCH_SCRIPT = _SKILL_DIR / "scripts" / "rss_search" / "rss_search.py"
_RSS_FEEDS_FILE = _SKILL_DIR / "scripts" / "rss_search" / "rss_feeds.txt"

# Platform mapping for union-search --platforms flag
_PLATFORM_MAP: dict[str, list[str]] = {
    "xiaohongshu": ["xiaohongshu", "bilibili", "weibo"],
    "wechat": ["zhihu", "baidu"],
    "all": ["google", "duckduckgo", "xiaohongshu", "zhihu", "weibo", "bilibili"],
}


def _run_script(cmd: list[str], timeout: int = 30) -> list[dict[str, Any]]:
    """Run a search script and parse JSON output."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning("Script failed (exit %d): %s", result.returncode, result.stderr[:200])
            return []

        stdout = result.stdout.strip()
        if not stdout:
            return []

        data: Any = None
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            for i, ch in enumerate(stdout):
                if ch in "[{":
                    try:
                        data, _ = decoder.raw_decode(stdout[i:])
                        break
                    except json.JSONDecodeError:
                        continue

        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "results" in data:
                return data["results"] if isinstance(data["results"], list) else []
            items: list[dict[str, Any]] = []
            for val in data.values():
                if isinstance(val, dict) and "results" in val:
                    items.extend(val["results"])
                elif isinstance(val, list):
                    items.extend(val)
            return items
        return []
    except subprocess.TimeoutExpired:
        logger.warning("Script timed out after %ds", timeout)
        return []
    except FileNotFoundError:
        logger.warning("Script not found: %s", cmd[0] if cmd else "?")
        return []
    except Exception as e:
        logger.warning("Script execution error: %s", e)
        return []


class SearchTrendingTool(BaseTool):
    """
    Search for trending topics using union-search + RSS + DuckDuckGo fallback.

    Search chain (results are merged and deduplicated):
    1. Union Search — multi-platform search via union_search.py
    2. RSS feeds — curated AI/tech RSS sources via rss_search.py
    3. DuckDuckGo — instant answers API fallback
    4. Generated placeholders — last resort
    """

    name = "search_trending"
    description = (
        "Search for trending topics in the content domain. "
        "Returns a list of trending topics with relevance scores, "
        "so the agent can pick the best one for content generation. "
        "Pass 'query' to specify the search domain or topic area."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query or domain to find trending topics in",
            },
            "platform": {
                "type": "string",
                "enum": ["xiaohongshu", "wechat", "all"],
                "description": "Platform to search on (default: all)",
            },
            "limit": {
                "type": "integer",
                "description": "Max number of topics to return (default: 10)",
            },
        },
        "required": ["query"],
    }

    def __init__(self, project_id: str = "") -> None:
        self._project_id = project_id

    async def execute(
        self,
        query: str,
        platform: str = "all",
        limit: int = 10,
    ) -> ToolResult:
        topics = await self._search(query, platform, limit)
        return ToolResult(
            success=True,
            data={"topics": topics, "query": query, "platform": platform},
            metadata={"tool": self.name, "count": len(topics)},
        )

    async def _search(self, query: str, platform: str, limit: int) -> list[dict[str, Any]]:
        """Multi-source search: union-search -> RSS -> DuckDuckGo -> fallback."""
        import asyncio

        all_topics: list[dict[str, Any]] = []

        loop = asyncio.get_running_loop()
        union_fut = loop.run_in_executor(None, self._search_union, query, platform, limit)
        rss_fut = loop.run_in_executor(None, self._search_rss, query, limit)

        union_results, rss_results = await asyncio.gather(
            union_fut, rss_fut, return_exceptions=True,
        )

        if isinstance(union_results, list):
            all_topics.extend(union_results)
        if isinstance(rss_results, list):
            all_topics.extend(rss_results)

        if not all_topics:
            ddg_results = await self._search_duckduckgo(query, limit)
            all_topics.extend(ddg_results)

        if not all_topics:
            all_topics = self._generate_fallback(query, limit)

        all_topics = self._deduplicate(all_topics)
        all_topics.sort(key=lambda t: t.get("score", 0), reverse=True)
        return all_topics[:limit]

    def _search_union(self, query: str, platform: str, limit: int) -> list[dict[str, Any]]:
        """Search via union_search.py subprocess."""
        if not _UNION_SEARCH_SCRIPT.exists():
            logger.info("union_search.py not found at %s", _UNION_SEARCH_SCRIPT)
            return []

        cmd = [sys.executable, str(_UNION_SEARCH_SCRIPT), query, "--json", "--limit", str(limit)]
        platforms = _PLATFORM_MAP.get(platform, _PLATFORM_MAP["all"])
        cmd.extend(["--platforms"] + platforms)

        raw_items = _run_script(cmd, timeout=45)
        topics: list[dict[str, Any]] = []
        for item in raw_items:
            title = str(item.get("title", item.get("name", ""))).strip()
            if not title:
                continue
            topics.append({
                "topic": title[:120],
                "title": title[:80],
                "score": float(item.get("score", 7.0)),
                "source": f"union:{item.get('platform', item.get('source', 'unknown'))}",
                "url": str(item.get("href", item.get("url", item.get("link", "")))),
                "summary": str(item.get("snippet", item.get("description", "")))[:200],
            })
        return topics

    def _search_rss(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Search curated RSS feeds via rss_search.py subprocess."""
        if not _RSS_SEARCH_SCRIPT.exists():
            logger.info("rss_search.py not found at %s", _RSS_SEARCH_SCRIPT)
            return []

        cmd = [sys.executable, str(_RSS_SEARCH_SCRIPT), query, "--json", "--limit", str(limit)]
        if _RSS_FEEDS_FILE.exists():
            cmd.extend(["--feeds", str(_RSS_FEEDS_FILE)])

        raw_items = _run_script(cmd, timeout=60)
        topics: list[dict[str, Any]] = []
        for item in raw_items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            topics.append({
                "topic": title[:120],
                "title": title[:80],
                "score": 6.5,
                "source": f"rss:{item.get('author', item.get('feed_title', 'feed'))}",
                "url": str(item.get("link", item.get("weixin_link", ""))),
                "summary": str(item.get("summary", ""))[:200],
                "published": str(item.get("published", "")),
            })
        return topics

    async def _search_duckduckgo(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Fallback: DuckDuckGo instant answers API."""
        import httpx

        topics: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": f"{query} trending 2026", "format": "json", "no_html": 1},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in (data.get("RelatedTopics") or [])[:limit]:
                        if isinstance(item, dict) and "Text" in item:
                            topics.append({
                                "topic": item["Text"][:120],
                                "title": item["Text"][:80],
                                "score": 5.0,
                                "source": "duckduckgo",
                                "url": item.get("FirstURL", ""),
                            })
        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", e)
        return topics

    @staticmethod
    def _generate_fallback(query: str, limit: int) -> list[dict[str, Any]]:
        """Last resort: generate topic suggestions from query."""
        return [
            {"topic": f"{query} latest trends and insights", "title": f"{query} latest trends", "score": 3.0, "source": "generated"},
            {"topic": f"How {query} is changing in 2026", "title": f"How {query} is changing", "score": 2.5, "source": "generated"},
            {"topic": f"Common mistakes in {query}", "title": f"Common mistakes in {query}", "score": 2.0, "source": "generated"},
        ][:limit]

    @staticmethod
    def _deduplicate(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate topics by normalized title."""
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for t in topics:
            key = t.get("title", "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(t)
        return result


class SearchCompetitorTool(BaseTool):
    """
    Analyze competitor content in the user's domain.

    Searches for top-performing content from competitor accounts
    and extracts patterns (title structures, content length, engagement strategies).
    """

    name = "search_competitor"
    description = (
        "Analyze competitor content in the given domain. "
        "Returns top-performing content with extracted patterns "
        "(title structures, content formats, engagement strategies)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Domain/niche to analyze competitors in",
            },
            "platform": {
                "type": "string",
                "enum": ["xiaohongshu", "wechat"],
                "description": "Platform to search",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default: 5)",
            },
        },
        "required": ["domain"],
    }

    async def execute(
        self,
        domain: str,
        platform: str = "xiaohongshu",
        limit: int = 5,
    ) -> ToolResult:
        # Placeholder: in production uses platform-specific search APIs
        return ToolResult(
            success=True,
            data={
                "competitors": [],
                "patterns": {
                    "title_formats": ["numbered_list", "how_to", "contrarian_take"],
                    "avg_engagement_rate": 0.035,
                    "common_hashtags": [],
                },
                "domain": domain,
                "platform": platform,
            },
            metadata={"tool": self.name},
        )


class ReadContentHistoryTool(BaseTool):
    """Read past content from the project for dedup and style reference."""

    name = "read_content_history"
    description = (
        "Read past content from this project. Use for deduplication "
        "(avoid repeating topics) and style reference (match established patterns)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max number of past content items (default: 10)",
            },
            "status": {
                "type": "string",
                "description": "Filter by status (draft, queued, published)",
            },
        },
        "required": [],
    }

    def __init__(self, project_id: str = "") -> None:
        self._project_id = project_id

    async def execute(
        self,
        limit: int = 10,
        status: str | None = None,
    ) -> ToolResult:
        from tastecraft.models.base import get_session
        from tastecraft.models.tables import Content
        from sqlalchemy import select

        session = await get_session()
        async with session:
            stmt = (
                select(Content)
                .where(Content.project_id == self._project_id)
                .order_by(Content.created_at.desc())
                .limit(limit)
            )
            if status:
                stmt = stmt.where(Content.status == status)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            items = [
                {
                    "id": r.id,
                    "title": r.title,
                    "body_preview": r.body[:200] if r.body else "",
                    "status": r.status,
                    "quality_score": r.quality_score,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]
            return ToolResult(
                success=True,
                data={"items": items, "count": len(items)},
                metadata={"tool": self.name},
            )
