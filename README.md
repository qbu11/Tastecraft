# Crew Media Ops

> 基于 CrewAI 的自媒体运营 Multi-Agent 系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.80+-orange.svg)](https://www.crewai.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 简介

Crew Media Ops 是一套全自动化的自媒体运营系统，通过多 Agent 协作实现从选题策划、内容创作、多平台发布到数据分析的全链路自动化。

### 核心能力

| 能力 | 说明 |
|------|------|
| **内容生产** | 选题研究 → AI 创作智能协作 → 人工审核 |
| **多平台发布** | 一键适配 6 大平台，支持定时发布 |
| **数据分析** | 自动采集数据，生成效果报告和优化建议 |
| **批量生产** | 给定选题/素材，自动生成多平台适配内容 |

### 支持平台

#### 国内平台

| 平台 | 内容类型 | 发布方式 |
|------|---------|---------|
| 小红书 | 图文笔记、视频笔记 | Chrome CDP |
| 微信公众号 | 文章、图文消息 | API + Chrome CDP |
| 微博 | 微博、头条文章 | Chrome CDP |
| 知乎 | 回答、文章、想法 | Chrome CDP |
| 抖音 | 短视频 | Chrome CDP |
| B站 | 视频、专栏 | Chrome CDP |

#### 海外平台

| 平台 | 内容类型 | 发布方式 |
|------|---------|---------|
| Reddit | Post, Comment, Image | PRAW SDK（推荐）/ Chrome CDP |
| X (Twitter) | Tweet, Thread, Image | Tweepy SDK（推荐）/ Chrome CDP |
| Facebook | Post, Image, Video | facebook-sdk（Graph API） |
| Instagram | Post, Reel, Carousel, Story | instagrapi SDK（推荐）/ Graph API |
| Threads | Text, Image, Video | threadspipepy SDK（Threads API） |

> 海外平台优先使用成熟开源 SDK，Chrome CDP 作为 fallback。安装 SDK 依赖：`uv sync --extra overseas`

---

## 运行机制

### 1. 热点追踪与选题研究

```
┌─────────────────────────────────────────────────────────────┐
│                    TopicResearcher Agent                    │
├─────────────────────────────────────────────────────────────┤
│  输入: 行业/领域、关键词                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ HotSearchTool — 跨平台热搜采集                        │    │
│  │ • 微博热搜、抖音热点、小红书趋势、知乎热榜            │    │
│  │ • 数据源: TikHub API / Chrome CDP 爬取               │    │
│  │ • 缓存策略: 10 分钟 TTL，避免频繁请求                │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ CompetitorAnalysisTool — 竞品分析                    │    │
│  │ • 账号内容采集、互动数据分析                          │    │
│  │ • 高赞内容特征提取                                    │    │
│  │ • 最佳发布时间分析                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ TrendAnalysisTool — 趋势预测                         │    │
│  │ • 关键词热度趋势 (24h/7d/30d)                        │    │
│  │ • 上升/下降/稳定 判断                                │    │
│  │ • 相关话题推荐                                        │    │
│  └─────────────────────────────────────────────────────┘    │
│  输出: 选题报告 (热点话题 + 竞品分析 + 趋势预测)               │
└─────────────────────────────────────────────────────────────┘
```

**数据源策略：**
- **TikHub API**（优先）：聚合各平台热搜数据，稳定可靠
- **Chrome CDP 备用**：API 失效时通过浏览器爬取
- **缓存机制**：10 分钟内相同请求直接返回缓存，节省配额

### 2. 数据监测与采集

```
┌─────────────────────────────────────────────────────────────┐
│                      DataAnalyst Agent                      │
├─────────────────────────────────────────────────────────────┤
│  输入: 已发布内容 ID、时间范围                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ DataCollectTool — 多平台数据采集                     │    │
│  │ • 浏览量、点赞、评论、分享、收藏                       │    │
│  │ • 互动率计算 (likes+comments+shares) / views         │    │
│  │ • 粉丝增长数据                                        │    │
│  │ • 采集频率: 发布后 1h/24h/7d 自动采集                │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ AnalyticsReportTool — 报告生成                       │    │
│  │ • JSON / Markdown / CSV 多格式导出                   │    │
│  │ • 同比/环比分析                                       │    │
│  │ • 内容表现排名                                        │    │
│  └─────────────────────────────────────────────────────┘    │
│  输出: 分析报告 + 优化建议                                     │
└─────────────────────────────────────────────────────────────┘
```

**采集策略：**
- **定时采集**：APScheduler 后台任务，自动触发
- **增量采集**：只采集新数据，避免重复
- **异常处理**：采集失败自动重试 3 次（指数退避）

### 3. 内容发布机制

```
┌─────────────────────────────────────────────────────────────┐
│                   PublishCrew 发布线                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐                                       │
│  │ PlatformAdapter  │ — 内容格式适配                        │
│  │ • 标题长度截断     │   (小红书 20字 vs 微博 100字)         │
│  │ • 正文分段         │                                       │
│  │ • 话题标签转换     │   (#话题# vs @话题)                   │
│  │ • 图片压缩/数量限制 │                                       │
│  └────────┬─────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │        Platform Publishers (并行执行)                 │    │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌───┐│    │
│  │  │小红书│ │公众号│ │ 微博 │ │ 知乎 │ │ 抖音 │ │B站 ││    │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └─┬─┘│    │
│  │     │        │        │        │        │       │  │    │
│  │  Chrome CDP / Playwright — 浏览器自动化                │    │
│  │  • Cookie 认证                                        │    │
│  │  • 模拟人工操作 (打字、滚动、等待)                      │    │
│  │  • 截图验证发布成功                                    │    │
│  │  • 内置间隔限制 (防止风控)                             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**发布策略：**
- **并行发布**：多平台同时发布，互不阻塞
- **人工确认**：发布前可预览，人工审核后确认
- **定时发布**：支持指定时间发布，APScheduler 调度
- **失败重试**：发布失败自动重试 3 次
- **状态追踪**：实时记录发布状态和结果 URL

### 4. 技术栈说明

| 组件 | 技术选择 | 说明 |
|------|---------|------|
| **Agent 框架** | CrewAI | 多 agent 编排，支持 Sequential/Hierarchical |
| **LLM** | Claude (Anthropic) | Opus 创作，Sonnet 审核分析，Haiku 适配 |
| **浏览器自动化** | Playwright + Chrome CDP | 跨平台发布通用方案，可复用登录态 |
| **任务调度** | APScheduler | 定时发布、数据采集 |
| **持久化** | SQLite → PostgreSQL | 内容草稿、发布日志、分析数据 |
| **数据采集** | TikHub API + Chrome CDP | API 优先，浏览器备用 |

**为什么选择 Chrome CDP 而非各平台 API？**

1. **通用性强**：一套代码适配所有平台，API 需逐个对接
2. **复用登录态**：通过 Chrome MCP 复制已登录的浏览器状态，无需处理 OAuth
3. **规避限制**：官方 API 往往有频率限制和审核门槛
4. **快速迭代**：平台 UI 变化只需调整选择器，API 变更需要重写代码

**Chrome CDP 的局限性与应对：**
- **速度较慢**：需要等待页面加载，适合定时发布而非实时响应
- **稳定性依赖 UI**：平台改版可能失效，需要维护选择器
- **风控风险**：模拟人工操作（随机延迟、鼠标轨迹），严格遵守发布间隔

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ContentCrew（内容生产线）                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ TopicResearch│───▶│ ContentWriter│───▶│ ContentReview│──┐       │
│  │   选题研究员   │    │   内容创作者   │    │   内容审核员   │  │       │
│  └──────────────┘    └──────────────┘    └──────────────┘  │       │
│                                                          │ Human │
└──────────────────────────────────────────────────────────┼───────┘
                                                           │ Input
                                                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PublishCrew（发布线）                          │
│  ┌──────────────┐    ┌─────────────────────────────────────────┐   │
│  │PlatformAdapt │───▶│         Platform Publishers (并行)        │   │
│  │  平台适配师   │    │ 小红书 │ 公众号 │ 微博 │ 知乎 │ 抖音 │ B站  │   │
│  └──────────────┘    └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                                           │
                                                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       AnalyticsCrew（分析线）                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ DataCollect  │───▶│  DataAnalyze │───▶│  Recommend   │          │
│  │   数据采集    │    │   效果分析    │    │   优化建议    │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 前置要求

- Python 3.11+
- uv 包管理器（推荐）

### 安装

```bash
# 进入项目目录
cd C:\11projects\Crew

# 安装 uv（如果未安装）
pip install uv

# 安装依赖
uv sync

# 安装浏览器驱动（可选，用于平台发布）
uv run playwright install chromium
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入必要的 API Keys
```

**必需配置：**
```bash
# LLM API（二选一）
ANTHROPIC_API_KEY=sk-ant-xxx     # 推荐，用于 Claude 模型
OPENAI_API_KEY=sk-xxx            # 备选，用于 GPT 模型

# 各平台 Cookie / Token（按需填写）
XIAOHONGSHU_COOKIE=              # 小红书
WECHAT_APP_ID=                   # 微信公众号
WECHAT_APP_SECRET=
WEIBO_COOKIE=                    # 微博
ZHIHU_COOKIE=                    # 知乎
DOUYIN_COOKIE=                   # 抖音
BILIBILI_COOKIE=                 # B站
```

### 运行

#### 1. 内容生产线

```bash
# 从选题生成内容草稿
uv run python scripts/run_content_crew.py run \
  --topic "AI创业" \
  --platforms "xiaohongshu,wechat" \
  --brand-voice "专业但不失亲和" \
  --output "data/content/draft-001.json"

# 查看支持的平台
uv run python scripts/run_content_crew.py platforms
```

#### 2. 发布线

```bash
# 发布草稿到指定平台
uv run python scripts/run_publish_crew.py run \
  --draft-id "draft-001" \
  --platforms "xiaohongshu,wechat"

# 定时发布
uv run python scripts/run_publish_crew.py run \
  --draft-id "draft-001" \
  --platforms "xiaohongshu" \
  --schedule "2026-03-20T10:00:00"

# 查看发布状态
uv run python scripts/run_publish_crew.py status --draft-id "draft-001"
```

#### 3. 数据分析线

```bash
# 生成内容效果报告
uv run python scripts/run_analytics_crew.py run \
  --content-id "content-001" \
  --period "7d" \
  --output "data/analytics/report-001.json"

# 快速查看数据
uv run python scripts/run_analytics_crew.py quick --content-id "content-001"
```

---

## 项目结构

```
C:\11projects\Crew\
├── src/
│   ├── agents/              # Agent 定义（6 个）
│   │   ├── topic_researcher.py
│   │   ├── content_writer.py
│   │   ├── content_reviewer.py
│   │   ├── platform_adapter.py
│   │   ├── platform_publisher.py
│   │   └── data_analyst.py
│   ├── tools/               # 工具定义
│   │   ├── search_tools.py      # 热点搜索、竞品分析
│   │   ├── content_tools.py     # 配图搜索、话题标签、SEO
│   │   ├── analytics_tools.py   # 数据采集、报告生成
│   │   └── platform/            # 平台发布工具
│   │       ├── xiaohongshu.py       # 国内
│   │       ├── wechat.py
│   │       ├── weibo.py
│   │       ├── zhihu.py
│   │       ├── douyin.py
│   │       ├── bilibili.py
│   │       └── overseas.py          # 海外 (Reddit/X/FB/IG/Threads)
│   ├── crew/crews/         # Crew 编排
│   │   ├── content_crew.py      # 内容生产线
│   │   ├── publish_crew.py      # 发布线
│   │   └── analytics_crew.py    # 分析线
│   ├── schemas/             # Pydantic 数据模型
│   ├── models/              # SQLAlchemy 数据库模型
│   ├── core/                # 核心配置
│   └── api/                 # FastAPI（可选）
├── scripts/                 # CLI 入口脚本
│   ├── run_content_crew.py
│   ├── run_publish_crew.py
│   └── run_analytics_crew.py
├── tests/                   # 测试套件
│   ├── unit/               # 单元测试
│   └── integration/        # 集成测试
├── data/                    # 数据存储
│   ├── content/            # 生成的内容
│   └── analytics/          # 分析报告
├── pyproject.toml          # 项目配置
├── .env.example            # 环境变量模板
├── README.md               # 本文件
└── CLAUDE.md               # Claude Code 开发指南
```

---

## Agent 角色说明

| Agent | 职责 | LLM |
|-------|------|-----|
| **TopicResearcher** | 选题研究员 — 追踪热点、分析竞品、挖掘高潜力选题 | Claude Sonnet |
| **ContentWriter** | 内容创作者 — 根据选题创作高质量内容 | Claude Opus |
| **ContentReviewer** | 内容审核员 — 质量审核、合规检查、SEO 优化 | Claude Sonnet |
| **PlatformAdapter** | 平台适配师 — 将内容适配为各平台最优格式 | Claude Haiku |
| **PlatformPublisher** | 平台发布员 — 执行发布和排期操作 | — |
| **DataAnalyst** | 数据分析师 — 采集数据、分析效果、生成建议 | Claude Sonnet |

---

## 开发

### 代码质量

```bash
# 格式化代码
uv run ruff format src tests

# 检查代码
uv run ruff check src tests

# 类型检查
uv run mypy src

# 运行测试
uv run pytest

# 测试覆盖率
uv run pytest --cov=src --cov-report=html
```

### 测试

```bash
# 运行所有测试
uv run pytest

# 运行单元测试
uv run pytest tests/unit/

# 运行集成测试
uv run pytest tests/integration/

# 查看覆盖率报告
open htmlcov/index.html
```

### API 服务（可选）

```bash
# 启动 FastAPI 服务
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 访问 API 文档
# http://localhost:8000/docs
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | CrewAI |
| LLM | Claude (Anthropic) / OpenAI |
| 后端框架 | FastAPI |
| 数据验证 | Pydantic v2 |
| 任务调度 | APScheduler |
| 持久化 | SQLite (dev) / PostgreSQL (prod) |
| 浏览器自动化 | Playwright |
| 测试框架 | pytest |

---

## 注意事项

### 平台发布限制

为避免被平台风控，各平台发布操作内置了间隔限制：

#### 国内平台

| 平台 | 最小间隔 | 正文限制 | 图片限制 | 说明 |
|------|---------|---------|---------|------|
| 小红书 | 60 秒 | 1000 字 | 9 张 | 严格风控 |
| 微信公众号 | 30 秒 | 无限制 | 无限制 | API 发布 |
| 微博 | 10 秒 | 2000 字 | 9 张 | 支持 #话题# |
| 知乎 | 30 秒 | 10000 字 | 无限制 | 100/500 字最小限制 |
| 抖音 | 5 分钟 | 150 字 | 1 封面 | 严格风控 |
| B站 | 60 秒 | 200 字 | 1 封面 | 支持分区选择 |

#### 海外平台

| 平台 | 最小间隔 | 正文限制 | 图片限制 | 说明 |
|------|---------|---------|---------|------|
| Reddit | 10 分钟 | 40000 字 | 20 张 | 需指定 Subreddit，Markdown |
| X (Twitter) | 60 秒 | 280 字 | 4 张 | 超长自动拆分 Thread |
| Facebook | 60 秒 | 63206 字 | 10 张 | 支持 Page/Group |
| Instagram | 5 分钟 | 2200 字 | 10 张 | 必须含图片/视频，支持 Carousel |
| Threads | 60 秒 | 500 字 | 10 张 | Meta 旗下，类 Twitter |

### 安全建议

- 不要在代码中硬编码 API Keys
- 使用环境变量管理敏感信息
- 定期更新平台 Cookie
- 首次使用建议用小号测试

---

## 路线图

- [x] Phase 1: MVP — 单平台内容生产和发布
- [x] Phase 2: 多平台扩展 — 6 大平台支持
- [x] Phase 3: 数据分析 — 自动采集和报告生成
- [ ] Phase 4: Web Dashboard — 可视化操作界面
- [ ] Phase 5: 智能排期 — 基于历史数据的发布时间优化

---

## 许可证

MIT License

---

## 相关文档

- [PRD](research/自媒体运营MultiAgent系统选型报告.md) — 产品需求文档
- [CLAUDE.md](CLAUDE.md) — Claude Code 开发指南
- [CrewAI 文档](https://docs.crewai.com/)
