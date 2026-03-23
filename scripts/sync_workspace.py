#!/usr/bin/env python3
"""
同步 workspace/crew-hotspot 的新功能到 C:\11projects\Crew

执行前提：
1. 已阅读 SYNC-PLAN.md
2. 当前在 feat/sync-workspace-modules 分支
3. 已备份原项目

使用：
    python scripts/sync_workspace.py --dry-run  # 预览
    python scripts/sync_workspace.py            # 执行
"""

import shutil
import sys
from pathlib import Path
from typing import List, Tuple

# 路径配置
WS_ROOT = Path(r"C:\Users\puzzl\metabot_workspace\crew-hotspot")
ORIG_ROOT = Path(r"C:\11projects\Crew")

# Phase 1: 新增独立模块映射
PHASE1_MODULES = [
    ("src/crew_hotspot/cookie_manager.py", "src/services/cookie_manager.py"),
    ("src/crew_hotspot/rate_limiter.py", "src/services/rate_limiter.py"),
    ("src/crew_hotspot/retry.py", "src/utils/retry.py"),
    ("src/crew_hotspot/task_queue.py", "src/services/task_queue.py"),
    ("src/crew_hotspot/scheduler.py", "src/services/scheduler.py"),
    ("src/crew_hotspot/publish_engine_v2.py", "src/services/publish_engine_v2.py"),
    ("src/crew_hotspot/data_collector.py", "src/services/data_collector.py"),
    ("src/crew_hotspot/api_routes/image_router.py", "src/api/routes/images.py"),
    ("src/crew_hotspot/tools/image_generator.py", "src/tools/image_generator.py"),
]

# Phase 3: 数据文件
PHASE3_DATA = [
    ("data/cookies", "data/cookies"),
    ("data/drafts", "data/drafts"),
]

# Phase 4: 文档
PHASE4_DOCS = [
    ("DEPLOY.md", "docs/DEPLOY.md"),
    ("QUICKSTART.md", "docs/QUICKSTART.md"),
    ("PUBLISH.md", "docs/PUBLISH.md"),
    ("Dockerfile", "Dockerfile"),
    ("docs/feishu_upload_guide.md", "docs/features/feishu-upload-guide.md"),
    ("docs/weibo-image-research.md", "docs/research/weibo-image-research.md"),
    ("docs/xiaohongshu-image-research.md", "docs/research/xiaohongshu-image-research.md"),
    ("docs/zhihu-image-research.md", "docs/research/zhihu-image-research.md"),
]


def adapt_imports(content: str, file_path: str) -> str:
    """
    适配 import 路径: crew_hotspot.xxx -> src.xxx

    ORIG 的 import 约定：
    - 全部使用绝对 import，以 src. 开头
    - 模型：from src.models.xxx import XxxModel
    - 配置：from src.core.config import settings
    - 日志：import logging; logger = logging.getLogger(__name__)
    - 错误处理：from src.core.error_handling import Result, success, error
    - 异常：from src.core.exceptions import CrewException
    """
    import re

    # 基本 import 替换
    content = content.replace("from crew_hotspot.", "from src.")
    content = content.replace("import crew_hotspot.", "import src.")

    # database.py 的自定义 ORM import 映射到 SQLAlchemy models
    # WS: from src.database import DatabaseManager, ...
    # ORIG: from src.models import Client, Account, HotTopic, Metrics
    content = content.replace("from src.database import", "from src.models import")

    # WS 的 api_routes 映射到 ORIG 的 api.routes
    content = content.replace("from src.api_routes.", "from src.api.routes.")

    # 标记需要人工检查的行
    lines = content.split("\n")
    flagged_lines = []
    for i, line in enumerate(lines, 1):
        # 检查是否还有 crew_hotspot 引用
        if "crew_hotspot" in line and not line.strip().startswith("#"):
            flagged_lines.append(f"  Line {i}: {line.strip()}")

    if flagged_lines:
        header = f"# ⚠️ MANUAL CHECK NEEDED - remaining crew_hotspot references:\n"
        header += "\n".join(f"#   {fl}" for fl in flagged_lines)
        content = header + "\n\n" + content

    return content


