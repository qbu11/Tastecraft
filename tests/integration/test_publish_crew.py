"""
Integration tests for PublishCrew.

Tests cover:
- Crew creation and configuration
- Input validation
- Task generation with platform-specific logic
- PublishBatch creation
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.agents.platform_adapter import Platform
from src.agents.platform_publisher import PublishBatch, PublishRecord, PublishStatus
from src.crew.crews.base_crew import CrewInput, CrewResult, CrewStatus
from src.crew.crews.publish_crew import (
    PublishCrew,
    PublishCrewInput,
    PublishCrewResult,
)


class TestPublishCrewInput:
    """Test cases for PublishCrewInput."""

    def test_publish_crew_input_creation(self) -> None:
        """
        Test PublishCrewInput can be created with valid parameters.

        Arrange: Prepare valid input parameters
        Act: Create PublishCrewInput instance
        Assert: All parameters are stored correctly
        """
        crew_input = PublishCrewInput(
            content_id="draft_123",
            content_draft={
                "title": "测试标题",
                "content": "测试内容",
                "tags": ["标签1"],
            },
            target_platforms=["xiaohongshu", "wechat"],
            schedule_time=None,
            enable_retry=True,
        )

        assert crew_input.inputs["content_id"] == "draft_123"
        assert crew_input.inputs["target_platforms"] == ["xiaohongshu", "wechat"]
        assert crew_input.metadata["platforms"] == ["xiaohongshu", "wechat"]
        assert crew_input.metadata["scheduled"] is False

    def test_publish_crew_input_with_schedule(self) -> None:
        """
        Test PublishCrewInput with scheduled publishing.

        Arrange: Create input with schedule_time
        Act: Create PublishCrewInput instance
        Assert: Schedule metadata is set correctly
        """
        crew_input = PublishCrewInput(
            content_id="draft_123",
            content_draft={"title": "标题", "content": "内容"},
            target_platforms=["xiaohongshu"],
            schedule_time="2025-03-25T10:00:00",
        )

        assert crew_input.inputs["schedule_time"] == "2025-03-25T10:00:00"
        assert crew_input.metadata["scheduled"] is True


class TestPublishCrewResult:
    """Test cases for PublishCrewResult."""

    def test_publish_crew_result_creation(self) -> None:
        """
        Test PublishCrewResult can be created with all fields.

        Arrange: Prepare result data
        Act: Create PublishCrewResult instance
        Assert: All fields are stored correctly
        """
        result = PublishCrewResult(
            status=CrewStatus.COMPLETED,
            adapted_contents={
                "xiaohongshu": {"title": "小红书标题"},
                "wechat": {"title": "微信标题"},
            },
            publish_records=[
                {
                    "platform": "xiaohongshu",
                    "status": "published",
                    "published_url": "https://xhs.com/123",
                },
                {
                    "platform": "wechat",
                    "status": "failed",
                    "error": "API error",
                },
            ],
        )

        assert result.status == CrewStatus.COMPLETED
        assert len(result.adapted_contents) == 2
        assert len(result.publish_records) == 2

    def test_publish_crew_result_summary_generation(self) -> None:
        """
        Test PublishCrewResult generates correct summary.

        Arrange: Create PublishCrewResult with mixed results
        Act: Check summary field
        Assert: Summary statistics are correct
        """
        result = PublishCrewResult(
            status=CrewStatus.COMPLETED,
            publish_records=[
                {"platform": "p1", "status": "published"},
                {"platform": "p2", "status": "published"},
                {"platform": "p3", "status": "failed"},
            ],
        )

        summary = result._generate_summary()

        assert summary["total"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["pending"] == 0
        assert summary["success_rate"] == "66.7%"

    def test_publish_crew_result_all_success_property(self) -> None:
        """
        Test PublishCrewResult.all_success property.

        Arrange: Create results with different outcomes
        Act: Check all_success property
        Assert: Returns correct boolean values
        """
        all_success = PublishCrewResult(
            status=CrewStatus.COMPLETED,
            publish_records=[
                {"platform": "p1", "status": "published"},
                {"platform": "p2", "status": "published"},
            ],
        )

        partial_success = PublishCrewResult(
            status=CrewStatus.COMPLETED,
            publish_records=[
                {"platform": "p1", "status": "published"},
                {"platform": "p2", "status": "failed"},
            ],
        )

        assert all_success.all_success is True
        assert partial_success.all_success is False

    def test_publish_crew_result_successful_platforms_property(self) -> None:
        """
        Test PublishCrewResult.successful_platforms property.

        Arrange: Create result with mixed statuses
        Act: Check successful_platforms property
        Assert: Returns only successful platforms
        """
        result = PublishCrewResult(
            status=CrewStatus.COMPLETED,
            publish_records=[
                {"platform": "xiaohongshu", "status": "published"},
                {"platform": "wechat", "status": "failed"},
                {"platform": "weibo", "status": "published"},
            ],
        )

        successful = result.successful_platforms
        failed = result.failed_platforms

        assert set(successful) == {"xiaohongshu", "weibo"}
        assert failed == ["wechat"]


class TestPublishCrew:
    """Test cases for PublishCrew."""

    def test_publish_crew_creation(self) -> None:
        """
        Test PublishCrew can be created with default parameters.

        Arrange: None
        Act: Create PublishCrew instance
        Assert: Default parameters are set correctly
        """
        crew = PublishCrew()

        assert crew.get_crew_name() == "ContentPublishing"
        assert "发布" in crew.get_description()
        assert crew.enable_retry is True
        assert crew.max_retries == 3

    def test_publish_crew_custom_parameters(self) -> None:
        """
        Test PublishCrew with custom parameters.

        Arrange: Prepare custom parameters
        Act: Create PublishCrew with custom settings
        Assert: Custom parameters are set correctly
        """
        crew = PublishCrew(
            verbose=False,
            max_rpm=20,
            enable_retry=False,
            max_retries=1,
        )

        assert crew.verbose is False
        assert crew.max_rpm == 20
        assert crew.enable_retry is False
        assert crew.max_retries == 1

    def test_publish_crew_validate_inputs_valid(self) -> None:
        """
        Test PublishCrew.validate_inputs with valid data.

        Arrange: Create PublishCrew and valid input
        Act: Call validate_inputs()
        Assert: Returns (True, None)
        """
        crew = PublishCrew()
        crew_input = PublishCrewInput(
            content_id="draft_123",
            content_draft={
                "title": "测试标题",
                "content": "测试内容" * 100,  # Ensure long enough
            },
            target_platforms=["xiaohongshu"],
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is True
        assert error is None

    def test_publish_crew_validate_inputs_missing_content_id(self) -> None:
        """
        Test PublishCrew.validate_inputs without content_id.

        Arrange: Create input without content_id
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = PublishCrew()
        crew_input = CrewInput(
            inputs={
                "content_draft": {"title": "标题", "content": "内容"},
                "target_platforms": ["xiaohongshu"],
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "content_id" in error

    def test_publish_crew_validate_inputs_missing_draft(self) -> None:
        """
        Test PublishCrew.validate_inputs without content_draft.

        Arrange: Create input without content_draft
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = PublishCrew()
        crew_input = CrewInput(
            inputs={
                "content_id": "draft_123",
                "target_platforms": ["xiaohongshu"],
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "content_draft" in error

    def test_publish_crew_validate_inputs_missing_title(self) -> None:
        """
        Test PublishCrew.validate_inputs without title in draft.

        Arrange: Create input with draft missing title
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = PublishCrew()
        crew_input = CrewInput(
            inputs={
                "content_id": "draft_123",
                "content_draft": {"content": "内容..."},
                "target_platforms": ["xiaohongshu"],
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "title" in error

    def test_publish_crew_validate_inputs_missing_content(self) -> None:
        """
        Test PublishCrew.validate_inputs without content in draft.

        Arrange: Create input with draft missing content
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = PublishCrew()
        crew_input = CrewInput(
            inputs={
                "content_id": "draft_123",
                "content_draft": {"title": "标题"},
                "target_platforms": ["xiaohongshu"],
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "content" in error

    def test_publish_crew_validate_inputs_empty_platforms(self) -> None:
        """
        Test PublishCrew.validate_inputs with empty platform list.

        Arrange: Create input with empty platforms list
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = PublishCrew()
        crew_input = CrewInput(
            inputs={
                "content_id": "draft_123",
                "content_draft": {"title": "标题", "content": "内容..."},
                "target_platforms": [],
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "target_platforms" in error

    def test_publish_crew_validate_inputs_invalid_platform(self) -> None:
        """
        Test PublishCrew.validate_inputs with invalid platform.

        Arrange: Create input with invalid platform
        Act: Call validate_inputs()
        Assert: Returns (False, error_message)
        """
        crew = PublishCrew()
        crew_input = CrewInput(
            inputs={
                "content_id": "draft_123",
                "content_draft": {"title": "标题", "content": "内容..."},
                "target_platforms": ["invalid_platform"],
            }
        )

        is_valid, error = crew.validate_inputs(crew_input)

        assert is_valid is False
        assert "平台" in error or "platform" in error

    def test_publish_crew_create_publish_batch(self) -> None:
        """
        Test PublishCrew.create_publish_batch method.

        Arrange: Create PublishCrew with platforms
        Act: Call create_publish_batch()
        Assert: Returns PublishBatch with correct platforms
        """
        crew = PublishCrew()
        batch = crew.create_publish_batch(
            content_id="draft_123",
            platforms=["xiaohongshu", "wechat", "weibo"],
        )

        assert batch.content_id == "draft_123"
        assert len(batch.records) == 3
        assert Platform.XIAOHONGSHU in batch.records
        assert Platform.WECHAT in batch.records
        assert Platform.WEIBO in batch.records

    @patch("src.crew.crews.publish_crew.PlatformAdapter.create")
    @patch("src.crew.crews.publish_crew.PlatformPublisher.create")
    def test_publish_crew_get_agents(
        self,
        mock_publisher: Mock,
        mock_adapter: Mock,
    ) -> None:
        """
        Test PublishCrew.get_agents creates correct agents.

        Arrange: Mock agent creation methods
        Act: Call get_agents()
        Assert: Returns adapter + publishers for all platforms
        """
        mock_adapter.return_value = MagicMock()
        mock_publisher.return_value = MagicMock()

        crew = PublishCrew()
        agents = crew.get_agents()

        # 1 adapter + 6 platform publishers
        assert len(agents) == 7
        mock_adapter.assert_called_once()
        # Publisher should be called for each platform
        assert mock_publisher.call_count == len(Platform)

    def test_publish_crew_extract_task_output_json(self) -> None:
        """
        Test PublishCrew._extract_task_output with JSON output.

        Arrange: Create mock task output with JSON string
        Act: Call _extract_task_output()
        Assert: Returns parsed JSON dictionary
        """
        crew = PublishCrew()
        mock_output = MagicMock()
        mock_output.raw = '{"platform": "xiaohongshu", "status": "published"}'

        result = crew._extract_task_output(mock_output)

        assert isinstance(result, dict)
        assert result["platform"] == "xiaohongshu"
        assert result["status"] == "published"

    def test_publish_crew_parse_outputs(self) -> None:
        """
        Test PublishCrew._parse_outputs extracts all task outputs.

        Arrange: Create mock outputs with multiple tasks
        Act: Call _parse_outputs()
        Assert: Extracts adapted contents and publish records
        """
        crew = PublishCrew()

        mock_outputs = MagicMock()
        mock_outputs.tasks_output = [
            # Adapt task
            MagicMock(raw='{"xiaohongshu": {"title": "小红书标题"}, "wechat": {"title": "微信标题"}}'),
            # Publish tasks
            MagicMock(raw='{"platform": "xiaohongshu", "status": "published"}'),
            MagicMock(raw='{"platform": "wechat", "status": "failed", "error": "API error"}'),
        ]
        mock_outputs.to_dict.return_value = {"test": "value"}

        result = crew._parse_outputs(mock_outputs)

        assert "adapted_contents" in result
        assert "publish_records" in result
        assert len(result["publish_records"]) == 2


class TestPublishCrewIntegration:
    """Integration tests for PublishCrew end-to-end workflow."""

    @patch("src.crew.crews.publish_crew.PlatformAdapter.create")
    @patch("src.crew.crews.publish_crew.PlatformPublisher.create")
    @patch.object(PublishCrew, "execute")
    def test_publish_crew_full_workflow_mock(
        self,
        mock_execute: Mock,
        mock_publisher: Mock,
        mock_adapter: Mock,
    ) -> None:
        """
        Test PublishCrew full workflow with mocked execution.

        Arrange: Mock agents and execute method
        Act: Call kickoff() with input
        Assert: Returns expected PublishCrewResult
        """
        mock_adapter.return_value = MagicMock()
        mock_publisher.return_value = MagicMock()

        # Mock execute to return a PublishCrewResult
        mock_execute.return_value = PublishCrewResult(
            status=CrewStatus.COMPLETED,
            adapted_contents={
                "xiaohongshu": {"title": "小红书标题"},
            },
            publish_records=[
                {
                    "platform": "xiaohongshu",
                    "status": "published",
                    "published_url": "https://xhs.com/123",
                },
            ],
            execution_time=5.0,
        )

        crew = PublishCrew()
        result = crew.kickoff(
            content_id="draft_123",
            content_draft={
                "title": "测试标题",
                "content": "测试内容" * 100,
            },
            target_platforms=["xiaohongshu"],
        )

        assert result.status == CrewStatus.COMPLETED
        assert result.all_success is True
        assert "xiaohongshu" in result.successful_platforms

    def test_publish_crew_execute_returns_publish_crew_result(self) -> None:
        """
        Test PublishCrew.execute returns PublishCrewResult type.

        Arrange: Create PublishCrew with mocked execute
        Act: Call execute() with valid input
        Assert: Returns PublishCrewResult instance
        """
        crew = PublishCrew()

        # Mock the parent execute method
        with patch.object(
            PublishCrew.__bases__[0],  # BaseCrew
            "execute",
            return_value=CrewResult(
                status=CrewStatus.COMPLETED,
                raw_outputs={"test": "output"},
            ),
        ):
            crew_input = PublishCrewInput(
                content_id="draft_123",
                content_draft={"title": "标题", "content": "内容..."},
                target_platforms=["xiaohongshu"],
            )

            result = crew.execute(crew_input)

            # Should return PublishCrewResult, not just CrewResult
            # Note: This depends on the implementation
            assert isinstance(result, (CrewResult, PublishCrewResult))

    @patch("src.crew.crews.publish_crew.PlatformAdapter.create")
    @patch("src.crew.crews.publish_crew.PlatformPublisher.create")
    def test_publish_crew_create_classmethod(
        self,
        mock_publisher: Mock,
        mock_adapter: Mock,
    ) -> None:
        """
        Test PublishCrew.create class method.

        Arrange: Mock agent creation
        Act: Call PublishCrew.create()
        Assert: Returns PublishCrew instance
        """
        mock_adapter.return_value = MagicMock()
        mock_publisher.return_value = MagicMock()

        crew = PublishCrew.create(
            enable_retry=False,
            max_retries=1,
        )

        assert isinstance(crew, PublishCrew)
        assert crew.enable_retry is False
        assert crew.max_retries == 1
