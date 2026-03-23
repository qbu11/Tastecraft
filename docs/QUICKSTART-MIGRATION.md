# 快速开始：迁移执行指南

> 按照此指南逐步执行迁移，确保每个步骤都正确完成

## 📋 迁移前检查清单

### 1. 运行环境检查脚本

```bash
cd /c/11projects/Crew
python scripts/pre_migration_check.py
```

**必须通过的检查：**
- ✅ Python >= 3.11
- ✅ Git 工作区干净（或已提交）
- ✅ 核心依赖已安装（crewai, fastapi, sqlalchemy）
- ✅ WS 源文件完整

**可选检查（失败时有降级方案）：**
- ⚠️ gstack-browse（数据采集需要）
- ⚠️ media-publish skills（发布需要）

### 2. 阅读风险文档

```bash
# 在编辑器中打开
code docs/MIGRATION-RISKS.md
```

**重点关注：**
- 🚨 P0 风险：数据库不兼容、缺失 Crew、外部依赖
- ⚠️ P1 风险：版本差异、同步/异步混用
- 📊 工作量估算：44 小时（6-8 天）

### 3. 备份数据和代码

```bash
# 备份数据库
mkdir -p data/backup
cp data/*.db data/backup/

# 备份当前代码（可选）
git stash push -m "backup before migration"
```

### 4. 创建迁移分支

```bash
# 切换到 main 分支
git checkout main
git pull origin main

# 创建迁移分支
git checkout -b feature/workspace-sync

# 提交当前未跟踪的文件
git add SYNC-PLAN.md docs/ scripts/
git commit -m "docs: add migration planning documents

- Add SYNC-PLAN.md for workspace sync strategy
- Add MIGRATION-RISKS.md for risk assessment
- Add DATABASE-REWRITE-GUIDE.md for database migration
- Add pre_migration_check.py for environment validation

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 🚀 阶段 1：基础设施（2 天）

### 目标
- 数据库层完全迁移到 SQLAlchemy
- 独立模块迁移完成

### 步骤 1.1：安装新依赖

```bash
cd /c/11projects/Crew

# 添加新依赖
uv add "apscheduler>=3.10.4"
uv add "aiofiles>=23.0.0"

# 升级 crewai
uv add "crewai>=0.86.0"

# 验证安装
python -c "import apscheduler; print(apscheduler.__version__)"
python -c "import aiofiles; print('aiofiles installed')"
python -c "import crewai; print(crewai.__version__)"
```

### 步骤 1.2：创建 SQLAlchemy 模型

**参考：[DATABASE-REWRITE-GUIDE.md](docs/DATABASE-REWRITE-GUIDE.md)**

```bash
# 创建 4 个新模型
touch src/models/client.py
touch src/models/account.py
touch src/models/hot_topic.py
touch src/models/task.py
```

**复制以下代码到对应文件：**

1. `src/models/client.py` - 见 DATABASE-REWRITE-GUIDE.md
2. `src/models/account.py` - 见 DATABASE-REWRITE-GUIDE.md
3. `src/models/hot_topic.py` - 见 SYNC-PLAN.md Phase 2.1
4. `src/models/task.py` - 见 DATABASE-REWRITE-GUIDE.md 步骤 1.1

**更新 `src/models/__init__.py`：**

```python
# 添加新模型导入
from src.models.client import Client
from src.models.account import Account, AccountStatus
from src.models.hot_topic import HotTopic
from src.models.metrics import Metrics
from src.models.task import Task, TaskStatus

# 添加到 __all__
__all__ = [
    # ... 现有的 ...
    "Client",
    "Account",
    "AccountStatus",
    "HotTopic",
    "Metrics",
    "Task",
    "TaskStatus",
]
```

### 步骤 1.3：创建数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "add workspace tables (client, account, hot_topic, task, metrics)"

# 检查生成的迁移文件
ls migrations/versions/

# 应用迁移
alembic upgrade head

# 验证表结构
sqlite3 data/crew.db ".schema clients"
sqlite3 data/crew.db ".schema accounts"
sqlite3 data/crew.db ".schema hot_topics"
sqlite3 data/crew.db ".schema tasks"
sqlite3 data/crew.db ".schema metrics"
```

### 步骤 1.4：创建 Service 层

```bash
# 创建 4 个 Service 类
touch src/services/client_service.py
touch src/services/account_service.py
touch src/services/metrics_service.py
touch src/services/task_queue.py
```

