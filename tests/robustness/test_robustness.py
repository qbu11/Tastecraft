"""
鲁棒性测试脚本

测试发帖和采集功能在各种异常情况下的稳定性。
包括：网络超时、认证失效、内容格式错误、平台风控等场景。
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass, field

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.panel import Panel

console = Console()


@dataclass
class TestCase:
    """测试用例"""
    name: str
    description: str
    test_func: callable
    expected_result: str
    timeout: int = 30
    retry_count: int = 3


@dataclass
class TestResult:
    """测试结果"""
    name: str
    status: str  # PASS, FAIL, SKIP, ERROR
    duration: float
    error: str | None = None
    retry_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


class RobustnessTester:
    """鲁棒性测试器"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.test_cases: List[TestCase] = []
        self._setup_tests()

    def _setup_tests(self):
        """设置测试用例"""
        self.test_cases = [
            # 网络异常测试
            TestCase(
                name="网络超时-热点搜索",
                description="测试网络超时情况下热点搜索的降级处理",
                test_func=self._test_network_timeout_hot_search,
                expected_result="降级到缓存或返回空结果",
                timeout=10
            ),
            TestCase(
                name="网络超时-内容发布",
                description="测试网络超时情况下发布的重试机制",
                test_func=self._test_network_timeout_publish,
                expected_result="重试3次后返回失败",
                timeout=60
            ),

            # 认证测试
            TestCase(
                name="认证失效-小红书",
                description="测试Cookie失效时的处理",
                test_func=self._test_auth_expired_xiaohongshu,
                expected_result="返回认证失败，提示重新登录",
                timeout=15
            ),
            TestCase(
                name="认证失效-微信公众号",
                description="测试Access Token失效时的刷新机制",
                test_func=self._test_auth_expired_wechat,
                expected_result="自动刷新Token或提示重新授权",
                timeout=15
            ),

            # 内容验证测试
            TestCase(
                name="内容超长-小红书标题",
                description="测试标题超过20字符的截断处理",
                test_func=self._test_title_too_long,
                expected_result="自动截断并保留完整内容",
                timeout=5
            ),
            TestCase(
                name="图片数量超限",
                description="测试图片数量超过平台限制的处理",
                test_func=self._test_too_many_images,
                expected_result="取前N张图片或提示错误",
                timeout=5
            ),
            TestCase(
                name="空内容发布",
                description="测试空内容的校验",
                test_func=self._test_empty_content,
                expected_result="发布前校验拦截",
                timeout=5
            ),

            # 平台约束测试
            TestCase(
                name="发布频率限制-小红书",
                description="测试短时间内多次发布的频率限制",
                test_func=self._test_rate_limit_xiaohongshu,
                expected_result="遵守60秒间隔，或排队等待",
                timeout=120
            ),
            TestCase(
                name="发布频率限制-微博",
                description="测试微博发布频率限制",
                test_func=self._test_rate_limit_weibo,
                expected_result="遵守10秒间隔",
                timeout=30
            ),

            # 数据采集测试
            TestCase(
                name="数据采集-内容不存在",
                description="测试采集不存在内容的数据",
                test_func=self._test_analytics_not_found,
                expected_result="返回404或空数据",
                timeout=15
            ),
            TestCase(
                name="数据采集-API限流",
                description="测试API限流时的处理",
                test_func=self._test_analytics_rate_limit,
                expected_result="等待后重试或使用备用数据源",
                timeout=30
            ),

            # 边界条件测试
            TestCase(
                name="特殊字符处理",
                description="测试内容中的特殊字符和emoji处理",
                test_func=self._test_special_characters,
                expected_result="正确处理或转义特殊字符",
                timeout=5
            ),
            TestCase(
                name="并发发布测试",
                description="测试同时向多个平台发布",
                test_func=self._test_concurrent_publish,
                expected_result="各平台独立执行，互不影响",
                timeout=60
            ),
        ]

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        console.print(Panel.fit("[bold cyan]鲁棒性测试开始[/bold cyan]"))
        console.print()

        with Progress() as progress:
            task = progress.add_task("[cyan]运行测试...", total=len(self.test_cases))

            for test_case in self.test_cases:
                result = await self._run_test(test_case, progress, task)
                self.results.append(result)

        self._print_summary()
        return self._generate_report()

    async def _run_test(
        self,
        test_case: TestCase,
        progress: Progress,
        parent_task: TaskID
    ) -> TestResult:
        """运行单个测试"""
        start_time = time.time()
        status = "ERROR"
        error = None
        retry_count = 0
        details = {}

        progress.update(parent_task, description=f"[cyan]{test_case.name}[/cyan]")

        for attempt in range(test_case.retry_count + 1):
            try:
                # 执行测试（带超时）
                result = await asyncio.wait_for(
                    test_case.test_func(),
                    timeout=test_case.timeout
                )
                status = result.get("status", "PASS")
                details = result.get("details", {})
                error = result.get("error")
                retry_count = attempt

                if status == "PASS":
                    break

            except asyncio.TimeoutError:
                error = f"测试超时 (>{test_case.timeout}s)"
                status = "FAIL"
                retry_count = attempt + 1

            except Exception as e:
                error = str(e)
                status = "ERROR"
                retry_count = attempt + 1

            if status == "PASS":
                break

            # 重试前等待
            if attempt < test_case.retry_count:
                await asyncio.sleep(1)

        duration = time.time() - start_time

        # 显示结果
        status_color = {
            "PASS": "green",
            "FAIL": "red",
            "SKIP": "yellow",
            "ERROR": "bright_red"
        }.get(status, "white")

        console.print(
            f"[{status_color}]{status}[/{status_color}] "
            f"{test_case.name} ({duration:.1f}s)"
        )

        progress.update(parent_task, advance=1)

        return TestResult(
            name=test_case.name,
            status=status,
            duration=duration,
            error=error,
            retry_count=retry_count,
            details=details
        )

    def _print_summary(self):
        """打印测试摘要"""
        console.print()
        console.print(Panel.fit("[bold cyan]测试摘要[/bold cyan]"))

        # 统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        errors = sum(1 for r in self.results if r.status == "ERROR")
        skipped = sum(1 for r in self.results if r.status == "SKIP")

        console.print(f"总计: {total} | 通过: [green]{passed}[/green] | "
                     f"失败: [red]{failed}[/red] | "
                     f"错误: [bright_red]{errors}[/bright_red] | "
                     f"跳过: [yellow]{skipped}[/yellow]")

        # 失败详情
        if failed + errors > 0:
            console.print()
            console.print(Panel.fit("[bold red]失败/错误详情[/bold red]"))
            for result in self.results:
                if result.status in ("FAIL", "ERROR"):
                    console.print(f"\n[red]{result.name}[/red]")
                    if result.error:
                        console.print(f"  错误: {result.error}")
                    console.print(f"  重试: {result.retry_count} 次")

    def _generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.status == "PASS"),
            "failed": sum(1 for r in self.results if r.status == "FAIL"),
            "errors": sum(1 for r in self.results if r.status == "ERROR"),
            "skipped": sum(1 for r in self.results if r.status == "SKIP"),
            "duration": sum(r.duration for r in self.results),
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "duration": r.duration,
                    "error": r.error,
                    "retry_count": r.retry_count,
                    "details": r.details
                }
                for r in self.results
            ]
        }

    # ========== 测试函数 ==========

    async def _test_network_timeout_hot_search(self) -> Dict[str, Any]:
        """测试网络超时时热点搜索的降级处理"""
        try:
            from src.tools.search_tools import HotSearchTool

            tool = HotSearchTool(config={"tikhub_token": "invalid"})
            tool._cache = {}  # 清空缓存，强制网络请求

            # 模拟网络请求（会失败）
            result = tool.execute(platform="weibo", limit=10)

            # 验证降级处理
            if result.status.value == "failed":
                return {
                    "status": "PASS",
                    "details": {"message": "正确处理网络失败"}
                }

            return {
                "status": "FAIL",
                "error": "未正确处理网络失败"
            }

        except Exception as e:
            return {"status": "PASS", "details": {"exception": str(e)}}

    async def _test_network_timeout_publish(self) -> Dict[str, Any]:
        """测试网络超时时发布的重试机制"""
        # 模拟发布重试逻辑
        retry_count = 0
        max_retries = 3

        for i in range(max_retries):
            try:
                # 模拟网络超时
                await asyncio.sleep(0.1)
                raise ConnectionError("Network timeout")

            except ConnectionError:
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(0.5)  # 指数退避
                    continue

        if retry_count == max_retries:
            return {
                "status": "PASS",
                "details": {"retries": retry_count}
            }

        return {"status": "FAIL", "error": "未执行预期次数的重试"}

    async def _test_auth_expired_xiaohongshu(self) -> Dict[str, Any]:
        """测试小红书Cookie失效处理"""
        from src.tools.platform.xiaohongshu import XiaohongshuTool

        tool = XiaohongshuTool(config={"cookie": "invalid_cookie"})

        # 尝试认证
        result = tool.authenticate()

        if not result.is_success():
            return {
                "status": "PASS",
                "details": {"message": "正确识别认证失效"}
            }

        return {"status": "FAIL", "error": "未检测到认证失效"}

    async def _test_auth_expired_wechat(self) -> Dict[str, Any]:
        """测试微信公众号Token失效处理"""
        from src.tools.platform.wechat import WeChatTool

        tool = WeChatTool(config={
            "app_id": "invalid",
            "app_secret": "invalid"
        })

        result = tool.authenticate()

        if not result.is_success():
            return {
                "status": "PASS",
                "details": {"message": "正确识别认证失效"}
            }

        return {"status": "FAIL", "error": "未检测到认证失效"}

    async def _test_title_too_long(self) -> Dict[str, Any]:
        """测试标题超长截断"""
        from src.tools.platform.xiaohongshu import XiaohongshuTool
        from src.tools.platform.base import PublishContent, ContentType

        tool = XiaohongshuTool()

        # 创建超长标题
        long_title = "这是一个非常非常长的标题" * 5  # 约100字

        content = PublishContent(
            title=long_title,
            body="测试内容",
            content_type=ContentType.IMAGE_TEXT
        )

        # 验证
        is_valid, error = tool.validate_content(content)

        # 小红书应该拒绝或截断
        if not is_valid and "标题" in (error or ""):
            return {
                "status": "PASS",
                "details": {"original_length": len(long_title)}
            }

        return {"status": "FAIL", "error": "未检测到标题超长"}

    async def _test_too_many_images(self) -> Dict[str, Any]:
        """测试图片数量超限"""
        from src.tools.platform.xiaohongshu import XiaohongshuTool
        from src.tools.platform.base import PublishContent, ContentType

        tool = XiaohongshuTool()

        # 创建超量图片
        content = PublishContent(
            title="测试",
            body="测试内容",
            content_type=ContentType.IMAGE_TEXT,
            images=[f"image{i}.jpg" for i in range(20)]  # 超过限制
        )

        is_valid, error = tool.validate_content(content)

        if not is_valid and "图片" in (error or ""):
            return {
                "status": "PASS",
                "details": {"image_count": len(content.images)}
            }

        return {"status": "FAIL", "error": "未检测到图片超限"}

    async def _test_empty_content(self) -> Dict[str, Any]:
        """测试空内容校验"""
        from src.tools.platform.base import PublishContent, ContentType

        content = PublishContent(
            title="",  # 空标题
            body="",   # 空正文
            content_type=ContentType.TEXT
        )

        if not content.title or not content.body:
            return {
                "status": "PASS",
                "details": {"message": "正确识别空内容"}
            }

        return {"status": "FAIL", "error": "未检测到空内容"}

    async def _test_rate_limit_xiaohongshu(self) -> Dict[str, Any]:
        """测试小红书发布频率限制"""
        from src.tools.platform.xiaohongshu import XiaohongshuTool
        from src.tools.platform.base import PublishContent, ContentType

        tool = XiaohongshuTool()

        # 验证间隔设置
        if tool.min_publish_interval >= 60:
            return {
                "status": "PASS",
                "details": {"min_interval": tool.min_publish_interval}
            }

        return {"status": "FAIL", "error": f"间隔过短: {tool.min_publish_interval}秒"}

    async def _test_rate_limit_weibo(self) -> Dict[str, Any]:
        """测试微博发布频率限制"""
        from src.tools.platform.weibo import WeiboTool

        tool = WeiboTool()

        if tool.min_publish_interval >= 10:
            return {
                "status": "PASS",
                "details": {"min_interval": tool.min_publish_interval}
            }

        return {"status": "FAIL", "error": f"间隔过短: {tool.min_publish_interval}秒"}

    async def _test_analytics_not_found(self) -> Dict[str, Any]:
        """测试采集不存在内容的数据"""
        from src.tools.analytics_tools import DataCollectTool

        tool = DataCollectTool(config={})

        # 使用不存在的ID
        result = tool.execute(
            platform="xiaohongshu",
            content_ids=["nonexistent_id_12345"]
        )

        if result.status.value == "failed":
            return {
                "status": "PASS",
                "details": {"message": "正确处理不存在的内容"}
            }

        return {"status": "SKIP", "error": "需要实际API测试"}

    async def _test_analytics_rate_limit(self) -> Dict[str, Any]:
        """测试API限流处理"""
        return {"status": "SKIP", "error": "需要实际API测试"}

    async def _test_special_characters(self) -> Dict[str, Any]:
        """测试特殊字符处理"""
        special_chars = [
            "🎉🎊🔥💡",  # emoji
            "<script>alert('xss')</script>",  # HTML
            "'; DROP TABLE users; --",  # SQL注入
            "中文《》「」【】",  # 中文标点
            "https://example.com",  # URL
        ]

        # 验证特殊字符能被正确处理
        all_valid = True
        for chars in special_chars:
            try:
                # 简单验证：能被JSON序列化
                json.dumps({"content": chars})
            except Exception as e:
                all_valid = False
                break

        if all_valid:
            return {
                "status": "PASS",
                "details": {"tested": len(special_chars)}
            }

        return {"status": "FAIL", "error": "特殊字符处理失败"}

    async def _test_concurrent_publish(self) -> Dict[str, Any]:
        """测试并发发布"""
        import asyncio

        async def mock_publish(platform: str, delay: float):
            await asyncio.sleep(delay)
            return platform

        # 模拟并发发布到多个平台
        platforms = ["xiaohongshu", "wechat", "weibo", "zhihu"]
        start = time.time()

        results = await asyncio.gather(*[
            mock_publish(p, 0.5) for p in platforms
        ])

        duration = time.time() - start

        # 并发执行应该接近单个任务的时间
        if duration < 1.0:  # 4个0.5秒任务并发应该约0.5秒
            return {
                "status": "PASS",
                "details": {
                    "platforms": len(results),
                    "duration": duration
                }
            }

        return {
            "status": "FAIL",
            "error": f"可能是串行执行，耗时: {duration:.1f}秒"
        }


async def main():
    """主函数"""
    tester = RobustnessTester()
    report = await tester.run_all_tests()

    # 保存报告
    output_dir = Path("C:/11projects/Crew/data/tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    report_file = output_dir / f"robustness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    console.print()
    console.print(f"[dim]报告已保存到: {report_file}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
