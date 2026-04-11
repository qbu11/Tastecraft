"""Unit tests for platform publish tools (fixed imports) and metrics collection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tastecraft.tools.platform.xiaohongshu import (
    CollectXiaohongshuMetricsTool,
    PublishXiaohongshuTool,
)
from tastecraft.tools.platform.wechat import (
    CollectWechatMetricsTool,
    PublishWechatTool,
)


class TestPublishXiaohongshuTool:
    def test_instantiation(self) -> None:
        tool = PublishXiaohongshuTool(project_id="test")
        assert tool.name == "publish_xiaohongshu"

    def test_schema_export(self) -> None:
        tool = PublishXiaohongshuTool(project_id="test")
        schema = tool.to_anthropic_schema()
        assert schema["name"] == "publish_xiaohongshu"
        assert "title" in schema["input_schema"]["properties"]
        assert "body" in schema["input_schema"]["properties"]

    @pytest.mark.asyncio
    async def test_returns_error_when_tool_unavailable(self) -> None:
        """When old XHS tool can't be imported, returns clear error."""
        tool = PublishXiaohongshuTool(project_id="test")
        with (
            patch("tastecraft.tools.platform.xiaohongshu._XHSTool", None),
            patch("tastecraft.tools.platform.xiaohongshu._ContentType", None),
            patch("tastecraft.tools.platform.xiaohongshu._PublishContent", None),
            patch("tastecraft.tools.platform.xiaohongshu._ensure_old_tools_importable", lambda: None),
        ):
            result = await tool.execute(title="Test", body="Test body")
            assert result.success is False
            assert "not available" in result.error

    @pytest.mark.asyncio
    async def test_execute_delegates_to_old_tool(self) -> None:
        """When old tool is available, it delegates publish."""
        tool = PublishXiaohongshuTool(project_id="test")
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = {"post_id": "abc", "url": "https://xhs.com/abc"}
        mock_result.status = "published"

        mock_old_tool = MagicMock()
        mock_old_tool.publish.return_value = mock_result

        mock_ct = MagicMock()
        mock_ct.IMAGE_TEXT = "image_text"
        mock_ct.TEXT = "text"
        mock_pc = MagicMock()

        with (
            patch("tastecraft.tools.platform.xiaohongshu._XHSTool", mock_old_tool),
            patch("tastecraft.tools.platform.xiaohongshu._ContentType", mock_ct),
            patch("tastecraft.tools.platform.xiaohongshu._PublishContent", mock_pc),
            patch("tastecraft.tools.platform.xiaohongshu._ensure_old_tools_importable", lambda: None),
        ):
            result = await tool.execute(title="Test", body="Body text")
            assert result.success is True
            assert result.data["platform"] == "xiaohongshu"


class TestPublishWechatTool:
    def test_instantiation(self) -> None:
        tool = PublishWechatTool(project_id="test")
        assert tool.name == "publish_wechat"

    def test_schema_export(self) -> None:
        tool = PublishWechatTool(project_id="test")
        schema = tool.to_anthropic_schema()
        assert schema["name"] == "publish_wechat"
        assert "title" in schema["input_schema"]["properties"]

    @pytest.mark.asyncio
    async def test_returns_error_when_tool_unavailable(self) -> None:
        tool = PublishWechatTool(project_id="test")
        with (
            patch("tastecraft.tools.platform.wechat._WechatTool", None),
            patch("tastecraft.tools.platform.wechat._ensure_old_tools_importable", lambda: None),
        ):
            result = await tool.execute(title="Test", body="Test body")
            assert result.success is False
            assert "not available" in result.error

    def test_to_html(self) -> None:
        tool = PublishWechatTool(project_id="test")
        html = tool._to_html("Para 1\n\nPara 2")
        assert "<p>Para 1</p>" in html
        assert "<p>Para 2</p>" in html
        assert "<!DOCTYPE html>" in html


class TestCollectXiaohongshuMetricsTool:
    def test_instantiation(self) -> None:
        tool = CollectXiaohongshuMetricsTool()
        assert tool.name == "collect_xhs_metrics"

    @pytest.mark.asyncio
    async def test_requires_url_or_id(self) -> None:
        tool = CollectXiaohongshuMetricsTool()
        result = await tool.execute()
        assert result.success is False
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handles_scrape_failure(self) -> None:
        tool = CollectXiaohongshuMetricsTool()
        with patch.object(
            tool, "_scrape_metrics",
            side_effect=RuntimeError("CDP connection refused"),
        ):
            result = await tool.execute(post_url="https://www.xiaohongshu.com/explore/123")
            assert result.success is False
            assert "failed" in result.error.lower()

    def test_extract_number_chinese_wan(self) -> None:
        tool = CollectXiaohongshuMetricsTool()
        mock_el = MagicMock()
        mock_el.inner_text.return_value = "1.2万"
        mock_page = MagicMock()
        mock_page.query_selector.return_value = mock_el
        assert tool._extract_number(mock_page, "sel") == 12000

    def test_extract_number_plain(self) -> None:
        tool = CollectXiaohongshuMetricsTool()
        mock_el = MagicMock()
        mock_el.inner_text.return_value = "456"
        mock_page = MagicMock()
        mock_page.query_selector.return_value = mock_el
        assert tool._extract_number(mock_page, "sel") == 456

    def test_extract_number_no_element(self) -> None:
        tool = CollectXiaohongshuMetricsTool()
        mock_page = MagicMock()
        mock_page.query_selector.return_value = None
        assert tool._extract_number(mock_page, "sel") == 0


class TestCollectWechatMetricsTool:
    def test_instantiation(self) -> None:
        tool = CollectWechatMetricsTool()
        assert tool.name == "collect_wechat_metrics"

    @pytest.mark.asyncio
    async def test_requires_id_or_url(self) -> None:
        tool = CollectWechatMetricsTool()
        result = await tool.execute()
        assert result.success is False
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handles_missing_credentials(self) -> None:
        tool = CollectWechatMetricsTool()
        with patch.dict("os.environ", {"WECHAT_APP_ID": "", "WECHAT_APP_SECRET": ""}, clear=False):
            result = await tool.execute(article_id="media_123")
            assert result.data is not None
            assert "error" in result.data or result.data.get("views", -1) == 0