**复制代码：**
- `client_service.py` - 见 DATABASE-REWRITE-GUIDE.md 步骤 2.1
- `account_service.py` - 见 DATABASE-REWRITE-GUIDE.md 步骤 2.2
- `metrics_service.py` - 见 DATABASE-REWRITE-GUIDE.md 步骤 2.3
- `task_queue.py` - 见 DATABASE-REWRITE-GUIDE.md 步骤 3

### 步骤 1.5：迁移独立模块

```bash
# 运行同步脚本（仅独立模块）
python scripts/sync_workspace.py --dry-run

# 确认无误后执行
python scripts/sync_workspace.py
```

**手动适配（脚本无法自动处理的部分）：**

1. **cookie_manager.py**
   - 改为异步文件 I/O（使用 aiofiles）
   - 补充类型注解
   - 添加 Result[T] 返回类型

2. **rate_limiter.py**
   - 改为异步文件 I/O
   - 补充类型注解

3. **retry.py**
   - 检查是否与 ORIG 的 `error_handling.py` 冲突
   - 如冲突，考虑直接使用 tenacity

### 步骤 1.6：提交阶段 1

```bash
git add src/models/ src/services/ migrations/
git commit -m "feat(stage1): add SQLAlchemy models and service layer

- Add Client, Account, HotTopic, Task, Metrics models
- Add ClientService, AccountService, MetricsService
- Rewrite TaskQueue to async SQLAlchemy
- Add database migration

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

git add src/services/cookie_manager.py src/services/rate_limiter.py src/utils/retry.py
git commit -m "feat(stage1): add independent modules

- Add cookie_manager for multi-platform auth
- Add rate_limiter for publish frequency control
- Add retry decorator with exponential backoff

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

### 步骤 1.7：编写测试

```bash
# 创建测试文件
touch tests/unit/test_client_service.py
touch tests/unit/test_account_service.py
touch tests/unit/test_task_queue.py
touch tests/unit/test_cookie_manager.py
touch tests/unit/test_rate_limiter.py

# 运行测试
pytest tests/unit/test_client_service.py -v
pytest tests/unit/test_account_service.py -v
pytest tests/unit/test_task_queue.py -v
```

**阶段 1 验证清单：**
- [ ] 所有模型测试通过
- [ ] Service 层测试通过
- [ ] 独立模块测试通过
- [ ] 数据库迁移成功
- [ ] 无 sqlite3 原生调用残留

---

## 🔧 阶段 2：核心功能（2 天）

### 目标
- 任务队列和图片生成可用

### 步骤 2.1：迁移 image_generator

```bash
# 复制 image_generator 工具
cp /c/Users/puzzl/metabot_workspace/crew-hotspot/src/crew_hotspot/tools/image_generator.py \
   src/tools/image_generator.py

# 适配 import
sed -i 's/from crew_hotspot\./from src./g' src/tools/image_generator.py
sed -i 's/from src\.image_generator/from src.services.image_generator/g' src/tools/image_generator.py

# 添加 image_generator service（如果还没有）
git add src/services/image_generator.py
```

### 步骤 2.2：迁移 image API 路由

```bash
# 复制路由文件
cp /c/Users/puzzl/metabot_workspace/crew-hotspot/src/crew_hotspot/api_routes/image_router.py \
   src/api/routes/images.py

# 适配 import
sed -i 's/from crew_hotspot\./from src./g' src/api/routes/images.py
sed -i 's/from src\.api_routes\./from src.api.routes./g' src/api/routes/images.py
```

**手动修改 `src/api/routes/images.py`：**

```python
# 修改路由定义
router = APIRouter(prefix="/images", tags=["Images"])

# 修改返回类型
async def generate_image(...) -> dict[str, Any]:
    ...
```

**注册路由到 `src/api/main.py`：**

```python
from src.api.routes import health, content, tasks, analytics, dashboard, research, search, images

app.include_router(images.router)
```

### 步骤 2.3：测试图片生成

```bash
# 启动服务
uvicorn src.api.main:app --reload &

# 测试 API
curl -X POST http://localhost:8000/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{"platform":"xiaohongshu","type":"cover","title":"测试标题"}'

# 查看 API 文档
open http://localhost:8000/docs
```

### 步骤 2.4：提交阶段 2

```bash
git add src/tools/image_generator.py src/api/routes/images.py src/api/main.py
git commit -m "feat(stage2): add image generation API

- Add image_generator tool for CrewAI
- Add /api/images routes for image generation
- Support xiaohongshu, weibo, zhihu platforms

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

**阶段 2 验证清单：**
- [ ] 图片生成 API 可用
- [ ] 任务队列提交和执行成功
- [ ] 集成测试通过

---

## 🎯 阶段 3：高级功能（3 天）

### 目标
- 调度器和数据采集可用

### 步骤 3.1：创建 HotspotDetectionCrew

