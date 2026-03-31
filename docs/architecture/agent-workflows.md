# Crew Media Ops — Agent 工作流全景文档

> 本文档整理了系统中所有 Agent 的内部工作流、输入输出、工具调用和协作关系。

---

## 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户入口                                  │
│  Onboarding → 录入赛道/目标客户/品味偏好 → TasteEngine 沉淀      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │     ContentCrew         │
              │   (内容生产线 Crew)      │
              │                         │
              │  模式 1: 简化模式        │
              │  Creator → Reviewer     │
              │                         │
              │  模式 2: 完整模式        │
              │  Orchestrator 编排:      │
              │  Researcher → Marketer  │
              │  → Copywriter → Designer│
              │  → Reviewer             │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │     PublishCrew          │
              │   (发布线 Crew)          │
              │                         │
              │  PlatformAdapter        │
              │  → PlatformPublisher ×N │
              │    (6平台并行发布)       │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │    AnalyticsCrew        │
              │   (分析线 Crew)          │
              │                         │
              │  DataCollector           │
              │  → DataAnalyzer          │
              │  → StrategyAdvisor       │
              │                         │
              │  数据反哺 → TasteEngine  │
              └─────────────────────────┘
```

---

## 0. OnboardingAgent — 用户偏好引导

**文件**: `src/agents/onboarding.py`

### 定位
引导新用户通过对话录入 taste 偏好，沉淀到 TasteProfile。不参与 Crew 编排，独立运行。

### 工作流

```
用户注册
  │
  ▼
Step 1: 选赛道 ─────── "你主要创作哪个领域的内容？"
  │                     选项: 科技/AI, 职场/成长, 生活方式, 教育, 其他
  ▼
Step 2: 选调性 ─────── "你的内容调性更偏向？"（多选）
  │                     选项: 专业权威, 亲和真诚, 幽默风趣, 极简干货
  ▼
Step 3: 选平台 ─────── "你主要在哪些平台发布？"（多选）
  │                     选项: 小红书, 公众号, 微博, 知乎, 抖音, B站
  ▼
Step 4: 选长度 ─────── "你偏好的文章长度？"
  │                     选项: 短(500字内), 中(500-1500字), 长(1500字+)
  ▼
Step 5: 选开场 ─────── "你偏好的开场方式？"（多选）
  │                     选项: 痛点开场, 反常识, 故事, 数据, 提问
  ▼
Step 6: 选避免 ─────── "你希望避免什么风格？"（多选）
  │                     选项: 太营销, 太官话, 太模板, 废话多, 太夸张
  ▼
构建 ExplicitPreferences → 写入 TasteEngine
  │
  ▼
返回 taste_prompt（供后续创作使用）
```

### 输入/输出

| 方向 | 数据 |
|------|------|
| 输入 | 用户逐步回答的选项（session 管理） |
| 输出 | `ExplicitPreferences` → 写入 `TasteEngine` |

### 持续学习

Onboarding 之后，用户对样稿的反馈（喜欢/不喜欢/修改）通过 `record_draft_feedback()` 持续沉淀到 TasteEngine，不断校准品味画像。

---

## 1. Researcher — 热点研究员

**文件**: `src/agents/researcher.py`
**LLM**: claude-sonnet-4（默认）

### 定位
追踪热点、分析趋势、收集爆款参考。为内容创作提供数据支持。

### 内部工作流

```
输入: topic + target_platform
  │
  ▼
Tool 1: HotSearchTool ──── 热点搜索
  │  输入: platform, limit=10
  │  输出: 各平台热搜/热榜 TOP 10
  ▼
Tool 2: TrendAnalysisTool ── 趋势分析
  │  输入: keyword=topic, time_range="7d"
  │  输出: trend_direction, trend_score
  ▼
Tool 3: 爆款搜索（LLM 生成） ── 结构化爆款分析
  │  输出: 5 个爆款参考，每个包含:
  │    - title, platform, metrics(likes/comments)
  │    - analysis: 结构(清单体/故事体), 情绪(实用/焦虑),
  │               标题技巧, 内容深度
  ▼
生成 recommendations（创作建议列表）
  │
  ▼
输出: ResearchReport
  {
    topic, trending_topics[], viral_references[],
    competitor_insights[], recommendations[],
    trend_analysis{}
  }