def copy_and_adapt(src: Path, dst: Path, dry_run: bool = False) -> bool:
    """复制文件并适配 import"""
    if not src.exists():
        print(f"❌ 源文件不存在: {src}")
        return False

    if dst.exists():
        print(f"⚠️  目标文件已存在: {dst}")
        return False

    # 读取源文件
    content = src.read_text(encoding="utf-8")

    # 适配 import（仅 Python 文件）
    if src.suffix == ".py":
        content = adapt_imports(content, str(dst))

    if dry_run:
        print(f"📋 [DRY-RUN] {src.relative_to(WS_ROOT)} → {dst.relative_to(ORIG_ROOT)}")
        return True

    # 创建目标目录
    dst.parent.mkdir(parents=True, exist_ok=True)

    # 写入
    dst.write_text(content, encoding="utf-8")
    print(f"✅ {src.relative_to(WS_ROOT)} → {dst.relative_to(ORIG_ROOT)}")
    return True


def copy_directory(src: Path, dst: Path, dry_run: bool = False) -> bool:
    """复制目录"""
    if not src.exists():
        print(f"❌ 源目录不存在: {src}")
        return False

    if dst.exists():
        print(f"⚠️  目标目录已存在: {dst}")
        return False

    if dry_run:
        print(f"📁 [DRY-RUN] {src.relative_to(WS_ROOT)} → {dst.relative_to(ORIG_ROOT)}")
        return True

    shutil.copytree(src, dst)
    print(f"✅ {src.relative_to(WS_ROOT)} → {dst.relative_to(ORIG_ROOT)}")
    return True


def phase1_modules(dry_run: bool = False) -> Tuple[int, int]:
    """Phase 1: 新增独立模块"""
    print("\n" + "=" * 60)
    print("Phase 1: 新增独立模块")
    print("=" * 60)

    success = 0
    total = len(PHASE1_MODULES)

    for src_rel, dst_rel in PHASE1_MODULES:
        src = WS_ROOT / src_rel
        dst = ORIG_ROOT / dst_rel
        if copy_and_adapt(src, dst, dry_run):
            success += 1

    return success, total


def phase3_data(dry_run: bool = False) -> Tuple[int, int]:
    """Phase 3: 数据文件"""
    print("\n" + "=" * 60)
    print("Phase 3: 数据文件")
    print("=" * 60)

    success = 0
    total = len(PHASE3_DATA)

    for src_rel, dst_rel in PHASE3_DATA:
        src = WS_ROOT / src_rel
        dst = ORIG_ROOT / dst_rel
        if copy_directory(src, dst, dry_run):
            success += 1

    return success, total


def phase4_docs(dry_run: bool = False) -> Tuple[int, int]:
    """Phase 4: 文档"""
    print("\n" + "=" * 60)
    print("Phase 4: 文档")
    print("=" * 60)

    success = 0
    total = len(PHASE4_DOCS)

    for src_rel, dst_rel in PHASE4_DOCS:
        src = WS_ROOT / src_rel
        dst = ORIG_ROOT / dst_rel
        if copy_and_adapt(src, dst, dry_run):
            success += 1

    return success, total


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("🔍 DRY-RUN 模式（仅预览，不实际复制）\n")
    else:
        print("⚠️  即将执行同步操作，请确认：")
        print(f"   源目录: {WS_ROOT}")
        print(f"   目标目录: {ORIG_ROOT}")
        confirm = input("\n继续？(yes/no): ")
        if confirm.lower() != "yes":
            print("❌ 已取消")
            return

    # 执行各阶段
    results = []
    results.append(("Phase 1: 新增独立模块", *phase1_modules(dry_run)))
    results.append(("Phase 3: 数据文件", *phase3_data(dry_run)))
    results.append(("Phase 4: 文档", *phase4_docs(dry_run)))

    # 汇总
    print("\n" + "=" * 60)
    print("同步汇总")
    print("=" * 60)

    total_success = 0
    total_files = 0

    for phase_name, success, total in results:
        total_success += success
        total_files += total
        status = "✅" if success == total else "⚠️"
        print(f"{status} {phase_name}: {success}/{total}")

    print(f"\n总计: {total_success}/{total_files} 文件")

    if not dry_run and total_success == total_files:
        print("\n✅ 同步完成！")
        print("\n下一步：")
        print("1. 检查 import 路径: grep -r 'crew_hotspot' src/")
        print("2. 运行测试: pytest")
        print("3. 类型检查: mypy src/ --strict")
        print("4. 代码检查: ruff check src/")
    elif not dry_run:
        print("\n⚠️  部分文件同步失败，请检查日志")


if __name__ == "__main__":
    main()
