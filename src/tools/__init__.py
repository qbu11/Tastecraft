"""
CrewAI Tools for Media Publishing Platform

Provides tools for content publishing, analytics, and optimization
across multiple Chinese social media platforms.
"""

from .base_tool import BaseTool, ToolResult, ToolError
from .search_tools import (
    hot_search_tool,
    competitor_analysis_tool,
    trend_analysis_tool
)
from .content_tools import (
    image_search_tool,
    hashtag_suggest_tool,
    seo_optimize_tool
)
from .analytics_tools import (
    data_collect_tool,
    analytics_report_tool
)

__all__ = [
    # Base classes
    "BaseTool",
    "ToolResult",
    "ToolError",

    # Search tools
    "hot_search_tool",
    "competitor_analysis_tool",
    "trend_analysis_tool",

    # Content tools
    "image_search_tool",
    "hashtag_suggest_tool",
    "seo_optimize_tool",

    # Analytics tools
    "data_collect_tool",
    "analytics_report_tool",
]

__version__ = "0.1.0"
