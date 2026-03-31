# Crew Media Ops — 开发进度

> 项目开发里程碑和当前状态追踪。

---

## 当前版本：v1.2

### 最新进展（2026-03-31）

**Taste Onboarding 系统**
- OnboardingAgent：6 步引导流程（领域/调性/平台/长度/开场/避免）
- API 端点：`/api/v1/onboarding/*`（start、answer、taste-prompt）
- TasteEngine 集成：偏好自动注入内容生成流程
- 置信度系统：基于信号数量计算各维度置信度

**4-Subagent 工作流**
- ContentOrchestrator 编排 4 个子 Agent 顺序执行
- Researcher → Marketer → Copywriter → Designer
- CallbackHandler 通过 WebSocket 实时推送执行状态
- 前端 SubagentWorkflow 组件可视化工作流进度

**前端 Dashboard**
- React + Vite + TailwindCSS
- 12 个页面：Dashboard、Crews、Content Create、Drafts、Review、Analytics、Agents、Publish、Search、Clients、Images、Tasks
- WebSocket 实时状态更新
- Zustand 状态管理

---

## 里程碑

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

- [ ] Onboarding 前端页面（OnboardingPage.tsx）
- [ ] 稿件反馈闭环（approve/reject → TasteEngine 学习）
- [ ] 数据分析 Agent 真实数据采集
- [ ] PostgreSQL 迁移
- [ ] 多用户/多账号支持
