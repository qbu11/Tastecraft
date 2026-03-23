# 迁移风险评估与缓解方案

> 基于深度检查报告，识别关键风险并提供解决方案

## 🚨 关键阻塞问题（P0 - 必须解决）

### 1. 数据库架构完全不兼容

**问题描述：**
- WS 使用 `sqlite3` 原生同步操作
- ORIG 使用 `SQLAlchemy + aiosqlite` 异步操作
- 所有依赖数据库的模块（`task_queue`, `scheduler`, `data_collector`）无法直接迁移

**影响范围：**
- `task_queue.py` - 直接使用 `sqlite3.connect()`
- `scheduler.py` - 调用 WS 的 `ClientManager`, `AccountManager`
- `data_collector.py` - 调用 `MetricsManager`

**解决方案：**

#### 方案A：完全重写为 SQLAlchemy（推荐）

**步骤：**

1. **创建新的 SQLAlchemy 模型**（已在 SYNC-PLAN.md Phase 2.1）
   - `src/models/client.py`
   - `src/models/account.py`
   - `src/models/hot_topic.py`
   - `src/models/task.py` (for task_queue)

2. **创建 Service 层替代 WS 的 Manager**

```python
# src/services/client_service.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.client import Client
from src.core.error_handling import Result, success, error

class ClientService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_client(self, name: str, industry: str | None = None) -> Result[Client]:
        try:
            client = Client(name=name, industry=industry)
            self.session.add(client)
            await self.session.commit()
            await self.session.refresh(client)
            return success(client)
        except Exception as e:
            await self.session.rollback()
            return error(f"Failed to create client: {e}", "CLIENT_CREATE_ERROR")

    async def list_clients(self, status: str | None = None) -> Result[list[Client]]:
        try:
            query = select(Client)
            if status:
                query = query.where(Client.status == status)
            result = await self.session.execute(query)
            clients = result.scalars().all()
            return success(list(clients))
        except Exception as e:
            return error(f"Failed to list clients: {e}", "CLIENT_LIST_ERROR")
```

3. **重写 task_queue.py 为异步**

```python
# src/services/task_queue.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.models.task import Task
from src.core.error_handling import Result, success, error

class TaskQueue:
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url)

    async def submit_task(self, task_type: str, payload: dict) -> Result[Task]:
        async with AsyncSession(self.engine) as session:
            task = Task(task_type=task_type, payload=payload, status="pending")
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return success(task)

    async def get_pending_tasks(self) -> Result[list[Task]]:
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(Task).where(Task.status == "pending")
            )
            tasks = result.scalars().all()
            return success(list(tasks))
```

4. **修改 scheduler.py 调用新 Service**

```python
# src/services/scheduler.py
from src.services.client_service import ClientService
from src.services.account_service import AccountService

class HotspotScheduler:
    def __init__(self, db_session: AsyncSession):
        self.client_service = ClientService(db_session)
        self.account_service = AccountService(db_session)

    async def daily_hotspot_job(self):
        result = await self.client_service.list_clients(status="active")
        if result.is_success:
            for client in result.data:
                # ...
```

**工作量估算：**
- 创建 4 个新模型：2 小时
- 创建 4 个 Service 类：4 小时
- 重写 task_queue：3 小时
- 修改 scheduler：2 小时
- 修改 data_collector：2 小时
- **总计：13 小时（约 2 天）**

#### 方案B：保留 sqlite3 + 添加异步包装（不推荐）

**优点：**
- 迁移快（1-2 小时）

**缺点：**
- 与 ORIG 架构不一致
- 同步操作会阻塞事件循环
- 维护两套数据库代码
- 未来难以扩展

**结论：采用方案A**

---

### 2. 缺失 HotspotDetectionCrew 和 ContentCreationCrew

**问题描述：**
- WS 的 `scheduler.py` 调用 `HotspotDetectionCrew` 和 `ContentCreationCrew`
- ORIG 只有 `ContentCrew`, `PublishCrew`, `AnalyticsCrew`

**影响范围：**
- `scheduler.py` 的定时任务无法运行

**解决方案：**