```bash
touch src/crew/crews/hotspot_crew.py
```

**参考 MIGRATION-RISKS.md 中的示例代码**

### 步骤 3.2：迁移 data_collector

```bash
# 检查 gstack-browse 是否存在
ls ~/.claude/skills/gstack/bin/gstack-browse

# 如果不存在，安装
cd ~/.claude/skills/gstack && ./setup

# 复制 data_collector
cp /c/Users/puzzl/metabot_workspace/crew-hotspot/src/crew_hotspot/data_collector.py \
   src/services/data_collector.py

# 适配 import 和数据库调用
# 手动修改：使用 MetricsService 替代 WS 的 MetricsManager
```

### 步骤 3.3：迁移 scheduler

```bash
cp /c/Users/puzzl/metabot_workspace/crew-hotspot/src/crew_hotspot/scheduler.py \
   src/services/scheduler.py

# 手动修改：
# 1. 使用 Service 层替代 Manager
# 2. 调用新创建的 HotspotDetectionCrew
# 3. 改为异步
```

**集成到 `src/api/main.py`：**

```python
from contextlib import asynccontextmanager
from src.services.scheduler import HotspotScheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    scheduler = HotspotScheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    yield

    # 关闭时
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()

app = FastAPI(
    title="Crew Media Ops API",
    version="0.1.0",
    lifespan=lifespan,
)
```

### 步骤 3.4：迁移 publish_engine

```bash
# 检查 media-publish skills
for skill in xiaohongshu weibo zhihu; do
    ls ~/.claude/skills/media-publish-$skill
done

# 复制 publish_engine_v2
cp /c/Users/puzzl/metabot_workspace/crew-hotspot/src/crew_hotspot/publish_engine_v2.py \
   src/services/publish_engine_v2.py

# 适配 import
```

### 步骤 3.5：提交阶段 3

```bash
git add src/crew/crews/hotspot_crew.py
git commit -m "feat(stage3): add HotspotDetectionCrew

- Add hotspot detection workflow
- Integrate with platform search tools

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

git add src/services/data_collector.py src/services/scheduler.py src/services/publish_engine_v2.py
git commit -m "feat(stage3): add scheduler and data collection

- Add HotspotScheduler with APScheduler
- Add DataCollector with Chrome MCP integration
- Add PublishEngineV2 for native publishing
- Integrate scheduler into FastAPI lifespan

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

**阶段 3 验证清单：**
- [ ] 调度器启动成功
- [ ] 定时任务触发
- [ ] 数据采集成功
- [ ] 发布流程完整

---

## ✅ 阶段 4：测试和优化（1 天）

### 步骤 4.1：运行全量测试

```bash
# 运行所有测试
pytest tests/ -v

# 检查覆盖率
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 步骤 4.2：类型检查

```bash
# 检查新增文件
mypy src/services/cookie_manager.py --strict
mypy src/services/rate_limiter.py --strict
mypy src/services/task_queue.py --strict
mypy src/services/scheduler.py --strict
mypy src/services/data_collector.py --strict
mypy src/services/publish_engine_v2.py --strict
mypy src/api/routes/images.py --strict

# 检查所有文件
mypy src/ --strict
```

### 步骤 4.3：代码风格检查

```bash
ruff check src/services/ src/api/routes/ src/models/ src/schemas/
```

### 步骤 4.4：性能测试

```bash
# 启动服务
uvicorn src.api.main:app --reload &

# 并发测试
ab -n 100 -c 10 http://localhost:8000/api/health

# 响应时间测试
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/clients
```

### 步骤 4.5：更新文档

```bash
# 更新 README.md
# 更新 CLAUDE.md
# 更新 API 文档
```

### 步骤 4.6：最终提交

```bash
git add tests/ docs/
git commit -m "test(stage4): add comprehensive test suite

- Add unit tests for all new modules
- Add integration tests for workflows
- Achieve 80%+ test coverage

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

git add README.md CLAUDE.md docs/
git commit -m "docs(stage4): update documentation

- Update README with new features
- Update CLAUDE.md with architecture changes
- Add API documentation

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

**阶段 4 验证清单：**
- [ ] 测试覆盖率 > 80%
- [ ] mypy strict 通过
- [ ] ruff check 通过
- [ ] API 响应时间 < 200ms
- [ ] 并发测试通过
- [ ] 文档更新完成

---

## 🎉 阶段 5：合并和部署

### 步骤 5.1：推送分支

```bash
git push origin feature/workspace-sync
```

### 步骤 5.2：创建 PR

```bash
gh pr create --title "feat: sync workspace modules (8 core modules + database migration)" \
  --body "$(cat <<'EOF'
