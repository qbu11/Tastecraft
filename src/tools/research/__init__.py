"""
Research Tools for TopicResearcher Agent

Provides tools for:
- Hot search / trending topics
- WeChat article search (keyword-based)
- WeChat account spider (account-based)
"""

from .wechat_search import WeChatSearchTool, WeChatSearchResult, WeChatSearchResponse, search_wechat_articles
from .wechat_spider import WeChatArticleSpider, WeChatArticle, WeChatAccount, WeChatSpiderResponse

__all__ = [
    # WeChat Search (keyword-based)
    "WeChatSearchTool",
    "WeChatSearchResult",
    "WeChatSearchResponse",
    "search_wechat_articles",
    # WeChat Spider (account-based)
    "WeChatArticleSpider",
    "WeChatArticle",
    "WeChatAccount",
    "WeChatSpiderResponse",
]