#### 选项1：创建新 Crew（推荐）

**文件：`src/crew/crews/hotspot_crew.py`**

```python
"""热点探测 Crew"""
from crewai import Agent, Task, Crew

from src.crew.crews.base_crew import BaseCrew, CrewInput, CrewResult
from src.agents.topic_researcher import TopicResearcher
from src.tools.search_tools import SearchTool

class HotspotDetectionInput(CrewInput):
    """热点探测输入"""
    keywords: list[str]
    platforms: list[str]

class HotspotDetectionResult(CrewResult):
    """热点探测结果"""
    hot_topics: list[dict]

class HotspotDetectionCrew(BaseCrew[HotspotDetectionInput, HotspotDetectionResult]):
    """热点探测 Crew"""

    def get_agents(self) -> list[Agent]:
        researcher = TopicResearcher()
        return [researcher.create_agent()]

    def get_tasks(self, input_data: HotspotDetectionInput) -> list[Task]:
        return [
            Task(
                description=f"搜索 {input_data.platforms} 平台的热点话题，关键词：{input_data.keywords}",
                agent=self.get_agents()[0],
                expected_output="热点话题列表（JSON 格式）",
            )
        ]

    def parse_result(self, crew_output: str) -> HotspotDetectionResult:
        # 解析 Crew 输出
        import json
        hot_topics = json.loads(crew_output)
        return HotspotDetectionResult(
            success=True,
            hot_topics=hot_topics,
        )
```

**工作量：**
- 创建 HotspotDetectionCrew：3 小时
- 创建 ContentCreationCrew（如果需要）：3 小时
- **总计：6 小时（约 1 天）**

#### 选项2：禁用相关调度任务

**修改 `scheduler.py`：**

```python
def setup_jobs(self):
    # 暂时禁用热点监控
    # self.scheduler.add_job(self.daily_hotspot_job, "cron", hour=8)

    # 只启用已有的任务
    self.scheduler.add_job(self.daily_analytics_job, "cron", hour=9)
```

**优点：**
- 快速迁移
- 不影响其他功能

**缺点：**
- 核心功能缺失

**结论：采用选项1**

---

### 3. gstack-browse 外部依赖

**问题描述：**
- `data_collector.py` 依赖 `~/.claude/skills/gstack/bin/gstack-browse`
- ORIG 环境可能没有安装

**影响范围：**
- 数据采集功能完全失败

**解决方案：**

#### 选项1：检查并安装 gstack（推荐）

**迁移前检查脚本：**

```bash
#!/bin/bash
# scripts/check_dependencies.sh

echo "检查 gstack 安装..."
if [ -f "$HOME/.claude/skills/gstack/bin/gstack-browse" ]; then
    echo "✅ gstack 已安装"
else
    echo "❌ gstack 未安装"
    echo "正在安装..."
    cd ~/.claude/skills/gstack && ./setup
fi

echo "检查 media-publish skills..."
for skill in xiaohongshu weibo zhihu; do
    if [ -d "$HOME/.claude/skills/media-publish-$skill" ]; then
        echo "✅ media-publish-$skill 已安装"
    else
        echo "⚠️  media-publish-$skill 未安装"
    fi
done
```

#### 选项2：改用 Playwright 直接调用

**修改 `data_collector.py`：**

```python
from playwright.async_api import async_playwright

class DataCollector:
    async def fetch_page_html(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            html = await page.content()
            await browser.close()
            return html
```

**优点：**
- 不依赖外部脚本
- 更可控

**缺点：**
- 需要重写部分代码（2-3 小时）

**结论：优先选项1，失败时降级到选项2**

---

## ⚠️ 中风险问题（P1 - 建议解决）

### 4. CrewAI 版本差异

**问题：**
- WS: `crewai>=0.86.0`
- ORIG: `crewai>=0.80.0`

**解决方案：**

```bash
cd /c/11projects/Crew
uv add "crewai>=0.86.0"
```

**验证：**

```python
import crewai
print(crewai.__version__)  # 应该 >= 0.86.0
```

---

### 5. 外部 skills 依赖

