"""
批量登录脚本 - 使用 Chrome DevTools MCP 完成平台登录

使用方法:
1. 运行此脚本
2. 脚本会依次打开各平台登录页
3. 你扫码登录
4. 自动保存 Cookie
5. 下次发布时自动使用

依赖:
- Chrome DevTools MCP 服务已启动
- Chrome 浏览器已安装
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crew_hotspot.cookie_manager import get_cookie_manager, CookieManager


# 平台配置
PLATFORMS = [
    {
        "id": "xiaohongshu",
        "name": "小红书",
        "login_url": "https://creator.xiaohongshu.com/login",
        "success_indicators": ["发布笔记", "创作中心", "数据看板"],
        "username_default": "default",
    },
    {
        "id": "weibo",
        "name": "微博",
        "login_url": "https://weibo.com/login.php",
        "success_indicators": ["首页", "发布", "我的"],
        "username_default": "default",
    },
    {
        "id": "zhihu",
        "name": "知乎",
        "login_url": "https://www.zhihu.com/signin",
        "success_indicators": ["写文章", "提问", "我的"],
        "username_default": "default",
    },
    {
        "id": "bilibili",
        "name": "B站",
        "login_url": "https://passport.bilibili.com/login",
        "success_indicators": ["投稿", "创作中心", "个人空间"],
        "username_default": "default",
    },
    {
        "id": "douyin",
        "name": "抖音",
        "login_url": "https://creator.douyin.com/",
        "success_indicators": ["发布视频", "创作者中心", "数据分析"],
        "username_default": "default",
    },
]


class BatchLoginManager:
    """批量登录管理器"""

    def __init__(self):
        self.cookie_manager = get_cookie_manager()
        self.logged_platforms: List[str] = []

    def print_header(self, title: str):
        """打印标题头"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60 + "\n")

    def print_platform_status(self):
        """打印各平台登录状态"""
        self.print_header("当前登录状态")

        summary = self.cookie_manager.get_status_summary()

        for platform_id, status in summary.items():
            platform_name = next(
                (p["name"] for p in PLATFORMS if p["id"] == platform_id),
                platform_id
            )

            if status["logged_in"]:
                days = status.get("days_left", 0)
                if days > 3:
                    status_text = f"[OK] 已登录 (剩余 {days} 天)"
                elif days > 0:
                    status_text = f"[WARN] 即将过期 (剩余 {days} 天)"
                else:
                    status_text = "[EXPIRED] 已过期"
            else:
                status_text = "[NOT_LOGGED_IN] 未登录"

            print(f"  {platform_name:8} {status_text}")

        print()

    async def login_platform_via_chrome_mcp(self, platform: Dict[str, Any]) -> bool:
        """
        使用 Chrome DevTools MCP 登录单个平台

        注意: 这个函数需要在 Claude Code 环境中运行,
        由 Claude 调用 mcp__chrome-devtools__* 工具完成实际操作。

        这里只提供流程说明和状态跟踪。
        """
        platform_id = platform["id"]
        platform_name = platform["name"]

        print(f"\n>>> 准备登录: {platform_name}")
        print(f"    登录地址: {platform['login_url']}")
        print(f"    请在浏览器中扫码登录...")

        # 实际登录操作需要 Claude 调用 Chrome MCP 工具
        # 这里只是流程说明

        return False

    def save_cookies_from_chrome(
        self,
        platform_id: str,
        cookies: List[Dict[str, Any]],
        username: str = "default"
    ) -> bool:
        """保存从 Chrome 提取的 Cookie"""
        return self.cookie_manager.save_cookies(
            platform=platform_id,
            username=username,
            cookies=cookies
        )

    def get_pending_platforms(self) -> List[Dict[str, Any]]:
        """获取需要登录的平台列表"""
        summary = self.cookie_manager.get_status_summary()

        pending = []
        for platform in PLATFORMS:
            pid = platform["id"]
            status = summary.get(pid, {})

            # 未登录或已过期
            if not status.get("logged_in") or status.get("status") == "expired":
                pending.append(platform)

        return pending


def main():
    """主函数"""
    manager = BatchLoginManager()

    # 打印当前状态
    manager.print_platform_status()

    # 获取需要登录的平台
    pending = manager.get_pending_platforms()

    if not pending:
        print("所有平台都已登录!")
        return

    print(f"需要登录 {len(pending)} 个平台:\n")
    for i, p in enumerate(pending, 1):
        print(f"  {i}. {p['name']}")

    print("\n" + "-" * 60)
    print("""
要开始批量登录,请在 Claude Code 中运行:

    /batch-login

或者告诉 Claude:

    "帮我登录这 5 个平台"

Claude 会使用 Chrome DevTools MCP 自动化完成登录流程。
    """)


if __name__ == "__main__":
    main()