```

### 工具清单

| 工具 | 作用 | 来源 |
|------|------|------|
| `HotSearchTool` | 各平台热搜/热榜 | `src/tools/search_tools.py` |
| `TrendAnalysisTool` | 关键词趋势分析 | `src/tools/search_tools.py` |
| 爆款搜索 | LLM 生成结构化爆款分析 | 内置逻辑 |

---

## 2. Marketer — 营销策划师

**文件**: `src/agents/marketer.py`
**LLM**: claude-sonnet-4（默认）

### 定位
基于研究报告 + 用户 taste 制定内容策略、规划发布节奏。

### 内部工作流

```
输入: topic + target_platform + research_data + taste_context
  │
  ▼
Tool 1: 平台策略分析 ──── platform_strategy_analysis
  │  根据平台生成:
  │    - adaptation（内容适配方向）
  │    - best_time（最佳发布时间）
  │    - hashtags, interaction_tips
  │    - word_count_range
  ▼
Tool 2: 内容定位分析 ──── content_positioning
  │  结合 research_data + taste_context 生成:
  │    - main_theme, sub_themes
  │    - tone（调性）
  │    - key_messages
  │    - differentiation（差异化策略）
  │    - taste_notes（用户偏好备注）
  │    - research_backed_tips（研究支撑的建议）
  ▼
Tool 3: 发布时间优化 ──── publish_timing_optimizer
  │  输出: frequency, best_times[], content_mix
  ▼
输出: ContentStrategy
  {
    content_strategy{}, platform_strategies[],
    publishing_schedule{}, kpis{}
  }
```

### 平台最佳发布时间

| 平台 | 最佳时段 | 内容调性 |
|------|---------|---------|
| 小红书 | 08:00, 12:00, 20:00 | 真实种草分享感 |
| 公众号 | 07:00, 12:00, 21:00 | 有深度但不端着 |
| 微博 | 09:00, 12:00, 18:00 | 快准狠 |
| 知乎 | 20:00, 21:00 | 有框架有论证 |
| 抖音 | 18:00, 19:00, 21:00 | 口语化+快节奏 |
| B站 | 18:00, 20:00 | 有梗有信息量 |

---

## 3. Copywriter — 文案创作者

**文件**: `src/agents/copywriter.py`
**LLM**: claude-sonnet-4（默认）

### 定位
根据策略和研究创作文案，生成多版本，确保合规。

### 内部工作流

```
输入: topic + platform + research_data + strategy_data + taste_context
  │
  ▼
Tool 1: 爆款结构分析 ──── viral_structure_analysis
  │  从 research_data.viral_references 提取结构模式
  │  输出: patterns[] (清单体/故事体/观点体)
  ▼
Tool 2: 文案生成 ──── content_generation (LLM 调用)
  │  结合 strategy.tone + taste_context + patterns
  │  输出: title, content, summary, tags, hashtags
  ▼
Tool 3: 合规检查 ──── compliance_check
  │  检测三类违禁词:
  │    - 广告法极限词（最/第一/唯一/100%...）
  │    - 诱导互动词（点赞过/评论区领取...）
  │    - 站外引流词（微信号/加微信/扫码...）
  │  输出: { passed: bool, issues[], warnings[] }
  ▼
Tool 4: 标题变体生成 ──── title_variant_generation
  │  生成 2-3 个标题变体供 A/B 测试
  ▼
输出: CopyDraft
  {
    title, content, summary, tags, hashtags,
    platform, style_notes, title_variants[],
    compliance_check{}
  }
```

---

## 4. Designer — 视觉设计师

**文件**: `src/agents/designer.py`
**LLM**: claude-sonnet-4（默认）

### 定位
生成配图方案、设计封面、定义视觉风格。

### 内部工作流

```
输入: topic + content_data(Copywriter输出) + target_platform
  │
  ▼
Tool 1: 封面图生成 ──── cover_image_generation
  │  根据平台生成 DALL-E prompt + 尺寸:
  │    小红书: 1242×1660 (3:4)
  │    公众号: 900×383 (2.35:1)
  │    微博:   690×920 (3:4)
  │    知乎:   690×400
  │    抖音:   1080×1920 (9:16)
  │    B站:    1920×1080 (16:9)
  │  输出: { prompt, url, alt_text, dimensions }
  ▼
Tool 2: 配图方案 ──── content_images_planning
  │  分析正文段落数，决定配图数量(1-3张)
  │  输出: [{ prompt, url, alt_text, position }]
  ▼
