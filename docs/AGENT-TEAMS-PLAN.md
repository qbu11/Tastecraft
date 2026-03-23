# Agent Teams 迁移执行方案

> 使用 agent teams 并行执行 workspace → ORIG 迁移

## 团队架构

### Team Lead (你)
- 协调各 agent 工作
- 审查关键决策
- 处理冲突和阻塞

### Agent 分工

#### Agent 1: Database Architect
**职责：** 数据库层迁移
- 创建 4 个 SQLAlchemy 模型（Client, Account, HotTopic, Task）
- 创建 4 个 Service 层（ClientService, AccountService, MetricsService, TaskQueue）
- 创建 Alembic 迁移
- 编写数据库测试

**输入文档：**
- `docs/DATABASE-REWRITE-GUIDE.md`
- `SYNC-PLAN.md` Phase 2.1

**输出：**
- `src/models/client.py`
- `src/models/account.py`
- `src/models/hot_topic.py`
- `src/models/task.py`
- `src/services/client_service.py`
- `src/services/account_service.py`
- `src/services/metrics_service.py`
- `src/services/task_queue.py`
- `migrations/versions/xxx_add_workspace_tables.py`
- `tests/unit/test_*_service.py`

**预计时间：** 2 天

---

#### Agent 2: Module Migrator
**职责：** 独立模块迁移
- 迁移 cookie_manager, rate_limiter, retry
- 适配 import 路径
- 改为异步 I/O
- 补充类型注解
- 编写单元测试

**输入文档：**
- `SYNC-PLAN.md` Phase 1.1-1.3
- `scripts/sync_workspace.py`

**输出：**
- `src/services/cookie_manager.py`
- `src/services/rate_limiter.py`
- `src/utils/retry.py`
- `tests/unit/test_cookie_manager.py`
- `tests/unit/test_rate_limiter.py`
- `tests/unit/test_retry.py`

**预计时间：** 1 天

---

#### Agent 3: API Developer
**职责：** API 路由和 Schema
- 创建 clients, accounts 路由
- 创建对应的 Pydantic Schema
- 迁移 image_router
- 注册路由到 main.py
- 编写 API 测试

**输入文档：**
- `SYNC-PLAN.md` Phase 2.2
- ORIG 的路由范式（`src/api/routes/health.py` 作为参考）

**输出：**
- `src/api/routes/clients.py`
- `src/api/routes/accounts.py`
- `src/api/routes/images.py`
- `src/schemas/client.py`
- `src/schemas/account.py`
- `tests/unit/test_clients.py`
- `tests/unit/test_accounts.py`
- `tests/unit/test_image_router.py`

**预计时间：** 1.5 天

---

#### Agent 4: Crew Builder
**职责：** 创建缺失的 Crew
- 创建 HotspotDetectionCrew
- 基于 ORIG 的 BaseCrew 架构
- 对接 ORIG 的 Agent 和 Tool 体系
- 编写 Crew 测试

**输入文档：**
- `docs/MIGRATION-RISKS.md` 中的 HotspotDetectionCrew 示例
- ORIG 的 `src/crew/crews/base_crew.py`
- ORIG 的 `src/crew/crews/content_crew.py` 作为参考

**输出：**
- `src/crew/crews/hotspot_crew.py`
- `tests/integration/test_hotspot_crew.py`

**预计时间：** 1 天

---

#### Agent 5: Scheduler & Collector
**职责：** 调度器和数据采集
- 迁移 scheduler.py（改用 Service 层）
- 迁移 data_collector.py（改为异步 + SQLAlchemy）
- 迁移 publish_engine_v2.py
- 集成调度器到 FastAPI lifespan
- 编写集成测试

**输入文档：**
- `SYNC-PLAN.md` Phase 1.5-1.7
- `docs/DATABASE-REWRITE-GUIDE.md` 步骤 4（scheduler 示例）

**输出：**
- `src/services/scheduler.py`
- `src/services/data_collector.py`
- `src/services/publish_engine_v2.py`
- 修改 `src/api/main.py`（lifespan）
- `tests/integration/test_scheduler.py`
- `tests/integration/test_data_collector.py`

**预计时间：** 2 天

---

#### Agent 6: QA Engineer
**职责：** 测试和验证
- 运行全量测试
- 类型检查（mypy strict）
- 代码风格检查（ruff）
- 性能测试
- 功能验证
- 生成测试报告

**输入文档：**
- `docs/QUICKSTART-MIGRATION.md` 阶段 4
- `docs/MIGRATION-RISKS.md` 验证清单

**输出：**
- 测试报告（覆盖率、通过率）
- 类型检查报告
- 性能测试报告
- Bug 列表（如有）

**预计时间：** 1 天

---

## 执行流程

### Phase 1: 准备（并行）

```
Team Lead: 运行 pre_migration_check.py
Team Lead: 创建迁移分支 feature/workspace-sync
Team Lead: 备份数据库

Agent 1: 阅读 DATABASE-REWRITE-GUIDE.md
Agent 2: 阅读 SYNC-PLAN.md Phase 1
Agent 3: 阅读 SYNC-PLAN.md Phase 2.2
Agent 4: 阅读 ORIG 的 BaseCrew 架构
Agent 5: 阅读 SYNC-PLAN.md Phase 1.5-1.7
Agent 6: 准备测试环境
```

