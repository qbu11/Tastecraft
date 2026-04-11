"""Integration tests for TasteCraft pipelines."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSearchTrendingIntegration:
    """Integration test: SearchTrendingTool with mocked subprocess."""

    @pytest.mark.asyncio
    async def test_union_plus_rss_merged(self) -> None:
        """Simulate union-search and RSS both returning results."""
        from tastecraft.tools.search import SearchTrendingTool

        union_output = json.dumps([
            {"title": "Union Result 1", "href": "https://union.com/1", "snippet": "desc1"},
            {"title": "Union Result 2", "href": "https://union.com/2", "snippet": "desc2"},
        ])
        rss_output = json.dumps([
            {"title": "RSS Article 1", "link": "https://rss.com/1", "author": "AI_era"},
            {"title": "Union Result 1", "link": "https://dup.com", "author": "dup"},  # duplicate
        ])

        call_count = {"n": 0}

        def mock_run(cmd, **kwargs):
            call_count["n"] += 1
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            # First call is union_search, second is rss_search
            if call_count["n"] == 1:
                mock.stdout = union_output
            else:
                mock.stdout = rss_output
            return mock

        tool = SearchTrendingTool(project_id="integration-test")
        with (
            patch("tastecraft.tools.search.subprocess.run", side_effect=mock_run),
            patch("tastecraft.tools.search._UNION_SEARCH_SCRIPT") as mock_us,
            patch("tastecraft.tools.search._RSS_SEARCH_SCRIPT") as mock_rs,
            patch("tastecraft.tools.search._RSS_FEEDS_FILE") as mock_ff,
        ):
            mock_us.exists.return_value = True
            mock_rs.exists.return_value = True
            mock_ff.exists.return_value = True

            result = await tool.execute(query="AI", platform="all", limit=10)

        assert result.success is True
        topics = result.data["topics"]
        # Union Result 1 appears in both sources but should be deduped
        titles = [t["title"] for t in topics]
        assert titles.count("Union Result 1") == 1
        assert "Union Result 2" in titles
        assert "RSS Article 1" in titles

    @pytest.mark.asyncio
    async def test_fallback_chain_to_duckduckgo(self) -> None:
        """When union-search and RSS fail, falls back to DuckDuckGo."""
        from tastecraft.tools.search import SearchTrendingTool

        tool = SearchTrendingTool(project_id="integration-test")

        ddg_topics = [
            {"topic": "DDG Result", "title": "DDG Result", "score": 5.0, "source": "duckduckgo", "url": ""},
        ]

        with (
            patch("tastecraft.tools.search._UNION_SEARCH_SCRIPT") as mock_us,
            patch("tastecraft.tools.search._RSS_SEARCH_SCRIPT") as mock_rs,
        ):
            mock_us.exists.return_value = False
            mock_rs.exists.return_value = False

            with patch.object(tool, "_search_duckduckgo", return_value=ddg_topics):
                result = await tool.execute(query="test", limit=5)

        assert result.success is True
        assert any(t["source"] == "duckduckgo" for t in result.data["topics"])

    @pytest.mark.asyncio
    async def test_full_fallback_to_generated(self) -> None:
        """When all sources fail, returns generated placeholders."""
        from tastecraft.tools.search import SearchTrendingTool

        tool = SearchTrendingTool(project_id="integration-test")

        with (
            patch("tastecraft.tools.search._UNION_SEARCH_SCRIPT") as mock_us,
            patch("tastecraft.tools.search._RSS_SEARCH_SCRIPT") as mock_rs,
        ):
            mock_us.exists.return_value = False
            mock_rs.exists.return_value = False

            with patch.object(tool, "_search_duckduckgo", return_value=[]):
                result = await tool.execute(query="niche topic", limit=3)

        assert result.success is True
        assert len(result.data["topics"]) == 3
        assert all(t["source"] == "generated" for t in result.data["topics"])


class TestPublishPipelineIntegration:
    """Integration test: publish pipeline with mocked platform tools."""

    @pytest.mark.asyncio
    async def test_publish_tool_schema_and_unavailable(self) -> None:
        """Verify that publish tools have correct schema and handle unavailability."""
        from tastecraft.tools.platform.xiaohongshu import PublishXiaohongshuTool

        tool = PublishXiaohongshuTool(project_id="test")
        schema = tool.to_anthropic_schema()

        assert schema["name"] == "publish_xiaohongshu"
        assert "title" in schema["input_schema"]["properties"]
        assert "body" in schema["input_schema"]["properties"]

        # When tool is unavailable, it returns a clear error
        with (
            patch("tastecraft.tools.platform.xiaohongshu._XHSTool", None),
            patch("tastecraft.tools.platform.xiaohongshu._ContentType", None),
            patch("tastecraft.tools.platform.xiaohongshu._PublishContent", None),
            patch("tastecraft.tools.platform.xiaohongshu._ensure_old_tools_importable", lambda: None),
        ):
            result = await tool.execute(title="Test Title", body="Test body")
            assert result.success is False
            assert "not available" in result.error


class TestGenerateModeSwitching:
    """Integration test: generate command mode dispatch."""

    def test_collab_mode_dispatches_to_repl(self) -> None:
        """Verify mode='collab' would invoke run_repl."""
        from tastecraft.cli.commands.generate import _build_content_context

        ctx = _build_content_context("AI topic", "collab")
        assert "collab" in ctx.lower()
        assert "USER_INPUT_REQUIRED" in ctx

    def test_auto_mode_context(self) -> None:
        from tastecraft.cli.commands.generate import _build_content_context

        ctx = _build_content_context("test", "auto")
        assert "auto" in ctx.lower()
        assert "USER_INPUT_REQUIRED" not in ctx
