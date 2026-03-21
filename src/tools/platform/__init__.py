"""
Platform Publishing Tools

Provides tools for publishing content to various social media platforms.
Each platform tool implements a common interface for authentication,
publishing, analytics, and scheduling.

Supported platforms:
- Domestic (国内): 小红书, 微信公众号, 微博, 知乎, 抖音, B站
- Overseas (海外): Reddit, X/Twitter, Facebook, Instagram, Threads
"""

from .base import BasePlatformTool, PublishContent, PublishResult, ContentType, AuthStatus
from .xiaohongshu import XiaohongshuTool
from .wechat import WechatTool
from .weibo import WeiboTool
from .zhihu import ZhihuTool
from .douyin import DouyinTool
from .bilibili import BilibiliTool

# Import overseas platforms — SDK-based (preferred) with CDP fallback
OVERSEAS_SDK_AVAILABLE = False
OVERSEAS_CDP_AVAILABLE = False

try:
    from .overseas_sdk import (
        RedditSDKTool,
        TwitterSDKTool,
        InstagramSDKTool,
        FacebookSDKTool,
        ThreadsSDKTool,
    )
    OVERSEAS_SDK_AVAILABLE = True
except ImportError:
    pass

try:
    from .overseas import (
        RedditTool as RedditCDPTool,
        TwitterTool as TwitterCDPTool,
        InstagramTool as InstagramCDPTool,
        FacebookTool as FacebookCDPTool,
        ThreadsTool as ThreadsCDPTool,
        get_overseas_platform_tool,
    )
    OVERSEAS_CDP_AVAILABLE = True
except ImportError:
    pass

OVERSEAS_AVAILABLE = OVERSEAS_SDK_AVAILABLE or OVERSEAS_CDP_AVAILABLE

# Resolve overseas tool classes: SDK preferred, CDP fallback
if OVERSEAS_SDK_AVAILABLE:
    RedditTool = RedditSDKTool
    TwitterTool = TwitterSDKTool
    InstagramTool = InstagramSDKTool
    FacebookTool = FacebookSDKTool
    ThreadsTool = ThreadsSDKTool
elif OVERSEAS_CDP_AVAILABLE:
    RedditTool = RedditCDPTool
    TwitterTool = TwitterCDPTool
    InstagramTool = InstagramCDPTool
    FacebookTool = FacebookCDPTool
    ThreadsTool = ThreadsCDPTool

# Platform registry
PLATFORM_REGISTRY = {
    # 国内平台
    "xiaohongshu": XiaohongshuTool,
    "小红书": XiaohongshuTool,
    "wechat": WechatTool,
    "微信公众号": WechatTool,
    "weibo": WeiboTool,
    "微博": WeiboTool,
    "zhihu": ZhihuTool,
    "知乎": ZhihuTool,
    "douyin": DouyinTool,
    "抖音": DouyinTool,
    "bilibili": BilibiliTool,
    "b站": BilibiliTool,
}

# Add overseas platforms if available
if OVERSEAS_AVAILABLE:
    PLATFORM_REGISTRY.update({
        "reddit": RedditTool,
        "twitter": TwitterTool,
        "x": TwitterTool,
        "instagram": InstagramTool,
        "facebook": FacebookTool,
        "threads": ThreadsTool,
    })

# All supported platforms
ALL_PLATFORMS = list(PLATFORM_REGISTRY.keys())

# Domestic platforms
DOMESTIC_PLATFORMS = ["xiaohongshu", "wechat", "weibo", "zhihu", "douyin", "bilibili"]

# Overseas platforms
OVERSEAS_PLATFORMS = ["reddit", "twitter", "instagram", "facebook", "threads"] if OVERSEAS_AVAILABLE else []


def get_platform_tool(platform: str, config: dict | None = None) -> BasePlatformTool:
    """
    Get a platform tool instance by platform name.

    Args:
        platform: Platform name (e.g., 'xiaohongshu', 'twitter')
        config: Platform-specific configuration

    Returns:
        Platform tool instance

    Raises:
        ValueError: If platform is not supported
    """
    platform_lower = platform.lower()
    if platform_lower not in PLATFORM_REGISTRY:
        raise ValueError(
            f"Unsupported platform: {platform}. "
            f"Supported platforms: {', '.join(PLATFORM_REGISTRY.keys())}"
        )

    tool_class = PLATFORM_REGISTRY[platform_lower]
    return tool_class(config=config)


def list_platforms(domestic: bool = True, overseas: bool = True) -> list[str]:
    """
    List all supported platforms.

    Args:
        domestic: Include domestic (Chinese) platforms
        overseas: Include overseas platforms

    Returns:
        List of platform names
    """
    platforms = []
    if domestic:
        platforms.extend(DOMESTIC_PLATFORMS)
    if overseas and OVERSEAS_AVAILABLE:
        platforms.extend(OVERSEAS_PLATFORMS)
    return platforms


__all__ = [
    # Base classes
    "BasePlatformTool",
    "PublishContent",
    "PublishResult",
    "ContentType",
    "AuthStatus",
    # Factory function
    "get_platform_tool",
    "list_platforms",
    # Platform lists
    "ALL_PLATFORMS",
    "DOMESTIC_PLATFORMS",
    "OVERSEAS_PLATFORMS",
    # Availability flags
    "OVERSEAS_SDK_AVAILABLE",
    "OVERSEAS_CDP_AVAILABLE",
    "OVERSEAS_AVAILABLE",
    # Domestic tools
    "XiaohongshuTool",
    "WechatTool",
    "WeiboTool",
    "ZhihuTool",
    "DouyinTool",
    "BilibiliTool",
    # Overseas tools (SDK or CDP depending on availability)
    "RedditTool",
    "TwitterTool",
    "InstagramTool",
    "FacebookTool",
    "ThreadsTool",
]