Tool 3: 视觉风格定义 ──── visual_style_definition
  │  输出: { color_palette, style, mood }
  ▼
输出: DesignOutput
  {
    cover_image{}, content_images[],
    image_style{}, platform_adaptations{},
    generation_notes
  }
```

---

## 5. ContentCreator — 内容研究创作者（一体化）

**文件**: `src/agents/content_creator.py`
**LLM**: claude-opus-4（注意：用的是 Opus，不是 Sonnet）

### 定位
简化模式下的核心 Agent，合并了研究+创作。追踪热点 → 研究爆款 → 学习风格 → 创作内容。

### 内部工作流

```
输入: topic + target_platform + taste_context + revision_feedback(可选)
  │
  ▼
步骤 1: 爆款对标研究
  │  搜索 ≥5 个真实爆款（30天内、高互动、主题相关）
  │  每个爆款分析 5 维度: 结构、情绪、配图、标题、内容深度
  ▼
步骤 2: 拟定大纲
  │  - 3 个备选标题（选最强的）
  │  - 开头钩子设计
  │  - 正文结构规划
  │  - 情绪节奏设计
  │  - 结尾互动设计
  ▼
步骤 3: 正文创作
  │  - 匹配平台调性（按需注入平台风格指南）
  │  - 每段必须有新信息
  │  - 加入独特视角
  ▼
步骤 4: 质量自检（6 维度，每项 1-10，目标 ≥7）
  │  钩子力 | 信息密度 | 情绪节奏 | 可操作性 | 原创视角 | 互动设计
  │  如果任何维度 <7，修改后再提交
  ▼
输出: ContentDraft (JSON)
  {
    title, content, summary, tags, style_notes,
    platform, quality_self_check{},
    viral_references[{ title, url, metrics, matched_dimensions }]
  }
```

### 平台风格指南（按需注入）

Creator 内置了 6 个平台的详细风格指南，只在创作对应平台内容时注入到 backstory，避免 token 浪费：

| 平台 | 标题公式 | 正文结构 | 硬约束 |
|------|---------|---------|--------|
| 小红书 | {肤质}+{痛点}+{方案} | 五段式(痛点→方案→验证→总结→互动) | ≤20字标题, 500-1000字 |
| 公众号 | 激发好奇/观点鲜明 | 开头+分段正文+结尾 | 20-30字标题, 2000-4000字 |
| 微博 | 蹭热点四要素 | 开头+正文+标签 | 100-120字 |
| 知乎 | 反常识/故事/权威 | 结论先行+论证 | 专业中立 |
| 抖音 | 黄金3秒开场 | 钩子→引入→内容→总结→互动 | 15-60秒脚本 |
| B站 | 开场钩子+预告 | 背景→核心→总结→三连 | 10-20分钟 |

---

## 6. ContentReviewer — 内容审核员

**文件**: `src/agents/content_reviewer.py`
**LLM**: claude-sonnet-4（默认）

### 定位
独立审核内容质量和合规性，支持人工审核环节。

### 内部工作流

```
输入: ContentCreator/Copywriter 的输出 + target_platform
  │
  ▼
审核 1: 爆款对标验证（一票否决）
  │  - ≥5 个真实爆款对标？
  │  - 每个对标 ≥2 个维度匹配？
  │  - 链接和数据可验证？
  │  不满足 → 直接 needs_revision
  ▼
审核 2: 6 维度质量评分（对照创作者自检）
  │  钩子力 | 信息密度 | 情绪节奏 | 可操作性 | 原创视角 | 互动设计
  │  如果创作者自评与审核评分差距 >2 分 → 标注"自评偏差"
  ▼
审核 3: 合规检查（ForbiddenWordsChecker）
  │  5 类违禁词检测:
  │    - 广告法极限词（最/第一/唯一...）→ 严重，每个扣 20 分
  │    - 诱导互动词 → 轻度，每个扣 10 分
  │    - 站外引流词 → 严重
  │    - 医疗健康敏感词 → 严重
  │    - 金融投资敏感词 → 严重
  │  + 平台特定违禁词
  ▼
审核 4: 平台适配检查
  │  字数、结构、标题长度是否符合平台规范
  ▼
综合评分 = 质量(35%) + 合规(30%) + 传播力(20%) + 口味匹配(15%)
  │
  ├── ≥85 → approved
  ├── 60-84 → needs_revision（列出具体修改项）
  └── <60 → rejected（说明根本性问题）
  │
  ▼
