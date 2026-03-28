"""Unit tests for schedule API routes."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.routes.schedule import router


# ── App fixture ──────────────────────────────────────────────────


@pytest.fixture
def mock_scheduler():
    """Mock HotspotScheduler."""
    scheduler = MagicMock()
    scheduler.get_jobs.return_value = []
    return scheduler


@pytest.fixture
def app(mock_scheduler):
    """FastAPI test app with schedule router and mock scheduler."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api")
    test_app.state.scheduler = mock_scheduler
    return test_app


@pytest.fixture
def client(app):
    """TestClient for the test app."""
    return TestClient(app)


# ── POST /api/schedule ───────────────────────────────────────────


@pytest.mark.unit
class TestCreateSchedule:
    """Tests for POST /api/schedule."""

    def test_create_date_trigger(self, client, mock_scheduler):
        """Should create a one-time scheduled job."""
        mock_scheduler.add_custom_job.return_value = None

        resp = client.post("/api/schedule", json={
            "platform": "xiaohongshu",
            "content": {"title": "Test", "body": "Hello"},
            "publish_time": "2026-12-01T10:00:00",
            "trigger_type": "date",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "job_id" in data["data"]
        assert "scheduled_for" in data["data"]
        assert "xiaohongshu" in data["data"]["job_id"]
        mock_scheduler.add_custom_job.assert_called_once()

    def test_create_cron_trigger(self, client, mock_scheduler):
        """Should create a recurring cron job."""
        mock_scheduler.add_custom_job.return_value = None

        resp = client.post("/api/schedule", json={
            "platform": "weibo",
            "content": {"title": "Weekly post"},
            "publish_time": "2026-12-01T10:00:00",
            "trigger_type": "cron",
            "cron_expression": "0 10 * * 1",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "job_id" in data["data"]

    def test_invalid_publish_time(self, client):
        """Should return 400 for invalid ISO8601 datetime."""
        resp = client.post("/api/schedule", json={
            "platform": "xiaohongshu",
            "content": {},
            "publish_time": "not-a-date",
            "trigger_type": "date",
        })

        assert resp.status_code == 400
        assert "Invalid publish_time" in resp.json()["detail"]

    def test_cron_trigger_missing_expression(self, client):
        """Should return 400 when cron_expression is missing for cron trigger."""
        resp = client.post("/api/schedule", json={
            "platform": "xiaohongshu",
            "content": {},
            "publish_time": "2026-12-01T10:00:00",
            "trigger_type": "cron",
        })

        assert resp.status_code == 400
        assert "cron_expression" in resp.json()["detail"]

    def test_invalid_trigger_type(self, client):
        """Should return 400 for unknown trigger_type."""
        resp = client.post("/api/schedule", json={
            "platform": "xiaohongshu",
            "content": {},
            "publish_time": "2026-12-01T10:00:00",
            "trigger_type": "interval",
        })

        assert resp.status_code == 400
        assert "trigger_type" in resp.json()["detail"]

    def test_invalid_cron_expression(self, client):
        """Should return 400 for malformed cron expression."""
        resp = client.post("/api/schedule", json={
            "platform": "xiaohongshu",
            "content": {},
            "publish_time": "2026-12-01T10:00:00",
            "trigger_type": "cron",
            "cron_expression": "not a cron",
        })

        assert resp.status_code == 400


# ── GET /api/schedule ────────────────────────────────────────────


@pytest.mark.unit
class TestListSchedules:
    """Tests for GET /api/schedule."""

    def test_list_empty(self, client, mock_scheduler):
        """Should return empty list when no jobs exist."""
        mock_scheduler.get_jobs.return_value = []

        resp = client.get("/api/schedule")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["meta"]["total"] == 0

    def test_list_with_jobs(self, client, mock_scheduler):
        """Should return all scheduled jobs."""
        mock_scheduler.get_jobs.return_value = [
            {
                "id": "schedule-xiaohongshu-abc123",
                "name": "Publish to xiaohongshu",
                "next_run_time": "2026-12-01T10:00:00",
                "trigger": "date[2026-12-01 10:00:00]",
            },
            {
                "id": "daily_hotspot_detection",
                "name": "每日热点监控",
                "next_run_time": "2026-12-02T08:00:00",
                "trigger": "cron[hour='8']",
            },
        ]

        resp = client.get("/api/schedule")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == 2
        assert data["data"][0]["job_id"] == "schedule-xiaohongshu-abc123"
        assert data["data"][1]["job_id"] == "daily_hotspot_detection"

    def test_list_job_with_none_next_run_time(self, client, mock_scheduler):
        """Should handle jobs with no next_run_time."""
        mock_scheduler.get_jobs.return_value = [
            {
                "id": "paused-job",
                "name": "Paused",
                "next_run_time": None,
                "trigger": "cron[hour='8']",
            }
        ]

        resp = client.get("/api/schedule")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"][0]["next_run_time"] is None


# ── DELETE /api/schedule/{job_id} ────────────────────────────────


@pytest.mark.unit
class TestCancelSchedule:
    """Tests for DELETE /api/schedule/{job_id}."""

    def test_cancel_existing_job(self, client, mock_scheduler):
        """Should cancel an existing job and return cancelled status."""
        mock_scheduler.get_jobs.return_value = [
            {
                "id": "schedule-xiaohongshu-abc123",
                "name": "Publish to xiaohongshu",
                "next_run_time": "2026-12-01T10:00:00",
                "trigger": "date",
            }
        ]
        mock_scheduler.remove_job.return_value = None

        resp = client.delete("/api/schedule/schedule-xiaohongshu-abc123")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["job_id"] == "schedule-xiaohongshu-abc123"
        assert data["data"]["status"] == "cancelled"
        mock_scheduler.remove_job.assert_called_once_with("schedule-xiaohongshu-abc123")

    def test_cancel_nonexistent_job(self, client, mock_scheduler):
        """Should return 404 when job does not exist."""
        mock_scheduler.get_jobs.return_value = []

        resp = client.delete("/api/schedule/nonexistent-job-id")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_cancel_remove_raises(self, client, mock_scheduler):
        """Should return 500 when remove_job raises an exception."""
        mock_scheduler.get_jobs.return_value = [
            {
                "id": "job-to-fail",
                "name": "Failing job",
                "next_run_time": None,
                "trigger": "cron",
            }
        ]
        mock_scheduler.remove_job.side_effect = RuntimeError("Scheduler error")

        resp = client.delete("/api/schedule/job-to-fail")

        assert resp.status_code == 500
        assert "Failed to cancel job" in resp.json()["detail"]