## Summary
完成 workspace/crew-hotspot 到 ORIG 的功能迁移，包含：

### 新增功能
- ✅ Cookie 管理器（多平台认证）
- ✅ 限流器（发布频率控制）
- ✅ 任务队列（异步任务管理）
- ✅ 调度器（自动化工作流）
- ✅ 数据采集器（Chrome MCP 集成）
- ✅ 图片生成 API
- ✅ 客户/账号管理

### 架构变更
- 🔄 数据库从 sqlite3 迁移到 SQLAlchemy
- 🔄 所有数据库操作改为异步
- 🔄 新增 4 个 SQLAlchemy 模型
- 🔄 新增 4 个 Service 层

### Breaking Changes
- ⚠️ 数据库架构变更（需要运行 alembic upgrade）
- ⚠️ 所有数据库操作现在是异步的

## Test Plan
- [x] 运行全量测试（284 + 76 = 360 个测试）
- [x] 测试覆盖率 > 80%
- [x] mypy strict 通过
- [x] ruff check 通过
- [x] 性能测试通过
- [x] Cookie 管理功能验证
- [x] 限流器功能验证
- [x] 任务队列功能验证
- [x] 调度器功能验证
- [x] 数据采集功能验证
- [x] 图片生成功能验证

## Migration Guide
详见：
- [SYNC-PLAN.md](SYNC-PLAN.md)
- [MIGRATION-RISKS.md](docs/MIGRATION-RISKS.md)
- [DATABASE-REWRITE-GUIDE.md](docs/DATABASE-REWRITE-GUIDE.md)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### 步骤 5.3：Code Review

等待 Code Review 通过后合并。

### 步骤 5.4：合并到 main

```bash
# 合并 PR 后
git checkout main
git pull origin main

# 删除本地分支
git branch -d feature/workspace-sync
```

### 步骤 5.5：部署验证

```bash
# 在生产环境运行迁移
alembic upgrade head

# 重启服务
systemctl restart crew-media-ops

# 验证服务状态
curl http://localhost:8000/api/health
curl http://localhost:8000/api/scheduler/status
```

---

## 🆘 故障排查

### 问题 1：数据库迁移失败

```bash
# 回滚迁移
alembic downgrade -1

# 检查迁移文件
cat migrations/versions/xxx_add_workspace_tables.py

# 手动修复后重新应用
alembic upgrade head
```

### 问题 2：gstack-browse 不存在

```bash
# 安装 gstack
cd ~/.claude/skills/gstack
./setup

# 验证
~/.claude/skills/gstack/bin/gstack-browse --help
```

### 问题 3：测试失败

```bash
# 查看详细错误
pytest tests/unit/test_xxx.py -vv

# 单独运行失败的测试
pytest tests/unit/test_xxx.py::TestClass::test_method -vv

# 检查 fixture
pytest --fixtures tests/
```

### 问题 4：类型检查失败

```bash
# 查看详细错误
mypy src/services/xxx.py --strict --show-error-codes

# 常见问题：
# - 缺少类型注解：添加 -> Result[T]
# - Optional 写法：改为 X | None
# - 缺少 import：添加 from typing import Any
```

---

## 📚 参考文档

- [SYNC-PLAN.md](SYNC-PLAN.md) - 完整同步计划
- [MIGRATION-RISKS.md](docs/MIGRATION-RISKS.md) - 风险评估与缓解
- [DATABASE-REWRITE-GUIDE.md](docs/DATABASE-REWRITE-GUIDE.md) - 数据库重写指南
- [pre_migration_check.py](scripts/pre_migration_check.py) - 环境检查脚本
- [sync_workspace.py](scripts/sync_workspace.py) - 自动同步脚本

---

## 💡 最佳实践

1. **小步提交**：每完成一个模块就提交，便于回滚
2. **先测试后提交**：确保每次提交都能通过测试
3. **保持沟通**：遇到问题及时记录和讨论
4. **备份数据**：每个阶段开始前备份数据库
5. **验证功能**：每个阶段结束后验证功能完整性

---

## ✨ 完成标志

当以下所有项都完成时，迁移即告成功：

- [ ] 所有 8 个核心模块迁移完成
- [ ] 数据库完全迁移到 SQLAlchemy
- [ ] 所有测试通过（360+ 个）
- [ ] 测试覆盖率 > 80%
- [ ] mypy strict 通过
- [ ] ruff check 通过
- [ ] 所有功能验证通过
- [ ] 文档更新完成
- [ ] PR 合并到 main
- [ ] 生产环境部署成功

**预计完成时间：6-8 个工作日**

🎉 恭喜完成迁移！