**问题：**
- `publish_engine.py` 依赖 `~/.claude/skills/media-publish-*`

**解决方案：**

**检查脚本：**

```bash
for skill in xiaohongshu weibo zhihu; do
    if [ ! -d "$HOME/.claude/skills/media-publish-$skill" ]; then
        echo "⚠️  缺少 media-publish-$skill"
        echo "请手动安装或禁用相关发布功能"
    fi
done
```

**降级方案：**

```python
# src/services/publish_engine.py
class PublishEngine:
    def __init__(self):
        self.skills_available = self._check_skills()

    def _check_skills(self) -> dict[str, bool]:
        skills_dir = Path.home() / ".claude" / "skills"
        return {
            "xiaohongshu": (skills_dir / "media-publish-xiaohongshu").exists(),
            "weibo": (skills_dir / "media-publish-weibo").exists(),
            "zhihu": (skills_dir / "media-publish-zhihu").exists(),
        }

    async def publish(self, platform: str, content: dict) -> Result:
        if not self.skills_available.get(platform):
            return error(f"Skill for {platform} not available", "SKILL_NOT_FOUND")
        # ...
```

---

### 6. 同步/异步混用

**问题：**
- WS 的模块大量使用同步操作
- ORIG 是异步架构

**解决方案：**

**统一为异步：**

```python
# 错误示例（WS）
def save_cookie(self, platform: str, cookies: dict):
    with open(f"data/cookies/{platform}.json", "w") as f:
        json.dump(cookies, f)

# 正确示例（ORIG）
async def save_cookie(self, platform: str, cookies: dict) -> Result[None]:
    try:
        async with aiofiles.open(f"data/cookies/{platform}.json", "w") as f:
            await f.write(json.dumps(cookies))
        return success(None)
    except Exception as e:
        return error(f"Failed to save cookie: {e}", "COOKIE_SAVE_ERROR")
```

**需要修改的模块：**
- `cookie_manager.py` - 文件 I/O
- `rate_limiter.py` - 文件 I/O
- `task_queue.py` - 数据库操作
- `data_collector.py` - HTTP 请求

**工作量：4-6 小时**

---

## 📋 迁移前准备工作清单

### 环境检查

```bash
# 运行检查脚本
bash scripts/check_dependencies.sh
```

- [ ] gstack 已安装
- [ ] media-publish skills 已安装（或接受降级）
- [ ] Python 3.11+
- [ ] uv 包管理器

### 依赖安装

```bash
cd /c/11projects/Crew
uv add "apscheduler>=3.10.4"
uv add "crewai>=0.86.0"
uv add "aiofiles>=23.0.0"  # 异步文件 I/O
```

### 数据库备份

```bash
cp /c/11projects/Crew/data/*.db /c/11projects/Crew/data/backup/
```

### Git 准备

```bash
cd /c/11projects/Crew
git checkout main
git pull origin main
git checkout -b feature/workspace-sync
```

---

## ✅ 迁移后验证清单

### 单元测试

```bash
# 新模块测试
pytest tests/unit/test_cookie_manager.py -v
pytest tests/unit/test_rate_limiter.py -v
pytest tests/unit/test_task_queue.py -v
pytest tests/unit/test_scheduler.py -v

# 数据库测试
pytest tests/unit/test_client_service.py -v
pytest tests/unit/test_account_service.py -v
```

### 集成测试

```bash
# 完整流程测试
pytest tests/integration/test_hotspot_workflow.py -v
pytest tests/integration/test_publish_workflow.py -v
```

### 功能验证

**1. Cookie 管理**

```bash
curl -X POST http://localhost:8000/api/cookies/save \
  -H "Content-Type: application/json" \
  -d '{"platform":"xiaohongshu","cookies":{"session":"test"}}'

curl http://localhost:8000/api/cookies/status
```

**2. 任务队列**

```bash
curl -X POST http://localhost:8000/api/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"task_type":"hotspot_detection","payload":{}}'

curl http://localhost:8000/api/tasks/list
```

**3. 调度器**

```bash
curl http://localhost:8000/api/scheduler/jobs
curl http://localhost:8000/api/scheduler/status
```