输出: ReviewReport
  {
    result: "approved/needs_revision/rejected",
    overall_score, scores{},
    creator_self_check_delta{},
    viral_check, viral_count,
    issues[], suggestions[], highlights[],
    final_content(如有小修改可直接给出)
  }
```

---

## 7. ContentOrchestrator — 内容编排者

**文件**: `src/agents/content_orchestrator.py`

### 定位
完整模式下的协调者，指挥 4 个子 Agent 完成内容创作全流程。

### 编排工作流

```
输入: topic + target_platform + content_type + taste_context
  │
  ▼
阶段 1: Researcher.run()
  │  → emit_agent_started("researcher")
  │  → 执行热点研究流程（见 Agent 1）
  │  → emit_agent_completed("researcher")
  │  输出: research_output
  ▼
阶段 2: Marketer.run()
  │  → emit_agent_started("marketer")
  │  → 执行策略制定流程（见 Agent 2）
  │  → 接收 research_output + taste_context
  │  → emit_agent_completed("marketer")
  │  输出: strategy_output
  ▼
阶段 3: Copywriter.run()
  │  → emit_agent_started("copywriter")
  │  → 执行文案创作流程（见 Agent 3）
  │  → 接收 research_output + strategy_output + taste_context
  │  → emit_agent_completed("copywriter")
  │  输出: copy_output
  ▼
阶段 4: Designer.run()
  │  → emit_agent_started("designer")
  │  → 执行视觉设计流程（见 Agent 4）
  │  → 接收 copy_output
  │  → emit_agent_completed("designer")
  │  输出: design_output
  ▼
整合最终输出: _build_final_output()
  │  合并 copy_output + design_output
  ▼
输出:
  {
    topic, platform, workflow_stages{},
    final_output{ title, content, summary, tags,
                  cover_image, content_images, image_style },
    metadata{ sub_agents[], workflow_config{}, generated_at }
  }
```

### 特性
- 每个阶段可独立开关（`enable_researcher/marketer/copywriter/designer`）
- 每个阶段有 try/catch，单个 Agent 失败不影响整体
- 通过 `CallbackHandler` 实时推送 WS 事件到前端

---

## 8. PlatformAdapter — 平台适配师

**文件**: `src/agents/platform_adapter.py`
**LLM**: claude-sonnet-4（默认）

### 定位
将通用内容转换为各平台专属格式。

### 平台规格配置

| 平台 | 标题上限 | 摘要上限 | 标签上限 | 典型长度 | 特殊要求 |
|------|---------|---------|---------|---------|---------|
| 公众号 | 64字 | 200字 | 5个 | 1500-3000 | 支持 Markdown/HTML |
| 小红书 | 20字 | 100字 | 10个 | 500-1500 | 需要 emoji |
| 抖音 | 50字 | 150字 | 5个 | 200-500 | 视频优先 |
| B站 | 80字 | 500字 | 12个 | 800-2000 | — |
| 知乎 | 50字 | 300字 | 5个 | 2000-5000 | 支持 Markdown/HTML |
| 微博 | 30字 | 140字 | 5个 | 100-300 | — |

### 输出

```
AdaptedContent {
  platform, title, content, summary,
  tags[], cover_image, metadata{}
}
```

---

## 9. PlatformPublisher — 平台发布员

**文件**: `src/agents/platform_publisher.py`
**LLM**: claude-sonnet-4（默认）

### 定位
将适配后的内容发布到各平台，管理发布队列和重试。

### 发布状态机

```
PENDING → SCHEDULED → PUBLISHING → PUBLISHED
                                 ↘ FAILED → RETRYING → PUBLISHED/FAILED
```

### 输出

```
PublishRecord {
  content_id, platform, status,
  published_url, published_at, scheduled_at,
  error_message, retry_count, metadata{}
}

PublishBatch {
  content_id, records{ platform → PublishRecord },
  summary{ total, successful, failed, pending }
}
```

---

## 10. DataAnalyst — 数据分析师

**文件**: `src/agents/data_analyst.py`
**LLM**: claude-sonnet-4（默认）

### 定位
分析内容表现数据，提供优化建议。在 AnalyticsCrew 中扮演 3 个角色。

### 指标体系

| 指标 | 说明 |
|------|------|
| views | 浏览量 |
| likes | 点赞数 |
| comments | 评论数 |
| shares | 分享数 |
| favorites | 收藏数 |
| engagement_rate | 互动率 = (赞+评+转+藏)/浏览 |
| reach | 曝光量 |
| click_rate | 点击率 |
| conversion | 转化数 |
| follower_growth | 粉丝增长 |

### 输出

```
AnalysisReport {
  report_type, period, summary,
  key_findings[], metrics_summary{},
  top_performers[], underperformers[],
  recommendations[]
}

