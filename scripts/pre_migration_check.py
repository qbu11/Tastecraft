#!/usr/bin/env python3
"""
迁移前环境检查脚本

检查 ORIG 项目环境是否满足迁移要求。
运行方式：python scripts/pre_migration_check.py
"""

import subprocess
import sys
from pathlib import Path


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def ok(msg: str) -> None:
    print(f"  {Colors.GREEN}OK{Colors.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {Colors.YELLOW}WARN{Colors.RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {Colors.RED}FAIL{Colors.RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{Colors.BOLD}{'=' * 50}{Colors.RESET}")
    print(f"{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 50}{Colors.RESET}")


def check_python_version() -> bool:
    """检查 Python 版本"""
    section("1. Python 版本")
    version = sys.version_info
    if version >= (3, 11):
        ok(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        fail(f"Python {version.major}.{version.minor}.{version.micro} (需要 >= 3.11)")
        return False


def check_git_status() -> bool:
    """检查 Git 状态"""
    section("2. Git 状态")
    success = True

    # 当前分支
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True
    )
    branch = result.stdout.strip()
    if branch == "main":
        ok(f"当前分支: {branch}")
    else:
        warn(f"当前分支: {branch} (建议切换到 main 后创建迁移分支)")

    # 未提交的更改
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True
    )
    changes = result.stdout.strip()
    if changes:
        lines = changes.split("\n")
        warn(f"有 {len(lines)} 个未提交的更改:")
        for line in lines[:5]:
            print(f"    {line}")
        if len(lines) > 5:
            print(f"    ... 还有 {len(lines) - 5} 个")
    else:
        ok("工作区干净")

    # 未推送的提交
    result = subprocess.run(
        ["git", "log", "--oneline", "@{u}..HEAD"],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        commits = result.stdout.strip().split("\n")
        warn(f"有 {len(commits)} 个未推送的提交")
    elif result.returncode != 0:
        warn("无法检查远程跟踪状态")

    return success


def check_dependencies() -> bool:
    """检查依赖"""
    section("3. Python 依赖")
    success = True

    required_packages = [
        ("crewai", "0.80.0"),
        ("fastapi", "0.115.0"),
        ("sqlalchemy", "2.0.0"),
        ("aiosqlite", "0.20.0"),
        ("pydantic", "2.9.0"),
        ("pydantic_settings", "2.6.0"),
    ]

    new_packages = [
        ("apscheduler", "3.10.0"),
        ("aiofiles", None),
    ]

    for pkg_name, min_version in required_packages:
        try:
            mod = __import__(pkg_name.replace("-", "_"))
            version = getattr(mod, "__version__", "unknown")
            ok(f"{pkg_name} == {version}")
        except ImportError:
            fail(f"{pkg_name} 未安装")
            success = False

    print()
    for pkg_name, min_version in new_packages:
        try:
            mod = __import__(pkg_name.replace("-", "_"))
            version = getattr(mod, "__version__", "unknown")
            ok(f"{pkg_name} == {version}")
        except ImportError:
            warn(f"{pkg_name} 未安装 (迁移时需要: uv add {pkg_name})")

    return success


def check_external_skills() -> bool:
    """检查外部 skills"""
    section("4. 外部 Skills")
    success = True

    home = Path.home()

    # gstack
    gstack_browse = home / ".claude" / "skills" / "gstack" / "bin" / "gstack-browse"
    if gstack_browse.exists():
        ok("gstack-browse 已安装")
    else:
        warn("gstack-browse 未安装 (data_collector 将无法使用)")
        warn("  安装方法: cd ~/.claude/skills/gstack && ./setup")

    # media-publish skills
    for platform in ["xiaohongshu", "weibo", "zhihu"]:
        skill_dir = home / ".claude" / "skills" / f"media-publish-{platform}"
        if skill_dir.exists():
            ok(f"media-publish-{platform} 已安装")
        else:
            warn(f"media-publish-{platform} 未安装 (publish_engine 将降级)")

    return success


def check_database() -> bool:
    """检查数据库"""
    section("5. 数据库")
    success = True

    orig_root = Path(__file__).parent.parent
    db_dir = orig_root / "data"

    if db_dir.exists():
        ok(f"数据目录存在: {db_dir}")

        # 检查现有数据库
        db_files = list(db_dir.glob("*.db"))
        if db_files:
            for db_file in db_files:
                size = db_file.stat().st_size / 1024
                ok(f"数据库: {db_file.name} ({size:.1f} KB)")
        else:
            warn("没有现有数据库文件 (将自动创建)")

        # 检查备份
        backup_dir = db_dir / "backup"
        if backup_dir.exists():
            ok("备份目录已存在")
        else:
            warn("备份目录不存在 (建议: mkdir data/backup && cp data/*.db data/backup/)")
    else:
        warn("数据目录不存在 (将自动创建)")

    return success


def check_workspace_source() -> bool:
    """检查 WS 源文件"""
    section("6. Workspace 源文件")
    success = True

    ws_root = Path(r"C:\Users\puzzl\metabot_workspace\crew-hotspot")

    if not ws_root.exists():
        fail(f"WS 目录不存在: {ws_root}")
        return False

    ok(f"WS 目录存在: {ws_root}")

    # 检查核心模块
    modules = [
        "src/crew_hotspot/cookie_manager.py",
        "src/crew_hotspot/rate_limiter.py",
        "src/crew_hotspot/retry.py",
        "src/crew_hotspot/task_queue.py",
        "src/crew_hotspot/scheduler.py",
        "src/crew_hotspot/publish_engine_v2.py",
        "src/crew_hotspot/data_collector.py",
        "src/crew_hotspot/api_routes/image_router.py",
        "src/crew_hotspot/tools/image_generator.py",
    ]

    for module in modules:
        module_path = ws_root / module
        if module_path.exists():
            lines = len(module_path.read_text(encoding="utf-8").splitlines())
            ok(f"{module} ({lines} 行)")
        else:
            fail(f"{module} 不存在")
            success = False

    return success


def check_alembic() -> bool:
    """检查 Alembic 配置"""
    section("7. Alembic 迁移")

    orig_root = Path(__file__).parent.parent
    alembic_ini = orig_root / "alembic.ini"

    if alembic_ini.exists():
        ok("alembic.ini 存在")
    else:
        warn("alembic.ini 不存在 (需要配置 Alembic)")

    migrations_dir = orig_root / "migrations"
    if migrations_dir.exists():
        versions = list((migrations_dir / "versions").glob("*.py")) if (migrations_dir / "versions").exists() else []
        ok(f"migrations 目录存在 ({len(versions)} 个版本)")
    else:
        warn("migrations 目录不存在 (需要初始化 Alembic)")

    return True


def main() -> None:
    """运行所有检查"""
    print(f"\n{Colors.BOLD}迁移前环境检查{Colors.RESET}")
    print(f"{'=' * 50}")

    results = {
        "Python 版本": check_python_version(),
        "Git 状态": check_git_status(),
        "Python 依赖": check_dependencies(),
        "外部 Skills": check_external_skills(),
        "数据库": check_database(),
        "WS 源文件": check_workspace_source(),
        "Alembic": check_alembic(),
    }

    # 汇总
    section("汇总")
    all_passed = True

    for check_name, passed in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print(f"\n{Colors.GREEN}所有检查通过，可以开始迁移！{Colors.RESET}")
        print(f"\n下一步：")
        print(f"  1. git checkout main && git pull")
        print(f"  2. git checkout -b feature/workspace-sync")
        print(f"  3. mkdir -p data/backup && cp data/*.db data/backup/")
        print(f"  4. python scripts/sync_workspace.py --dry-run")
    else:
        print(f"\n{Colors.YELLOW}部分检查未通过，请先解决上述问题再开始迁移{Colors.RESET}")


if __name__ == "__main__":
    main()