### Phase 2: 基础设施（2 天）

**并行任务：**
- Agent 1: 创建 SQLAlchemy 模型 + Service 层
- Agent 2: 迁移独立模块（cookie_manager, rate_limiter, retry）

**依赖关系：**
- Agent 1 完成后 → Agent 5 可以开始（scheduler 依赖 Service 层）

**提交：**
```bash
git add src/models/ src/services/client_service.py src/services/account_service.py src/services/metrics_service.py
git commit -m "feat(stage1): add SQLAlchemy models and service layer"

git add src/services/cookie_manager.py src/services/rate_limiter.py src/utils/retry.py
git commit -m "feat(stage1): add independent modules"
```

### Phase 3: 核心功能（1.5 天）

**并行任务：**
- Agent 1: 重写 TaskQueue 为异步
- Agent 3: 创建 API 路由和 Schema
- Agent 4: 创建 HotspotDetectionCrew

**提交：**
```bash
git add src/services/task_queue.py
git commit -m "feat(stage2): rewrite task queue to async SQLAlchemy"

git add src/api/routes/ src/schemas/
git commit -m "feat(stage2): add client/account/image API routes"

git add src/crew/crews/hotspot_crew.py
git commit -m "feat(stage2): add HotspotDetectionCrew"
```

### Phase 4: 高级功能（2 天）

**串行任务（依赖 Phase 2 完成）：**
- Agent 5: 迁移 scheduler, data_collector, publish_engine_v2

**提交：**
```bash
git add src/services/scheduler.py src/services/data_collector.py src/services/publish_engine_v2.py src/api/main.py
git commit -m "feat(stage3): add scheduler and data collection"
```

### Phase 5: 测试和优化（1 天）

**串行任务（依赖所有功能完成）：**
- Agent 6: 运行全量测试和验证

**提交：**
```bash
git add tests/
git commit -m "test(stage4): add comprehensive test suite"

git add docs/
git commit -m "docs(stage4): update documentation"
```

### Phase 6: 合并和部署

**Team Lead：**
- 审查所有提交
- 创建 PR
- 合并到 main

---

## 通信协议

### Agent → Team Lead

**进度报告：**
```
Agent X: [PROGRESS] 已完成 Y/Z 任务
Agent X: [BLOCKED] 遇到问题：...
Agent X: [QUESTION] 需要决策：...
Agent X: [DONE] 任务完成，输出：...
```

**决策请求：**
```
Agent X: [DECISION NEEDED]
问题：...
选项 A：...
选项 B：...
推荐：...
```

### Team Lead → Agent

**任务分配：**
```
@Agent X: 开始任务 Y
输入：...
输出：...
截止时间：...
```

**决策反馈：**
```
@Agent X: 采用选项 A，原因：...
```

**阻塞解除：**
```
@Agent X: 问题已解决，继续执行
```

---

## 风险管理

### 阻塞场景

**场景 1：Agent 1 发现数据库迁移比预期复杂**
- **应对：** Team Lead 评估是否需要调整 Phase 2 时间线
- **备选方案：** 简化部分功能，先完成核心表

**场景 2：Agent 4 发现 ORIG 的 Crew 架构与预期不符**
- **应对：** Team Lead 与 Agent 4 讨论，调整 HotspotDetectionCrew 设计
- **备选方案：** 暂时禁用 scheduler 中的热点监控任务

**场景 3：Agent 5 发现 gstack-browse 不存在**
- **应对：** Team Lead 决定是否安装或改用 Playwright
- **备选方案：** data_collector 降级为 HTTP 抓取

**场景 4：Agent 6 发现大量测试失败**
- **应对：** Team Lead 召集相关 Agent 修复
- **备选方案：** 标记失败测试为 @pytest.mark.skip，后续修复

---

## 成功标准

- [ ] 所有 Agent 任务完成
- [ ] 所有提交通过 CI
- [ ] 测试覆盖率 > 80%
- [ ] mypy strict 通过
- [ ] ruff check 通过
- [ ] 所有功能验证通过
- [ ] PR 合并到 main

---

## 启动命令

```bash
# 1. 创建团队
/team create crew-migration "Workspace to ORIG migration team"

# 2. 启动 6 个 agents（并行）
# Agent 1: Database Architect
# Agent 2: Module Migrator
# Agent 3: API Developer
# Agent 4: Crew Builder
# Agent 5: Scheduler & Collector
# Agent 6: QA Engineer

# 3. Team Lead 监控进度
/team status
/team tasks

# 4. 处理阻塞和决策
# 根据 agent 报告做出决策

# 5. 完成后清理
/team shutdown
```

---

## 预计总时间

| Phase | 时间 | 并行度 |
|-------|------|--------|
| Phase 1: 准备 | 1 小时 | 全员 |
| Phase 2: 基础设施 | 2 天 | Agent 1, 2 |
| Phase 3: 核心功能 | 1.5 天 | Agent 1, 3, 4 |
| Phase 4: 高级功能 | 2 天 | Agent 5 |
| Phase 5: 测试优化 | 1 天 | Agent 6 |
| Phase 6: 合并部署 | 2 小时 | Team Lead |

**总计：5.5 天（实际日历时间，考虑并行）**

相比单人执行的 6-8 天，agent teams 可以节省 1-2.5 天。