TrendAnalysis {
  metric_type, platform,
  current_value, previous_value, change_percent,
  trend(up/down/stable), insight
}
```

---

## Crew 编排详解

### ContentCrew — 内容生产线

**文件**: `src/crew/crews/content_crew.py`

```
模式 1 (简化): ContentCreator → ContentReviewer
模式 2 (完整): Orchestrator(Researcher→Marketer→Copywriter→Designer) → ContentReviewer
```

**执行流程（带修订循环）**:

```
1. 从 TasteEngine 获取 taste_prompt
2. 注入 taste_context 到创作任务
3. 执行 create → review
4. 如果 reviewer 返回 needs_revision:
   │  提取 issues + suggestions
   │  格式化为 revision_feedback
   │  注入到下一轮创作任务
   │  重试（最多 3 轮）
5. 记录反馈到 TasteEngine
```

### PublishCrew — 发布线

**文件**: `src/crew/crews/publish_crew.py`

```
Task 1: PlatformAdapter 适配（顺序）
  │  将内容适配到 N 个平台格式
  ▼
Task 2-N: PlatformPublisher ×N（并行）
  │  各平台并行发布
  ▼
支持两种模式:
  - agent 模式: 通过 CrewAI agent 编排（LLM 驱动）
  - direct 模式: 直接调用平台工具 publish()（无 LLM 开销）
```

### AnalyticsCrew — 分析线

**文件**: `src/crew/crews/analytics_crew.py`

```
Task 1: DataCollector（数据采集员）
  │  使用 data_collect_tool 采集各平台数据
  ▼
Task 2: DataAnalyzer（数据分析员）
  │  计算统计、识别 top/bottom、检测异常
  ▼
Task 3: StrategyAdvisor（策略顾问）
  │  生成优化建议: content/timing/platform/tag/engagement
  │  分为 quick_wins + long_term_strategy
```

---

## 数据流全景

```
用户 Onboarding
  │
  ├─→ TasteEngine (品味沉淀)
  │     │
  │     ├─ ExplicitPreferences (注册时录入)
  │     ├─ ImplicitSignals (交互中学习)
  │     └─ taste_prompt (注入创作)
  │
  ▼
ContentCrew
  │
  ├─ Researcher → ResearchReport { trending[], viral[], recommendations[] }
  │     │
  │     ▼
  ├─ Marketer → ContentStrategy { theme, tone, schedule, kpis }
  │     │         (接收 research + taste)
  │     ▼
  ├─ Copywriter → CopyDraft { title, content, tags, compliance }
  │     │           (接收 research + strategy + taste)
  │     ▼
  ├─ Designer → DesignOutput { cover, images, style }
  │     │         (接收 copy)
  │     ▼
  └─ Reviewer → ReviewReport { score, issues, suggestions }
        │         (审核 → 可能触发修订循环)
        │
        ▼
PublishCrew
  │
  ├─ Adapter → AdaptedContent ×N (每平台一份)
  │     │
  │     ▼
  └─ Publisher ×N → PublishRecord ×N (并行发布)
        │
        ▼
AnalyticsCrew
  │
  ├─ Collector → ContentMetrics[]
  ├─ Analyzer → AnalysisReport
  └─ Advisor → Recommendations[]
        │
        ▼
  数据反哺 → TasteEngine (更新品味画像)
```

---

## WS 实时事件

通过 `CallbackHandler`（`src/crew/callbacks.py`），Orchestrator 在每个阶段发射 WS 事件：

| 事件类型 | 触发时机 | 数据 |
|---------|---------|------|
| `workflow_started` | Crew 开始执行 | agents[], inputs |
| `agent_started` | Agent 开始工作 | agent_id, agent_name, input |
| `agent_completed` | Agent 完成 | agent_id, output, duration_ms |
| `agent_failed` | Agent 失败 | agent_id, error, duration_ms |
| `tool_call_start` | 工具调用开始 | agent_id, tool_name, input |
| `tool_call_end` | 工具调用结束 | agent_id, tool_name, status, output |

---

_最后更新: 2026-03-31_
