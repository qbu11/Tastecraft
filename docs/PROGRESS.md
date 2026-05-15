# TasteCraft — 开发进度

> 项目开发里程碑和当前状态追踪。

---

## 当前版本：v2.0 — TasteCraft Self-Use Edition

### 最新进展（2026-04-13）

**架构转型：Multi-Agent → Single Agent + Multi Tool**
- 放弃 CrewAI 多 Agent 架构，改用 Anthropic SDK agent loop
- CLI-first（Typer + Rich），砍掉 Web Dashboard
- 单用户多 Project 隔离，SQLite 持久化
- 五条自动化 Pipeline：Content / Publish / Analytics / Evolution / Trending

**TasteCraft Self-Use Edition 已完成 Phase 1-6**
- Phase 1: Foundation — CLI skeleton + agent loop + project management
- Phase 2: Content Pipeline — 生成 + 审核 + REPL 交互模式
- Phase 3: Publish Pipeline — 小红书 + 微信公众号发布工具
- Phase 4: Analytics + Evolution — 数据收集 + 品味进化 + 调度
- Phase 5: CLI Polish — run/schedule/daemon 命令 + trending pipeline
- Phase 6: Search Enhancement — 搜索鲁棒性、平台修复、daemon、REPL、测试

**代码结构（`src/tastecraft/`）**
- `cli/` — Typer CLI 入口 + REPL + 子命令（generate/publish/project/taste/daemon/run/schedule）
- `core/` — agent_loop、config、logging
- `pipelines/` — content、publish、analytics、evolution、trending
- `tools/` — search、content、notification、platform（xiaohongshu/wechat）
- `taste/` — profile、prompt_builder
- `models/` — SQLite 表定义
- `services/` — scheduler

**Bug 修复**
- daemon base_dir → home_dir 路径修复
- agent_loop API 错误处理
- 搜索部分结果返回 + RSS 超时 + feedparser 依赖
- Publish→Analytics→Evolution 数据管道疏通
- AdaptPlatformTool body 校验边界情况

---

## 里程碑

### v2.0 — TasteCraft Self-Use Edition（2026-04-13）✅

| 功能 | 状态 |
|------|------|
| Phase 1: CLI skeleton + agent loop + project mgmt | ✅ 完成 |
| Phase 2: Content Pipeline + REPL | ✅ 完成 |
| Phase 3: Publish Pipeline（XHS + WeChat） | ✅ 完成 |
| Phase 4: Analytics + Evolution + Scheduling | ✅ 完成 |
| Phase 5: CLI polish + daemon + trending | ✅ 完成 |
| Phase 6: Search enhancement + platform fixes | ✅ 完成 |
| 数据管道疏通（Publish→Analytics→Evolution） | ✅ 修复 |
| Daemon 路径 + agent_loop 错误处理 | ✅ 修复 |
| 搜索鲁棒性（partial results, RSS timeout） | ✅ 修复 |

### v1.2 — Taste + Workflow（2026-03-31）✅

| 功能 | 状态 |
|------|------|
| OnboardingAgent 引导流程 | ✅ 完成 |
| TasteEngine 三因素计算 | ✅ 完成 |
| ContentOrchestrator 4-agent 编排 | ✅ 完成 |
| CallbackHandler WS 事件 | ✅ 完成 |
| SubagentWorkflow 前端组件 | ✅ 完成 |
| 文档整理归档 | ✅ 完成 |

### v1.1 — 平台自动化（2026-03-28）✅

| 功能 | 状态 |
|------|------|
| 微博 Playwright CDP 发布 | ✅ 26 tests |
| 知乎 CDP 发布（回答/文章/想法） | ✅ 27 tests |
| 抖音 CDP 发布（视频上传） | ✅ 25 tests |
| B站 CDP 发布（视频+分区） | ✅ 22 tests |
| 定时调度 REST API | ✅ 12 tests |
| BasePlatformTool 通用方法 | ✅ 完成 |

### v1.0 — 基础架构（2026-03-20）✅

| 功能 | 状态 |
|------|------|
| CrewAI Agent 框架 | ✅ 完成 |
| FastAPI 后端 | ✅ 完成 |
| 小红书/微信发布 | ✅ 完成 |
| SQLite 持久化 | ✅ 完成 |
| CLI 工具（Typer） | ✅ 完成 |
| 基础测试覆盖 | ✅ 138 tests |

---

## 待开发

- [ ] 端到端实际运行验证（真实 API key + 真实平台 cookie）
- [ ] 多 Project 并行运行测试
- [ ] Cron 调度生产环境验证
- [ ] 品味进化效果评估（Evolution Pipeline 实际反馈循环）
- [ ] 更多平台支持（微博、知乎、抖音、B站 → TasteCraft 架构适配）
- [ ] PostgreSQL 迁移（当 SQLite 不够用时）
- [ ] 内容质量评分自动化（替代人工审核）
