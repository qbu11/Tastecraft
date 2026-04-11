"""Unit tests for SearchTrendingTool with union-search + RSS integration."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tastecraft.tools.search import (
    SearchTrendingTool,
    _run_script,
)


class TestRunScript:
    """Tests for the _run_script helper."""

    @patch("tastecraft.tools.search.subprocess.run")
    def test_parses_json_list(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"title": "AI Trends", "url": "https://example.com"}]),
            stderr="",
        )
        result = _run_script(["python", "test.py"])
        assert len(result) == 1
        assert result[0]["title"] == "AI Trends"

    @patch("tastecraft.tools.search.subprocess.run")
    def test_parses_json_dict_with_results(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"results": [{"title": "Topic 1"}, {"title": "Topic 2"}]}),
            stderr="",
        )
        result = _run_script(["python", "test.py"])
        assert len(result) == 2

    @patch("tastecraft.tools.search.subprocess.run")
    def test_returns_empty_on_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = _run_script(["python", "test.py"])
        assert result == []

    @patch("tastecraft.tools.search.subprocess.run")
    def test_returns_empty_on_timeout(self, mock_run: MagicMock) -> None:
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=30)
        result = _run_script(["python", "test.py"])
        assert result == []

    @patch("tastecraft.tools.search.subprocess.run")
    def test_extracts_json_from_noisy_stdout(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Some log line\n[{"title": "Real Result"}]\nMore noise',
            stderr="",
        )
        result = _run_script(["python", "test.py"])
        assert len(result) == 1
        assert result[0]["title"] == "Real Result"


class TestSearchTrendingTool:
    """Tests for the SearchTrendingTool class."""

    def test_schema_export(self) -> None:
        tool = SearchTrendingTool(project_id="test")
        schema = tool.to_anthropic_schema()
        assert schema["name"] == "search_trending"
        assert "query" in schema["input_schema"]["properties"]

    @pytest.mark.asyncio
    async def test_fallback_to_generated(self) -> None:
        """When all search sources fail, returns generated placeholders."""
        tool = SearchTrendingTool(project_id="test")
        with (
            patch.object(tool, "_search_union", return_value=[]),
            patch.object(tool, "_search_rss", return_value=[]),
            patch.object(tool, "_search_duckduckgo", return_value=[]),
        ):
            result = await tool.execute(query="AI创业", platform="all", limit=5)
            assert result.success is True
            topics = result.data["topics"]
            assert len(topics) > 0
            assert all(t["source"] == "generated" for t in topics)

    @pytest.mark.asyncio
    async def test_union_results_merged(self) -> None:
        """Union search and RSS results are merged and deduplicated."""
        tool = SearchTrendingTool(project_id="test")
        union_data = [
            {"topic": "AI Trend", "title": "AI Trend", "score": 8.0, "source": "union:google", "url": ""},
        ]
        rss_data = [
            {"topic": "AI Trend", "title": "AI Trend", "score": 6.5, "source": "rss:feed", "url": ""},
            {"topic": "New Topic", "title": "New Topic", "score": 6.5, "source": "rss:feed", "url": ""},
        ]
        with (
            patch.object(tool, "_search_union", return_value=union_data),
            patch.object(tool, "_search_rss", return_value=rss_data),
        ):
            result = await tool.execute(query="AI", platform="all", limit=10)
            topics = result.data["topics"]
            # Should be deduplicated: "AI Trend" appears once
            titles = [t["title"] for t in topics]
            assert titles.count("AI Trend") == 1
            assert "New Topic" in titles

    @pytest.mark.asyncio
    async def test_results_sorted_by_score(self) -> None:
        tool = SearchTrendingTool(project_id="test")
        mixed = [
            {"topic": "Low", "title": "Low", "score": 2.0, "source": "test", "url": ""},
            {"topic": "High", "title": "High", "score": 9.0, "source": "test", "url": ""},
            {"topic": "Mid", "title": "Mid", "score": 5.0, "source": "test", "url": ""},
        ]
        with (
            patch.object(tool, "_search_union", return_value=mixed),
            patch.object(tool, "_search_rss", return_value=[]),
        ):
            result = await tool.execute(query="test", limit=10)
            scores = [t["score"] for t in result.data["topics"]]
            assert scores == sorted(scores, reverse=True)

    def test_search_union_parses_items(self) -> None:
        tool = SearchTrendingTool(project_id="test")
        raw = [{"title": "Topic A", "href": "https://a.com", "snippet": "desc"}]
        with patch("tastecraft.tools.search._run_script", return_value=raw):
            with patch("tastecraft.tools.search._UNION_SEARCH_SCRIPT") as mock_path:
                mock_path.exists.return_value = True
                result = tool._search_union("AI", "all", 10)
                assert len(result) == 1
                assert result[0]["source"].startswith("union:")

    def test_search_rss_parses_items(self) -> None:
        tool = SearchTrendingTool(project_id="test")
        raw = [{"title": "RSS Article", "link": "https://b.com", "author": "Author1"}]
        with patch("tastecraft.tools.search._run_script", return_value=raw):
            with (
                patch("tastecraft.tools.search._RSS_SEARCH_SCRIPT") as mock_script,
                patch("tastecraft.tools.search._RSS_FEEDS_FILE_FAST") as mock_feeds,
            ):
                mock_script.exists.return_value = True
                mock_feeds.exists.return_value = True
                result = tool._search_rss("AI", 10)
                assert len(result) == 1
                assert result[0]["source"] == "rss:Author1"

    def test_deduplicate(self) -> None:
        topics = [
            {"title": "Same Topic", "score": 5},
            {"title": "same topic", "score": 3},
            {"title": "Different", "score": 4},
        ]
        result = SearchTrendingTool._deduplicate(topics)
        assert len(result) == 2
