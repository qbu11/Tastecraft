"""Configuration tests."""

import pytest

from src.core.config import Settings, get_settings


@pytest.mark.unit
def test_default_settings() -> None:
    """Default settings load correctly."""
    s = Settings()
    assert s.APP_ENV == "development"
    assert s.API_PORT == 8000
    assert s.CREW_MAX_ITER == 15
    assert s.DEFAULT_LANGUAGE == "zh-CN"


@pytest.mark.unit
def test_get_settings_returns_instance() -> None:
    """get_settings returns a Settings instance."""
    s = get_settings()
    assert isinstance(s, Settings)