**4. 数据采集**

```bash
curl -X POST http://localhost:8000/api/data/collect \
  -H "Content-Type: application/json" \
  -d '{"platform":"xiaohongshu","url":"https://www.xiaohongshu.com/explore/xxx"}'
```

**5. 图片生成**

```bash
curl -X POST http://localhost:8000/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{"platform":"xiaohongshu","type":"cover","title":"测试标题"}'
```

### 性能验证

```bash
# 并发测试
ab -n 100 -c 10 http://localhost:8000/api/health

# 响应时间
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/clients
```

### 数据库验证

```bash
# 检查表结构
sqlite3 data/crew.db ".schema clients"
sqlite3 data/crew.db ".schema accounts"
sqlite3 data/crew.db ".schema hot_topics"
sqlite3 data/crew.db ".schema tasks"

# 检查数据
sqlite3 data/crew.db "SELECT COUNT(*) FROM clients;"
```

---

## 🔄 分阶段执行计划

### 阶段 1：基础设施（2 天）

**目标：**
- 数据库层完全迁移到 SQLAlchemy
- 独立模块迁移完成

**任务：**
1. 创建 4 个新 SQLAlchemy 模型
2. 创建 4 个 Service 类
3. 迁移 `cookie_manager`, `rate_limiter`, `retry`
4. 编写单元测试

**验证：**
- [ ] 所有模型测试通过
- [ ] Service 层测试通过
- [ ] 独立模块测试通过

### 阶段 2：核心功能（2 天）

**目标：**
- 任务队列和图片生成可用

**任务：**
1. 重写 `task_queue` 为异步
2. 迁移 `image_generator` 和 API 路由
3. 编写集成测试

**验证：**
- [ ] 任务提交和执行成功
- [ ] 图片生成 API 可用

### 阶段 3：高级功能（3 天）

**目标：**
- 调度器和数据采集可用

**任务：**
1. 创建 `HotspotDetectionCrew`
2. 重写 `data_collector` 为异步
3. 迁移 `scheduler`
4. 迁移 `publish_engine`

**验证：**
- [ ] 调度器启动成功
- [ ] 定时任务触发
- [ ] 数据采集成功
- [ ] 发布流程完整

### 阶段 4：测试和优化（1 天）

**目标：**
- 所有测试通过
- 性能达标

**任务：**
1. 运行全量测试
2. 性能测试和优化
3. 文档更新

**验证：**
- [ ] 测试覆盖率 > 80%
- [ ] API 响应时间 < 200ms
- [ ] 并发测试通过

---

## 📊 工作量估算

| 阶段 | 任务 | 工作量 | 风险 |
|------|------|--------|------|
| 阶段 1 | 数据库迁移 | 13 小时 | 高 |
| 阶段 1 | 独立模块 | 3 小时 | 低 |
| 阶段 2 | 任务队列 | 3 小时 | 中 |
| 阶段 2 | 图片生成 | 2 小时 | 低 |
| 阶段 3 | Crew 创建 | 6 小时 | 中 |
| 阶段 3 | 数据采集 | 4 小时 | 中 |
| 阶段 3 | 调度器 | 3 小时 | 中 |
| 阶段 3 | 发布引擎 | 2 小时 | 低 |
| 阶段 4 | 测试 | 6 小时 | 低 |
| 阶段 4 | 优化 | 2 小时 | 低 |
| **总计** | | **44 小时** | |

**预计时间：6-8 个工作日**

---

## 🚀 快速开始

```bash
# 1. 运行依赖检查
bash scripts/check_dependencies.sh

# 2. 创建迁移分支
cd /c/11projects/Crew
git checkout main
git pull origin main
git checkout -b feature/workspace-sync

# 3. 安装新依赖
uv add "apscheduler>=3.10.4" "crewai>=0.86.0" "aiofiles>=23.0.0"

# 4. 备份数据库
mkdir -p data/backup
cp data/*.db data/backup/

# 5. 开始阶段 1
# 参考 docs/DATABASE-REWRITE-GUIDE.md
```
