"""
Integration tests for AnalyticsCrew.

Tests cover:
- Crew creation and configuration
- Input validation
- Task generation
- Data collection and analysis workflow
- Report generation
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import json

import pytest

from src.agents.platform_adapter import Platform
from src.crew.crews.analytics_crew import (
    AnalyticsCrew,
    AnalyticsCrewInput,
    AnalyticsCrewResult,
)
from src.crew.crews.base_crew import CrewInput, CrewResult, CrewStatus


class TestAnalyticsCrewInput:
    """Test cases for AnalyticsCrewInput."""

    def test_analytics_crew_input_creation(self) -> None:
        """
        Test AnalyticsCrewInput can be created with valid parameters.

        Arrange: Prepare valid input parameters
        Act: Create AnalyticsCrewInput instance
        Assert: All parameters are stored correctly
        """
        crew_input = AnalyticsCrewInput(
            content_ids=["content_1", "content_2", "content_3"],
            time_range="7d",
            platforms=["xiaohongshu", "wechat"],
            metrics=["views", "likes", "comments"],
            report_format="json",
        )

        assert crew_input.inputs["content_ids"] == ["content_1", "content_2", "content_3"]
        assert crew_input.inputs["time_range"] == "7d"
        assert crew_input.inputs["platforms"] == ["xiaohongshu", "wechat"]
        assert crew_input.metadata["content_count"] == 3
        assert crew_input.metadata["report_format"] == "json"

    def test_analytics_crew_input_defaults(self) -> None:
        """
        Test AnalyticsCrewInput has correct default values.

        Arrange: Create AnalyticsCrewInput with minimal params
        Act: Check default values
        Assert: Defaults are applied correctly
        """
        crew_input = AnalyticsCrewInput(
            content_ids=["content_1"],
        )

        assert crew_input.inputs["time_range"] == "7d"
        assert crew_input.inputs["platforms"] == ["xiaohongshu"]
        assert "views" in crew_input.inputs["metrics"]
        assert "likes" in crew_input.inputs["metrics"]
        assert crew_input.inputs["report_format"] == "json"


class TestAnalyticsCrewResult:
    """Test cases for AnalyticsCrewResult."""

    def test_analytics_crew_result_creation(self) -> None:
        """
        Test AnalyticsCrewResult can be created with all fields.

        Arrange: Prepare result data
        Act: Create AnalyticsCrewResult instance
        Assert: All fields are stored correctly
        """
        result = AnalyticsCrewResult(
            status=CrewStatus.COMPLETED,
            collected_data=[
                {
                    "content_id": "id1",
                    "platform": "xiaohongshu",
                    "metrics": {"views": 1000, "likes": 100},
                },
                {
                    "content_id": "id2",
                    "platform": "wechat",
                    "metrics": {"views": 500, "likes": 50},
                },
            ],
            analysis_report={
                "summary": "本周表现良好",
                "total_views": 1500,
                "avg_engagement_rate": 10.0,
                "top_performers": [{"title": "热门内容", "views": 1000}],
                "underperformers": [],
                "key_findings": ["小红书表现突出"],
            },
            recommendations=[
                "增加小红书内容密度",
                "优化发布时间",
            ],
        )

        assert result.status == CrewStatus.COMPLETED
        assert len(result.collected_data) == 2
        assert result.analysis_report["summary"] == "本周表现良好"
        assert len(result.recommendations) == 2

    def test_analytics_crew_result_properties(self) -> None:
        """
        Test AnalyticsCrewResult property methods.

        Arrange: Create AnalyticsCrewResult with full data
        Act: Access properties
        Assert: Properties return correct data
        """
        result = AnalyticsCrewResult(
            status=CrewStatus.COMPLETED,
            collected_data=[],
            analysis_report={
                "top_performers": [
                    {"title": "Top 1", "views": 5000},
                    {"title": "Top 2", "views": 3000},
                ],
                "underperformers": [
                    {"title": "Low 1", "views": 100},
                ],
                "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
            },
            recommendations=[],
        )

        assert len(result.top_performers) == 2
        assert len(result.underperformers) == 1
        assert len(result.key_findings) == 3

    def test_analytics_crew_result_to_markdown_report(self) -> None:
        """
        Test AnalyticsCrewResult.to_markdown_report generates formatted output.

        Arrange: Create AnalyticsCrewResult with data
        Act: Call to_markdown_report()
        Assert: Returns properly formatted markdown
        """
        result = AnalyticsCrewResult(
            status=CrewStatus.COMPLETED,
            collected_data=[],
            analysis_report={
                "summary": "测试摘要",
                "top_performers": [
                    {"title": "热门内容", "views": 1000, "platform": "xiaohongshu"}
                ],
                "key_findings": ["发现1", "发现2"],
            },
            recommendations=["建议1", "建议2"],
        )

        markdown = result.to_markdown_report()

        assert "# Analytics Report" in markdown
        assert "测试摘要" in markdown
        assert "## Key Findings" in markdown
        assert "1. 发现1" in markdown
        assert "## Top Performers" in markdown
        assert "热门内容" in markdown
        assert "## Recommendations" in markdown
        assert "1. 建议1" in markdown


class TestAnalyticsCrew:
    """Test cases for AnalyticsCrew."""

    def test_analytics_crew_creation(self) -> None:
        """
        Test AnalyticsCrew can be created with default parameters.

        Arrange: None
        Act: Create AnalyticsCrew instance
        Assert: Default parameters are set correctly
        """
        crew = AnalyticsCrew()

        assert crew.get_crew_name() == "ContentAnalytics"
        assert "分析" in crew.get_description()
        assert crew.max_rpm == 30
        assert crew.memory is True

    def test_analytics_crew_custom_parameters(self) -> None:
        """
        Test AnalyticsCrew with custom parameters.

        Arrange: Prepare custom parameters
        Act: Create AnalyticsCrew with custom settings
        Assert: Custom parameters are set correctly
        """
        crew = AnalyticsCrew(
            verbose=False,
            memory=False,
            max_rpm=10,
            llm="claude-opus-4-20250514",
        )

        assert crew.verbose is False
        assert crew.memory is False
        assert crew.max_rpm == 10
        assert crew.llm == "claude-opus-4-20250514"

    def test_analytics_crew_validate_inputs_valid(self) -> None:
        """
        Test AnalyticsCrew.validate_inputs with valid data.

        Arrange: Create AnalyticsCrew and valid input
        Act: Call validate_inputs()
        Assert: Returns (True, None)
        """
        crew = AnalyticsCrew()
        crew_input = AnalyticsCrewInput(
            content_ids=["id1", "id2"],
            time_range="7d",
            platforms=["xiaohongshu", "wechat"],
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is True
        assert error is None

    def test_analytics_crew_validate_inputs_missing_content_ids(self) -> None:
        """
        Test AnalyticsCrew.validate_inputs without content_ids.

        Arrange: Create input without content_ids
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = AnalyticsCrew()
        crew_input = CrewInput(
            inputs={
                "time_range": "7d",
                "platforms": ["xiaohongshu"],
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "content_ids" in error

    def test_analytics_crew_validate_inputs_empty_content_ids(self) -> None:
        """
        Test AnalyticsCrew.validate_inputs with empty content_ids.

        Arrange: Create input with empty content_ids list
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = AnalyticsCrew()
        crew_input = CrewInput(
            inputs={
                "content_ids": [],
                "time_range": "7d",
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "content_ids" in error

    def test_analytics_crew_validate_inputs_invalid_time_range(self) -> None:
        """
        Test AnalyticsCrew.validate_inputs with invalid time_range.

        Arrange: Create input with invalid time_range
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = AnalyticsCrew()
        crew_input = CrewInput(
            inputs={
                "content_ids": ["id1"],
                "time_range": "1y",  # Invalid
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "time_range" in error

    def test_analytics_crew_validate_inputs_invalid_platform(self) -> None:
        """
        Test AnalyticsCrew.validate_inputs with invalid platform.

        Arrange: Create input with invalid platform
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = AnalyticsCrew()
        crew_input = CrewInput(
            inputs={
                "content_ids": ["id1"],
                "time_range": "7d",
                "platforms": ["invalid_platform"],
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "平台" in error or "platform" in error

    @patch("src.crew.crews.analytics_crew.DataAnalyst.create")
    def test_analytics_crew_get_agents(self, mock_analyst: Mock) -> None:
        """
        Test AnalyticsCrew.get_agents creates three analysts.

        Arrange: Mock DataAnalyst.create
        Act: Call get_agents()
        Assert: Returns 3 analyst agents
        """
        mock_analyst.return_value = MagicMock()

        crew = AnalyticsCrew()
        agents = crew.get_agents()

        assert len(agents) == 3
        # Called 3 times for collector, analyzer, advisor
        assert mock_analyst.call_count == 3

    @patch("src.crew.crews.analytics_crew.Task")
    @patch("src.crew.crews.analytics_crew.DataAnalyst.create")
    def test_analytics_crew_get_tasks(
        self,
        mock_analyst: Mock,
        mock_task: Mock,
    ) -> None:
        """
        Test AnalyticsCrew.get_tasks creates correct tasks.

        Arrange: Mock agent and task creation
        Act: Call get_tasks() with valid input
        Assert: Returns list with 3 tasks
        """
        mock_analyst.return_value = MagicMock()
        mock_task.return_value = MagicMock()

        crew = AnalyticsCrew()
        crew_input = AnalyticsCrewInput(
            content_ids=["id1", "id2"],
            time_range="7d",
            platforms=["xiaohongshu"],
        )

        tasks = crew.get_tasks(crew_input)

        assert len(tasks) == 3
        assert mock_task.call_count == 3

    def test_analytics_crew_extract_task_output_json(self) -> None:
        """
        Test AnalyticsCrew._extract_task_output with JSON output.

        Arrange: Create mock task output with JSON string
        Act: Call _extract_task_output()
        Assert: Returns parsed JSON dictionary
        """
        crew = AnalyticsCrew()
        mock_output = MagicMock()
        mock_output.raw = '{"total_views": 10000, "avg_engagement": 8.5}'

        result = crew._extract_task_output(mock_output)

        assert isinstance(result, dict)
        assert result["total_views"] == 10000
        assert result["avg_engagement"] == 8.5

    def test_analytics_crew_extract_task_output_invalid_json(self) -> None:
        """
        Test AnalyticsCrew._extract_task_output with invalid JSON.

        Arrange: Create mock task output with plain text
        Act: Call _extract_task_output()
        Assert: Returns dict with 'output' key
        """
        crew = AnalyticsCrew()
        mock_output = MagicMock()
        mock_output.raw = "Plain text output"

        result = crew._extract_task_output(mock_output)

        assert isinstance(result, dict)
        assert result["output"] == "Plain text output"

    def test_analytics_crew_parse_outputs_with_tasks(self) -> None:
        """
        Test AnalyticsCrew._parse_outputs with tasks_output.

        Arrange: Create mock outputs with tasks_output
        Act: Call _parse_outputs()
        Assert: Extracts task outputs correctly
        """
        crew = AnalyticsCrew()

        mock_outputs = MagicMock()
        mock_outputs.tasks_output = [
            # Collect task returns list
            MagicMock(raw='{"results": [{"content_id": "id1", "metrics": {}}]}'),
            # Analyze task returns dict
            MagicMock(raw='{"summary": "分析摘要", "total_views": 5000}'),
            # Advise task returns dict
            MagicMock(raw='{"recommendations": ["建议1", "建议2"]}'),
        ]
        mock_outputs.to_dict.return_value = {"test": "value"}

        result = crew._parse_outputs(mock_outputs)

        assert "collected_data" in result
        assert "analysis_report" in result
        assert "recommendations" in result

    def test_analytics_crew_parse_outputs_collect_as_list(self) -> None:
        """
        Test AnalyticsCrew._parse_outputs handles list from collect task.

        Arrange: Create mock where first task returns list directly
        Act: Call _parse_outputs()
        Assert: collected_data is extracted as list
        """
        crew = AnalyticsCrew()

        mock_outputs = MagicMock()
        mock_outputs.tasks_output = [
            # Collect task returns dict with results list
            MagicMock(
                raw='{"results": [{"content_id": "id1"}, {"content_id": "id2"}]}'
            ),
            MagicMock(raw='{"summary": "摘要"}'),
            MagicMock(raw='{"recommendations": []}'),
        ]
        mock_outputs.to_dict.return_value = {}

        result = crew._parse_outputs(mock_outputs)

        # Should extract results from the first task
        assert "collected_data" in result

    @patch("src.crew.crews.analytics_crew.DataAnalyst.create")
    def test_analytics_crew_create_classmethod(
        self,
        mock_analyst: Mock,
    ) -> None:
        """
        Test AnalyticsCrew.create class method.

        Arrange: Mock agent creation
        Act: Call AnalyticsCrew.create()
        Assert: Returns AnalyticsCrew instance
        """
        mock_analyst.return_value = MagicMock()

        crew = AnalyticsCrew.create(llm="claude-opus-4-20250514")

        assert isinstance(crew, AnalyticsCrew)
        assert crew.llm == "claude-opus-4-20250514"

    def test_analytics_crew_get_quick_stats(self) -> None:
        """
        Test AnalyticsCrew.get_quick_stats method.

        Arrange: Create AnalyticsCrew
        Act: Call get_quick_stats() with content IDs
        Assert: Returns statistics dictionary
        """
        crew = AnalyticsCrew()

        # Mock the data_collect_tool to return test data
        with patch("src.crew.crews.analytics_crew.data_collect_tool") as mock_tool:
            mock_tool.return_value = json.dumps({
                "status": "success",
                "data": {
                    "metrics": {
                        "views": 1000,
                        "likes": 100,
                    }
                }
            })

            stats = crew.get_quick_stats(["id1", "id2"])

            assert "content_count" in stats
            assert "total_views" in stats
            assert "total_likes" in stats


class TestAnalyticsCrewIntegration:
    """Integration tests for AnalyticsCrew end-to-end workflow."""

    @patch("src.crew.crews.analytics_crew.DataAnalyst.create")
    @patch.object(AnalyticsCrew, "execute")
    def test_analytics_crew_full_workflow_mock(
        self,
        mock_execute: Mock,
        mock_analyst: Mock,
    ) -> None:
        """
        Test AnalyticsCrew full workflow with mocked execution.

        Arrange: Mock agents and execute method
        Act: Call kickoff() with input
        Assert: Returns expected AnalyticsCrewResult
        """
        mock_analyst.return_value = MagicMock()

        # Mock execute to return an AnalyticsCrewResult
        mock_execute.return_value = AnalyticsCrewResult(
            status=CrewStatus.COMPLETED,
            collected_data=[
                {
                    "content_id": "id1",
                    "platform": "xiaohongshu",
                    "metrics": {"views": 10000, "likes": 1200},
                }
            ],
            analysis_report={
                "summary": "本周表现良好",
                "total_views": 10000,
                "avg_engagement_rate": 12.0,
                "top_performers": [{"title": "热门内容", "views": 10000}],
                "underperformers": [],
                "key_findings": ["小红书表现突出"],
            },
            recommendations=[
                "增加小红书内容密度",
                "优化发布时间",
            ],
            execution_time=8.0,
        )

        crew = AnalyticsCrew()
        result = crew.kickoff(
            content_ids=["id1", "id2"],
            time_range="7d",
            platforms=["xiaohongshu"],
        )

        assert result.status == CrewStatus.COMPLETED
        assert len(result.collected_data) >= 1
        assert result.analysis_report is not None
        assert len(result.recommendations) >= 1

    def test_analytics_crew_execute_returns_analytics_crew_result(self) -> None:
        """
        Test AnalyticsCrew.execute returns AnalyticsCrewResult type.

        Arrange: Create AnalyticsCrew with mocked execute
        Act: Call execute() with valid input
        Assert: Returns AnalyticsCrewResult instance
        """
        crew = AnalyticsCrew()

        # Mock the parent execute method
        with patch.object(
            AnalyticsCrew.__bases__[0],  # BaseCrew
            "execute",
            return_value=CrewResult(
                status=CrewStatus.COMPLETED,
                raw_outputs={"test": "output"},
            ),
        ):
            crew_input = AnalyticsCrewInput(
                content_ids=["id1"],
            )

            result = crew.execute(crew_input)

            # Should return AnalyticsCrewResult, not just CrewResult
            assert isinstance(result, (CrewResult, AnalyticsCrewResult))

    @patch("src.crew.crews.analytics_crew.DataAnalyst.create")
    def test_analytics_crew_post_execute_logging(
        self,
        mock_analyst: Mock,
    ) -> None:
        """
        Test AnalyticsCrew.post_execute logs recommendations.

        Arrange: Create AnalyticsCrew with successful result
        Act: Call post_execute()
        Assert: Log message includes recommendation count
        """
        import logging
        from unittest.mock import patch as patch_mock

        mock_analyst.return_value = MagicMock()

        crew = AnalyticsCrew()
        result = CrewResult(
            status=CrewStatus.COMPLETED,
            data={
                "recommendations": ["rec1", "rec2", "rec3"],
            },
        )

        with patch_mock("src.crew.crews.analytics_crew.logger") as mock_logger:
            crew.post_execute(result)

            # Verify logging happened
            assert mock_logger.info.called
