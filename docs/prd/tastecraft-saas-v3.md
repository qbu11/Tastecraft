# TasteCraft SaaS — PRD v3.0

> AI content engine with taste evolution: generate, publish, learn.

**Version**: 3.0
**Date**: 2026-05-15
**Status**: DRAFT
**Evolution**: Self-Use CLI (v1) → Full Product Design (v2.3, frozen) → SaaS MVP (v3, this doc)

---

## 1. Product Vision

### 1.1 One-liner

TasteCraft is a SaaS content engine that auto-generates, auto-publishes, and continuously learns your taste through every edit you make — until it writes like you, not like AI.

### 1.2 Core Insight

The real moat is not content generation (commodity) nor multi-platform publishing (solved). It's **taste memory** — the accumulated preference data from every user edit, every content performance signal, every competitor pattern observed. The longer you use TasteCraft, the harder it is to leave.

### 1.3 Target Users

**Primary**: Founders / small team leads who need social media presence but have no dedicated operations staff. Max 15 min/day on content.

**Decision flow**:
- Configure once (topic, style, platforms, competitors)
- Review and lightly edit generated content
- Confirm publish → system handles the rest
- System learns from every interaction

---

## 2. Product Architecture

### 2.1 System Overview

```
┌─────────────────────────────────────────────────┐
│              TasteCraft SaaS Website             │
│                                                  │
│  Onboarding → Config (topic/style/platform)      │
│  AI Generate + Auto-layout → Preview (L2 edit)   │
│  User confirms → System publishes                │
└────────────────────┬─────────────────────────────┘
                     │
          ┌──────────┼────────────────┐
          ▼          ▼                ▼
     WeChat MP    XHS / Weibo      Fallback
     wechatpy     Patchright       Local Helper
     Official     (Remote          (Browser ext/
     API          Browser +        Desktop agent,
                  noVNC login)     real environment)
          │          │                │
          └──────────┼────────────────┘
                     ▼
          ┌─────────────────────────┐
          │    TikHub API (READ)    │
          │                         │
          │  ① Published content    │
          │  ② Performance metrics  │
          │  ③ Competitor tracking  │
          │  ④ Trend discovery      │
          └────────────┬────────────┘
                       ▼
          ┌─────────────────────────┐
          │   Taste Evolution Engine │
          │                         │
          │  Inner loop: self→data  │
          │  Outer loop: comp→trend │
          │  Diff learning: edits   │
          └─────────────────────────┘
```

### 2.2 Module Design (Loosely Coupled)

Each module is independently usable; combined experience is better.

| Module | Standalone Value | Combined Value |
|--------|-----------------|----------------|
| Content Generation | AI writing + auto-layout | + taste-aware generation |
| Publishing | Multi-platform auto-publish | + draft preview + scheduling |
| Competitor Monitoring | Track competitors + trends | + feed into generation topics |
| Taste Evolution | — (requires other modules) | Synthesizes all signals |

Users can choose which modules to use. Pricing scales with usage.

---

## 3. Core Features

### 3.1 Content Generation + Auto-Layout

**Input**: Topic/direction + taste profile + competitor trends
**Output**: Platform-adapted content (text + images + tags + layout)
**User interaction**: Preview → L2 micro-edit (title, wording, minor tweaks) → Confirm

**Key capabilities**:
- Multi-platform adaptation (XHS short + visual vs WeChat long-form)
- Auto image selection / generation
- Hashtag and SEO optimization
- Tone/style aligned with taste profile

### 3.2 Publishing Engine

**Architecture (Hybrid D)**:

| Platform | Method | Draft Support | Reliability |
|----------|--------|---------------|-------------|
| WeChat Official Account | wechatpy (Official API) | Yes (native draft) | High |
| Xiaohongshu | Patchright (remote browser) | Push to web creator | Medium |
| Weibo | Patchright (remote browser) | Push to web draft | Medium-Low |

**Login state management**:
- WeChat: OAuth via official API (no browser needed)
- XHS/Weibo: Remote browser with noVNC — user scans QR on our website, session persists server-side
- Fallback: Local helper (browser extension) for when remote browser gets detected

**Publishing flow**:
1. Content pushed to platform's native draft box (user can preview in native editor)
2. Our platform also shows preview (with note: "native platform rendering is authoritative")
3. User confirms in our system
4. System executes publish from draft
5. TikHub verifies published version

**Reference projects**:
- `dreammis/social-auto-upload` (11K stars) — multi-platform publisher, Patchright-based
- `patchright-python` (1.3K stars) — anti-detection Playwright fork
- `white0dew/XiaohongshuSkills` (2.7K stars) — XHS CDP automation
- `wechatpy/wechatpy` (4.3K stars) — WeChat Official Account SDK

### 3.3 Data Collection (TikHub API)

**Dual role**:

**Role 1: Self-content tracking**
- Pull published version → Diff against draft (detect if user edited in native editor)
- Collect metrics: views, likes, comments, shares at T+24h / T+72h / T+7d
- Feed performance data into taste evolution

**Role 2: Competitor monitoring**
- Daily pull of new posts from competitor watch list
- Extract: hot topics, content hooks, traffic patterns, viral formats
- During cold-start: analyze competitor history to establish lane baseline

**Coverage** (verified via actual API testing 2026-05-15):

| Platform | List Posts by Account | Full Text | Metrics | Search | Trends |
|----------|:--------------------:|:---------:|:-------:|:------:|:------:|
| Xiaohongshu | YES | YES | YES | YES | YES |
| WeChat MP | **NO** (API broken) | YES (need URL) | **NO** | Keyword only (unstable) | NO |
| Zhihu | YES | YES | YES | YES | YES |
| Weibo | YES | YES | YES | YES | YES |
| Douyin | YES | YES | YES | YES | YES |

**WeChat MP limitation** (confirmed by live testing):
- `fetch_mp_article_list` (list by ghid): returns 400 on ALL attempts (20+ tries)
- `fetch_mp_article_read_count`: chain broken, unusable
- Only working: keyword search (20-30% success rate, needs 3-5 retries) + article detail by URL

**WeChat MP fallback strategy**:
- Own account data: wechatpy official API (full access to own articles + metrics)
- Competitor monitoring: TikHub keyword search (approximate, not per-account tracking) + 搜狗微信搜索 supplementary
- This is the weakest link in the data pipeline; acceptable tradeoff for MVP

**Cost estimate**: ~$55-62/month for 50 competitor accounts across 4 well-supported platforms + limited WeChat coverage.

### 3.4 Taste Evolution Engine

**Three signal sources**:

```
Taste Evolution
├── Explicit signals (user edits)
│   ├── First edit → immediately apply
│   └── Nth edit → synthesize with history, extract patterns
│
├── Performance signals (metrics)
│   ├── Which content performs well → reinforce style
│   └── Which content underperforms → adjust
│
└── External signals (competitor monitoring)
    ├── Lane trends → inject into topic selection
    └── Viral patterns → adapt format/hooks
```

**Diff Learning Mechanism** (core IP):

```python
class TasteEdit:
    original: str          # AI draft
    modified: str          # User's version
    diff_type: str         # title / body / tone / structure
    platform: str          # Platform context
    content_line: str      # Which content pipeline
    timestamp: datetime

class TastePreference:
    dimension: str         # "title_style" / "paragraph_length" / "tone"
    rule: str              # "Use question opener for XHS titles"
    confidence: float      # 0-1, grows with edit count
    platform: str          # Platform-specific or global
    source_edits: list[str]  # Source diff IDs
```

**Design principles**:
- First diff takes effect immediately (user perceives "it's learning me")
- Confidence grows with sample size (3+ similar edits → high confidence)
- Isolated by platform × content line (different contexts may have different preferences)
- Conflicts trigger user confirmation ("You previously preferred X, now Y — which?")
- This is implicit RLHF — every edit is a preference signal

**Retention moat**: Accumulated taste data is non-portable. Competitors can copy features but not user preference history.

### 3.5 Taste Vault (Per-User Knowledge Base)

Each user has an Obsidian-like knowledge base — a collection of interconnected markdown documents with bidirectional links. This IS the user's taste, not a flat config file.

**Structure** (per content line):

```
vault/{user_id}/{content_line}/
├── _index.md                    # Content line overview + active links
├── style/
│   ├── tone.md                  # Voice, register, formality level
│   ├── structure.md             # Paragraph patterns, hook styles
│   ├── vocabulary.md            # Preferred/banned words + phrases
│   ├── visual.md                # Image style, layout preferences
│   └── platform-adaptations.md  # Per-platform style overrides
├── preferences/
│   ├── edits-log.md             # Chronological diff history (JSONL-like)
│   ├── patterns.md              # Extracted patterns from edits (auto-updated)
│   ├── explicit-rules.md        # User-stated rules ("never use emoji")
│   └── conflicts.md             # Unresolved preference conflicts
├── competitors/
│   ├── {account-slug}.md        # Per-competitor profile + style analysis
│   ├── lane-trends.md           # Current lane hot topics + patterns
│   └── viral-patterns.md        # Structures/hooks that drove engagement
├── context/
│   ├── brand.md                 # Brand identity, mission, values
│   ├── audience.md              # Target audience profile
│   ├── topics-history.md        # Past topics + performance correlation
│   └── seasonal.md              # Time-sensitive context (events, launches)
└── evolution/
    ├── changelog.md             # Taste profile change history
    ├── metrics-correlation.md   # Which preferences correlate with performance
    └── weekly-digest.md         # Auto-generated weekly evolution summary
```

**Bidirectional links** (`[[wikilinks]]`):
- `tone.md` links to `patterns.md` ("tone preference X derived from [[edits-log]] entries #12, #34, #67")
- `{competitor}.md` links to `viral-patterns.md` ("competitor Y's hook style → see [[viral-patterns#question-opener]]")
- `patterns.md` links to `explicit-rules.md` ("inferred rule conflicts with [[explicit-rules#no-emoji]], user confirmed keep rule")

**Harness Engineering** (context injection strategy):

The critical challenge: each AI generation call has limited context window. The harness must select the RIGHT vault documents to inject, at the RIGHT time, with the RIGHT priority.

```
Generation Request
         │
         ▼
┌─────────────────────────────┐
│     Context Harness          │
│                              │
│  Step 1: ALWAYS inject       │
│    - style/tone.md           │
│    - style/structure.md      │
│    - preferences/patterns.md │
│    - context/brand.md        │
│                              │
│  Step 2: CONDITIONALLY inject│
│    (based on generation task)│
│    - Topic about X? → pull   │
│      [[competitors]] who     │
│      covered X recently      │
│    - Platform = XHS? → pull  │
│      [[platform-adaptations  │
│      #xiaohongshu]]          │
│    - Seasonal relevance? →   │
│      pull [[seasonal]]       │
│                              │
│  Step 3: DYNAMICALLY inject  │
│    (RAG over vault)          │
│    - Embed query: "content   │
│      about {topic} for       │
│      {platform}"             │
│    - Retrieve top-k relevant │
│      vault sections          │
│                              │
│  Step 4: PRIORITY & TRIM     │
│    - Hard rules > soft prefs │
│    - Recent edits > old edits│
│    - High-confidence > low   │
│    - Trim to fit context     │
│      window budget           │
└─────────────────────────────┘
         │
         ▼
   System prompt assembled
   (taste-aware generation)
```

**Vault maintenance** (automated):
- After each user edit: update `edits-log.md`, re-extract `patterns.md`
- After competitor daily pull: update `{competitor}.md`, refresh `lane-trends.md`
- After metrics collection: update `metrics-correlation.md`
- Weekly: generate `weekly-digest.md`, prune low-confidence patterns
- On conflict: add to `conflicts.md`, surface to user on next interaction

**Key engineering challenges**:
1. **Context budget allocation**: How much window to give vault vs. current task vs. examples?
2. **Staleness detection**: When does a preference become outdated? (Decay function)
3. **Cross-line learning**: Some preferences are global (tone), some are line-specific (topics). How to share without contaminating?
4. **Embedding freshness**: Vault changes frequently. RAG embeddings must stay in sync.

**User-facing taste perception** (vault is NEVER exposed raw):

The vault is internal infrastructure. Users see effects, not data:

1. **Inline Attribution**: Per-content annotations ("疑问句开头 — learned from your 3rd edit"). Shows learning is happening without exposing the rule database. Natural language summaries only, not structured exportable data.

2. **Taste Score**: Abstract 0-100% match score displayed on dashboard. Higher = system understands you better. Creates perceived value without revealing mechanism. Score methodology is opaque.

3. **No "view all preferences" page**: Intentionally omitted. Raw vault data IS the moat — exposing it enables migration to competitors.

4. **Evolution highlights**: Weekly notification like "This week I learned: you prefer shorter paragraphs on XHS (3 edits confirmed)". Drip-fed insights, not bulk export.

### 3.6 Onboarding

**Flow**:
1. Sign up → Choose platforms
2. Define content line(s) (topic/niche)
3. Set style preferences (tone, length, visual style)
4. Add competitor accounts to watch list
5. Connect platforms (QR scan via remote browser / OAuth for WeChat)
6. Generate first content → Preview → First-week free publishing

---

## 4. Pricing Model

### 4.1 Strategy

**Core principle**: Base price BELOW competitors. Scale exponentially with usage. Retention through taste memory (switching cost), not lock-in.

**Competitor pricing landscape** (confirmed via research):
- 易媒助手: ¥48/month (basic), ¥58 (mid), ¥198 (high) — 70+ platforms, AI writing (limited)
- 蚁小二: ¥59/month — 40+ platforms, no AI
- 融媒宝: ~¥50-80/month — multi-platform, recently added DeepSeek AI
- 讯飞绘文: FREE — AI generation + multi-platform publish (low quality AI)
- AI writing tools (笔灵/秘塔): ¥23-48/month — no publishing
- MultiPost: FREE (open source) — browser extension, no AI

**Market gap**: NO competitor offers taste learning / style memory. This is TasteCraft's sole differentiator.

**Our positioning**: ¥79 monthly / ¥49 annually — undercuts "分发+AI写作" combo cost (¥48+¥23=¥71) while adding taste evolution as unique value.

**Biggest threat**: 讯飞绘文 (free, AI + publish). Mitigation: Claude >> 讯飞星火 in content quality; taste learning creates switching cost absent in free tools.

### 4.2 Pricing Structure

**Free Tier**:
- 10 finalized articles / month
- Publishing enabled ONLY during first week after registration
- Full preview + editing
- 1 content line, 1 platform
- Purpose: Experience complete loop → convert to paid

**Usage-based (exponential scaling)**:

| Dimension | Tier 1 | Tier 2 | Tier 3 | Multiplier |
|-----------|--------|--------|--------|------------|
| Monthly posts | 30 | 100 | 300 | ×1 → ×2.5 → ×7 |
| Platforms | 1 | 3 | 5 | ×1 → ×2 → ×4 |
| Content lines | 1 | 3 | 5 | ×1 → ×2.5 → ×6 |

**Base price**: ¥79/month | ¥588/year (¥49/month — undercuts all competitors)

**Annual pricing logic**: ¥49/month < 蚁小二(¥59) < 易媒初级(¥48 but no AI) while offering AI generation + taste learning that no competitor has.

**Pricing examples**:
- Minimal user (1 platform, 30 posts): ¥79/month
- Growing user (3 platforms, 100 posts): ¥79 × 2 × 2.5 = ¥395/month
- Power user (5 platforms, 300 posts, 3 lines): ¥79 × 4 × 7 × 2.5 = ¥5,530/month

### 4.3 Taste Monitoring Add-on

Premium layer on top of base service: +40% to +200%.

| Tier | Competitor Accounts | Price Uplift | Features |
|------|--------------------:|:------------:|----------|
| Basic Monitoring | 10 | +40% | Daily competitor posts |
| Pro Monitoring | 30 | +100% | + Trend reports + topic suggestions |
| Enterprise Monitoring | 50+ | +200% | + Taste evolution + lane analysis |

---

## 5. Technical Architecture

### 5.1 Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Frontend** | Vite + React 19 + TypeScript 5.9 | Existing codebase, SPA sufficient |
| **Styling** | Tailwind CSS 4 + design-taste-frontend standards | Anti-generic, high-end UI |
| **State** | Zustand + TanStack Query | Lightweight, proven |
| **Editor** | Tiptap | L2 micro-edit, not heavy Notion-clone |
| **Remote Browser UI** | noVNC (WebSocket stream) | User sees platform login page on our site |
| **Backend API** | FastAPI + Pydantic v2 | Python ecosystem, rapid development |
| **Browser Automation** | Camoufox (MVP) → AdsPower (production) | Patchright alone insufficient for XHS TLS fingerprinting |
| **AI Engine** | Anthropic Python SDK (Claude) | Direct SDK, no framework lock-in |
| **Data Collection** | TikHub Python SDK | 5-platform coverage, $55/month |
| **WeChat Publish** | wechatpy | Official API, most reliable |
| **Database** | PostgreSQL | Multi-tenant SaaS |
| **Cache/Queue** | Redis + Celery | Async tasks, rate limiting |
| **Scheduling** | Celery Beat | Cron-based content + publish cycles |
| **Deployment** | Docker Compose → K8s | Start simple, scale later |

### 5.2 Frontend Design Standards

Per `design-taste-frontend` skill:

**Typography**: Geist / Outfit / Cabinet Grotesk (Inter banned)
**Color**: Max 1 accent color, saturation < 80%, no AI purple/blue
**Layout**: No centered hero, force split/asymmetric, CSS Grid first
**Cards**: No generic rounded card boxes
**Animation**: transform + opacity only, Framer Motion
**Interaction**: Full state cycle (loading / empty / error / haptic feedback)
**Banned patterns**: 3-column icon grids, gradient buttons, generic templates

### 5.3 Remote Browser Architecture

**Feasibility verdict**: Conditional YES. Patchright alone is insufficient for XHS (lacks TLS/Canvas/WebGL fingerprint spoofing). Requires commercial-grade anti-detect solution.

**Phased approach**:

| Phase | Solution | Accounts | Cost/month |
|-------|----------|----------|-----------|
| MVP | Camoufox (8.3K stars, C++ fingerprint mods, open-source) + Patchright fallback | 10-100 | ~¥2,700 (open-source path) |
| Scale | Camoufox + GoLogin ($24/100 profiles) commercial fallback | 100-500 | ~¥4,000-6,000 |
| Enterprise | K8s + AdsPower/Nstbrowser + auto-scaling | 500+ | Custom |

**Open-source stack** (recommended for early growth):
- Browser engine: Camoufox (C++ native fingerprint, Firefox-based, Playwright native, Docker+Headless)
- Chromium fallback: Patchright (for platforms requiring Chrome UA)
- CAPTCHA: Botright (open-source, GeeTest 50-100% success)
- Fingerprint data: chrome-fingerprints (real browser fingerprint database)
- Proxy: 快代理 private proxy + self-built sticky session pool (~¥2,000/month for 100 users)
- Commercial fallback: GoLogin $24/month (if open-source gets detected)

**Per-user infrastructure cost** (open-source path): ~¥27/user/month (100 users)
**Break-even**: At ¥49/month pricing, profitable from ~150 users onward

**XHS detection layers** (must defeat all):
1. JS environment (`navigator.webdriver`, injected objects)
2. Device fingerprint (Canvas, WebGL, AudioContext)
3. TLS fingerprint (JA3/JA4) ← biggest challenge
4. Behavioral analysis (mouse trajectory, typing rhythm, page dwell time)
5. IP reputation (datacenter IPs flagged immediately)
6. Cookie-device binding

**Session persistence strategy**:

| Strategy | Method | Effect |
|----------|--------|--------|
| Fixed Profile | Each account bound to fixed fingerprint | Consistent device identity |
| Fixed IP | Sticky residential proxy per account | No IP jumping |
| Keep-alive | Simulate browsing every 1-2 days | Maintain session activity |
| Cookie refresh | Proactively visit before expiry | Extend lifetime |
| Graceful degrade | Auto-notify user when session dies | Business continuity |

**Session survival rates**:
- 7 days: 90%+ (no re-auth needed)
- 14 days: 70-80%
- 30 days: 50-60% (frequent keep-alive required)

**Login flow (noVNC/Guacamole)**:

```
User clicks "Connect XHS" on our website
         │
         ▼
Server creates anti-detect browser instance (Camoufox/AdsPower Profile)
         │
         ▼
Apache Guacamole streams browser viewport via WebSocket
         │
         ▼
User sees XHS login page on our website, scans QR code
         │
         ▼
Session (cookie + fingerprint profile) saved server-side
         │
         ▼
Instance goes to sleep (release RAM)
         │
         ▼
On publish: wake instance with same Profile → execute → sleep
         │
         ▼
Session check: daily keep-alive; re-auth notification when expired
```

**Publish flow (automated)**:
1. Celery task triggers → pull from publish queue
2. Scheduler allocates browser instance (reuse stored Profile + fingerprint)
3. Load cookie → verify session validity
4. Execute publish with human-like behavior simulation (random delays, mouse curves, typing speed variation)
5. Record result → release instance

**Infrastructure architecture (100 users)**:

```
[API Server: 4vCPU/16GB ~¥500/month]
         │
    [Redis + Celery]
         │
    [Browser Scheduler]
     ╱       ╲
[Node 1]  [Node 2]  [Node 3]
8vCPU/32GB each (~¥900/month each)
30-40 concurrent instances per node
         │
    [Residential Proxy Pool]
    100 sticky IPs (~¥1,500-3,000/month)
```

**Key constraint**: Must deploy in China region (Alibaba Cloud / Tencent Cloud) for:
- Low latency noVNC streaming (50-150ms same-region vs 200-500ms cross-region)
- Chinese residential IP availability
- Platform IP reputation

**Cost per user**: ~200-500MB RAM per active browser instance.
**Optimization**: Instance pool with on-demand wake (not 100 always-on instances). Peak concurrent: ~15-30 during publish windows (12:00/18:00/21:00).

### 5.4 Data Flow

```
┌─────────────────────────────────────────────────┐
│                   WRITE PATH                     │
│                                                  │
│  User config → AI generates → User previews     │
│  → User edits (diff captured) → Confirms        │
│  → System publishes via Patchright/wechatpy      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│                   READ PATH                      │
│                                                  │
│  TikHub polls published content + metrics        │
│  TikHub polls competitor accounts daily           │
│  → Data stored in PostgreSQL                     │
│  → Taste evolution engine processes signals       │
│  → Updated taste profile injected into next gen  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│                  LEARNING PATH                   │
│                                                  │
│  User edit diffs → Immediate preference update   │
│  Performance data → Reinforce/adjust style       │
│  Competitor trends → Topic/format suggestions    │
│  → All feed into taste profile                   │
│  → Profile injected as system prompt context     │
└─────────────────────────────────────────────────┘
```

---

## 6. User Journey & Experience Design

### 6.1 Complete User Journey Map

```
Discovery → Onboarding → First Content → Daily Use → Power User → Retention
```

34 touchpoints across 6 phases:

### 6.2 Phase 1: Discovery & Signup

**① Landing Page**
- Core value in 5 seconds: "越用越懂你的内容合伙人"
- Demo: paste your own content → AI instantly mimics your style (no signup needed)
- Social proof: before/after taste evolution examples
- Competitive comparison: "不是工具，是懂你的搭档"

**② No-signup Demo (Taste Test)**
- User pastes 1 paragraph they wrote → system analyzes style in 10 seconds
- Returns: "你的风格特征：[犀利观点型 / 疑问句开头 / 短段落]"
- Then generates a sample paragraph "in your style"
- This is the first aha moment — before signup

**③ Registration**
- WeChat scan / phone number / email
- Minimal friction — just phone + verification code
- Immediately enter onboarding, not a blank dashboard

### 6.3 Phase 2: Onboarding (Before First Content)

Total time: 13-20 minutes. This is the MOST critical phase for a taste-driven product.

**④ Lane Positioning Dialogue (2 min)**

```
System: 你主要在哪些平台发内容？
User:   [多选] 小红书 / 微信公众号

System: 你的内容领域是什么？
User:   [自由输入] "AI 创业和产品思考"

System: 你的目标读者是谁？他们的痛点是什么？
User:   "想创业但不知道从哪开始的技术人"

System: 你希望读者看完后有什么感受/行动？
User:   "觉得我说的靠谱，想关注我看更多"
```

**⑤ Style Deep Dialogue (5-8 min)**

```
System: 以下哪种风格最接近你？
        [展示 4 个风格样本]
        A. 专业严谨："数据显示..."
        B. 对话轻松："你有没有想过..."
        C. 故事驱动："上周我遇到一件事..."
        D. 观点犀利："说实话，大多数人都错了..."
User:   D

System: 你的犀利是"温和揭示真相"还是"直接怼"？
User:   温和但坚定

System: 绝对不用的表达？
User:   emoji、"家人们"、"宝子们"

System: 写内容时，先给结论还是先铺垫？
User:   先结论

System: 段落偏好？
User:   短段落，一段一个观点
```

**⑥ Content Import (3-5 min, skippable)**

```
System: 导入已发布的内容，让我更快理解你：
        1. 粘贴小红书/公众号主页链接（推荐）
        2. 上传文件 (Word/MD/txt)
        3. 跳过

User:   [粘贴小红书主页链接]

System: 正在分析你的 23 篇笔记...
        [30 秒异步分析]
        
        分析完成！风格特征：
        ✓ 标题偏好：疑问句(65%) + 数字列表(20%)
        ✓ 段落长度：偏短（均 40 字/段）
        ✓ 常用句式："说实话..." "真正重要的是..."
        ✓ 避免使用：emoji、感叹号连用
        ✓ 内容结构：观点→案例→金句
        
        准确吗？有修正吗？
User:   准确！
```

Import mechanism:
- XHS/Weibo/Zhihu: TikHub API auto-fetch by user profile URL
- WeChat MP: user provides article links (TikHub fetch content)
- Manual: file upload (Word/MD/txt), max 50 pieces

Analysis pipeline:
- Extract: sentence patterns, vocabulary preferences, paragraph structure, topic distribution
- Generate: initial taste vault documents (tone.md, structure.md, vocabulary.md)
- Present: summary to user for confirmation/correction

**⑦ Competitor Setup (2-3 min, deferrable)**

```
System: 你关注/想对标的同领域账号？
        [搜索框 + 热门推荐]

User:   [搜索添加 3 个账号]

System: 正在分析这 3 个账号...
        你可以先继续，结果几分钟后出现在仪表盘。
```

Initial competitor analysis (async, 2-5 min):
- Fetch recent 50 posts per competitor (TikHub)
- Extract: content themes, posting frequency, engagement patterns, style characteristics
- Generate: competitors/*.md vault documents
- Identify: lane baseline (what topics/hooks work in this niche)

**⑧ Platform Connection**

```
System: 连接你的发布账号：
        [微信公众号] → OAuth 授权（官方API）
        [小红书] → 点击"连接" → 远程浏览器扫码
        [微博] → 点击"连接" → 远程浏览器扫码
```

Via noVNC/Guacamole streaming for XHS/Weibo (described in Section 5.3).

**⑨ Initial Vault Construction**

System automatically builds initial Taste Vault from all gathered signals:
- Dialogue answers → style/tone.md, style/structure.md, preferences/explicit-rules.md
- Imported content analysis → style/vocabulary.md, preferences/patterns.md
- Competitor analysis → competitors/*.md, competitors/lane-trends.md
- Platform info → context/brand.md, context/audience.md

Duration: built progressively during onboarding, fully constructed by end of step ⑧.

**⑩ Aha Moment: First Content Generation (1-2 min)**

```
System: 基于你的品味画像 + 当前赛道热点，建议今天写：
        "为什么 95% 的 AI 创业者都在做错事"
        
        要生成试试看吗？
User:   好的

[流式生成，逐段显示，用户的风格特征立即体现在第一句]

System: 这是根据你的品味写的第一篇。
        提示：你每次编辑，我都在学习。
        改得越多，下一次越像你。
```

### 6.4 Phase 3: Co-Creation Flow (Daily Use)

This is NOT "generate → approve". It's a collaborative creative process.

**⑪ Content Initiation (User gives direction)**

Three entry points:
1. **AI suggests**: System proposes 3 topics based on lane trends + schedule
2. **User specifies**: "我想写关于 X 的内容，重点 Y，参考 Z"
3. **Reference-based**: User pastes a link → "写一篇类似这个的，但用我的风格"

```
System: 今天有 3 个选题建议：
        1. [热点] "OpenAI 刚发布了 X，你的赛道怎么看？"
        2. [系列] 上周"创业工具"系列的第 3 篇
        3. [竞品灵感] 竞品 A 昨天发了一篇爆款，角度是...
        
        选一个？还是你有自己的想法？
User:   选 1，但重点聊对创业者的实际影响，不要太技术
```

**⑫ Multi-variant Generation**

System generates 2-3 approaches for user to choose:
```
System: 我准备了 3 个切入角度：
        A. [观点犀利] "OpenAI 的新功能对 99% 创业者毫无意义"
        B. [实用指南] "3 个方法让 OpenAI 新功能为你赚钱"
        C. [深度分析] "从 OpenAI 这步棋看 AI 创业的下一个拐点"
        
        哪个方向展开？
User:   A，但别太绝对，"毫无意义"改成"还没想清楚"
```

**⑬ Streaming Generation with Live Intervention**

```
[AI begins streaming output, paragraph by paragraph]

User can:
- Let it run (no intervention)
- Click "停" → AI stops, asks "哪里不对？"
- Type in chat: "这段太长了" → AI immediately revises
- Highlight text → floating menu: "重写 / 缩短 / 扩展 / 换语气"
```

**⑭ Co-Creation Workspace (Core UI)**

```
┌─────────────────────────────────────────────────┐
│  内容编辑器（左 60%）           创意对话（右 40%）│
│  ┌────────────────────────┐  ┌────────────────┐│
│  │ [实时编辑 - Tiptap]     │  │ AI: 开头用了   ││
│  │                         │  │ 反常识切入，   ││
│  │ 选中文字 → 浮动工具条   │  │ 你觉得够吸引？ ││
│  │ [重写] [缩短] [扩展]    │  │                ││
│  │ [换语气] [更像我]       │  │ User: 好，但   ││
│  │                         │  │ 第三段太长了   ││
│  │ 每段旁边:               │  │                ││
│  │ [🔄重新生成此段]         │  │ AI: 已拆分成   ││
│  │ [💡归因: "来自你第3次    │  │ 两段并加了     ││
│  │   修改的偏好"]          │  │ 小标题。       ││
│  └────────────────────────┘  └────────────────┘│
│                                                  │
│  风格快调（底部）                                 │
│  正式 ◉───────○ 随意  │  长 ○───────◉ 短       │
│  理性 ○───◉───○ 感性  │  专业 ◉───────○ 通俗   │
└─────────────────────────────────────────────────┘
```

**⑮ Natural Language Feedback (not just text editing)**

Beyond direct text editing, users can give meta-feedback:
- "整体太正式了，轻松点"
- "保持这种风格，但换个话题"
- "参考竞品 X 的这篇爆款结构"
- "像我上周那篇最火的笔记那样写"

System interprets these as instructions and regenerates relevant sections.

**⑯ Version History & Rollback**

- Every generation/edit creates a version
- User can compare versions side-by-side
- Partial rollback: "keep v2's opening but use v3's conclusion"
- Version diffs are all captured for taste learning

**⑰ Cross-Platform Adaptation**

When user confirms content for one platform:
```
System: 这篇公众号长文已确认。
        要自动适配其他平台吗？
        
        [小红书版] 精华摘要 + 轮播图文案 (预览)
        [微博版] 核心金句 140 字 (预览)
        
        每个版本可独立编辑，互不影响。
```

One piece → multiple platform-adapted versions, each independently editable.

**⑱ Visual Content Creation**

For image-first platforms (XHS):
- **Image source strategy**:
  - AI generation (DALL-E / Stable Diffusion) for concept images
  - User upload for product photos / screenshots
  - Template-based: brand-consistent cards with text overlay
- **Carousel generation**: System suggests slide structure + text per slide
- **Cover image**: Auto-generate with title text overlay, brand colors from taste vault
- **Style consistency**: Visual preferences stored in vault (style/visual.md)

```
System: 这篇小红书笔记建议 6 张轮播图：
        1. 封面: 大标题 + 吸引力副标
        2-5. 每张一个核心观点
        6. 总结 + CTA
        
        要我用你的品牌色(深蓝+白)生成模板吗？
User:   好的，但字体用更粗的
```

**⑲ Preview & Confirm**

Dual preview:
1. Our platform preview (WYSIWYG, editable)
2. Native platform preview note: "以原生平台渲染为准"

```
System: 预览确认：
        [小红书预览] [微信预览] [微博预览]
        
        ✓ 内容已推送到小红书草稿箱
        → 你可以打开小红书 App 查看最终效果
        
        [确认发布] [稍后发布] [定时: ___]
```

**⑳ Publish Execution & Status**

After user confirms:
- System executes publish via Patchright/wechatpy
- Real-time status: queued → publishing → success/failed
- On failure: auto-retry once → if still fails, notify user with reason + manual fallback option

### 6.5 Phase 4: Daily Touchpoints & Notifications

**㉑ Daily Digest Push**

Via WeChat service account notification / email / in-app:
```
[每日 8:30]
今天有 2 篇内容等你审阅：
1. "AI 创业者的 3 个认知误区" — 已生成，待确认
2. "周三系列第 4 篇" — 已生成，待确认

昨日发布表现：
• "为什么95%..." — 阅读 1,234 | 点赞 89 | 收藏 56
```

**㉒ Publish Status Notification**
- Success: "✓ 已发布到小红书 + 微信，查看链接"
- Failure: "⚠️ 小红书发布失败(Session 过期)，点击重新连接"

**㉓ Competitor Alert**
```
[周三 10:00]
竞品动态：
• 账号 "某某" 昨天发了一篇爆款(1.2万赞)
  话题：[链接] 角度是...
  要借鉴这个角度写一篇吗？ [是] [否]
```

**㉔ Taste Evolution Weekly Report**
```
[每周日 20:00]
本周品味进化报告：
• 学到了 3 条新偏好：
  1. "小红书标题用反问句效果更好"(置信度 85%)
  2. "段落控制在 35 字以内"(置信度 72%)
  3. "避免用'其实'"(置信度 60%)
• Taste Score: 67 → 71 (+4)
• 本周最佳内容：[标题]，表现超赛道均值 40%
```

**㉕ Session Expiry Warning**
```
[距离过期 2 天]
⚠️ 小红书登录即将过期，请在 2 天内重新扫码
[立即重新连接]
```

### 6.6 Phase 5: Content Calendar & Planning

**㉖ Calendar View**

```
┌─────────────────────────────────────────┐
│  5月 第3周                    [月/周/日] │
│                                          │
│  周一    周二    周三    周四    周五     │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐  │
│  │ ✓  │ │ 📝 │ │ 🕐 │ │    │ │    │  │
│  │已发布│ │待审阅│ │定时 │ │ +  │ │ +  │  │
│  │"AI..." │ │"3个"│ │"周三"│ │新建│ │新建│  │
│  └────┘ └────┘ └────┘ └────┘ └────┘  │
│                                          │
│  热点日历: 5/20 世界蜜蜂日 | 6/1 儿童节   │
└─────────────────────────────────────────┘
```

Features:
- Drag-and-drop scheduling
- Batch topic planning: "这周 5 个话题一起定"
- Series management: linked content pieces
- Holiday/hot-event calendar pre-loaded
- Optimal posting time suggestions (from analytics)

**㉗ Batch Topic Generation**

```
User: 帮我规划下周 5 篇内容
System: 基于你的赛道趋势和竞品动态，建议：
        周一: [热点跟进] "OpenAI 新发布..."
        周二: [系列续写] "创业工具推荐 #4"
        周三: [个人观点] "我为什么不看好..."
        周四: [实用教程] "3步搞定..."
        周五: [互动] "你们怎么看..."
        
        确认后我会逐篇生成，你再逐一审阅。
```

### 6.7 Phase 6: Analytics Dashboard

**㉘ Performance Overview**

```
┌─────────────────────────────────────────────────┐
│  本周数据概览                                     │
│                                                  │
│  总阅读: 12,450 (+23%)  总互动: 891 (+15%)       │
│  最佳内容: "AI创业的3个误区" (ROI: 4.2x)          │
│  最佳时段: 周二 18:00 (互动率最高)                │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  [折线图: 7日阅读量趋势, 分平台]           │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  品味关联洞察:                                    │
│  • 疑问句标题 vs 陈述句: +40% 点击率             │
│  • 短段落(<40字) vs 长段落: +25% 完读率          │
│  • 周二发布 vs 周五: +60% 互动                   │
└─────────────────────────────────────────────────┘
```

**㉙ Cross-Platform Comparison**
- Same topic performance on different platforms
- Platform-specific optimization suggestions
- "这篇在小红书火了但公众号表现平平，因为..."

**㉚ Competitor Benchmark**
- Your content vs competitor average (engagement rate)
- Gap analysis: what competitors do that you don't
- Opportunity alerts: topics competitors haven't covered

### 6.8 Phase 7: Edge Cases & Recovery

**㉛ Quality Dissatisfaction**

If user rejects/heavily edits 3+ consecutive pieces:
```
System: 我注意到最近几篇你改动很大。
        是不是哪里偏了？我们可以：
        1. 重新对话调整风格方向
        2. 导入一篇你最满意的近期作品，让我重新学习
        3. 看看哪些偏好需要修正 [查看当前偏好]
```

**㉜ User Goes Inactive (7+ days)**

Recall strategy:
- Day 7: "你的内容线已暂停 7 天，竞品在这期间发了 X 篇"
- Day 14: "赛道出现新趋势 [热点]，要不要写一篇？"
- Day 30: "你的品味画像仍在，随时回来继续"

**㉝ Platform Account Banned**

```
System: ⚠️ 小红书发布失败，可能账号受到限制。
        建议操作：
        1. 手动登录小红书检查账号状态
        2. 如果是登录过期 → [重新连接]
        3. 如果是内容违规 → 查看平台通知
        4. 如果是自动化检测 → 暂停发布 48h，切换到手动模式
        
        注意：我们已暂停该账号的自动发布以保护你。
```

**㉞ Publish Failure & Retry**
- Auto-retry once on transient failure
- On persistent failure: queue for next window + notify user
- On session expiry: prompt re-auth via noVNC

### 6.9 Phase 8: Upgrade & Payment

**㉟ Free Quota Exhaustion**

```
System: 本月 10 篇免费额度已用完。
        你的品味画像已积累 12 条偏好 — 系统越来越懂你了。
        
        升级基础版 ¥49/月：
        • 无限生成 + 自动发布
        • 品味持续进化
        • 你积累的偏好数据不会丢失
        
        [立即升级] [下月再说]
```

**㊱ Trial Week Expiry**

Day 6 notification:
```
System: 试用期还剩 1 天。这周你的品味进化成果：
        • 学到了 8 条偏好
        • 发布了 4 篇内容
        • 平均互动率超赛道均值 20%
        
        付费继续？品味数据越积累价值越大。
        [升级 ¥49/月] [查看方案]
```

**㊲ Payment Integration**
- WeChat Pay + Alipay (primary for China market)
- Stripe (international backup)
- Auto-renewal with notification 3 days before
- Invoice generation (企业客户)

**㊳ Plan Upgrade UX**
- Clear comparison: current plan vs. upgrade
- Immediate effect (no waiting for next billing cycle)
- Prorated pricing for mid-cycle upgrades

### 6.10 Phase 9: Multi-Content-Line Management

**㊴ Content Line Switching**

```
┌────────────────────────────────┐
│  内容线:                        │
│  [AI创业 ✓] [美食探店] [阅读]   │
│  [+ 新建内容线]                 │
└────────────────────────────────┘
```

Each content line has:
- Independent taste vault (completely isolated preferences)
- Independent competitor watch list
- Independent content calendar
- Independent analytics

Switching is instant — like switching workspaces.

**New content line onboarding**: Abbreviated version of initial onboarding (skip platform connection, only need lane + style + competitors for new line).

### 6.11 Competitive Moat (vs Tool-Chain Approach)

Why TasteCraft over OpenClaw / Claude Code / Hermes for technical users:

| Dimension | Generic AI Tools | TasteCraft |
|-----------|-----------------|------------|
| Memory | Session-based, resets | Persistent vault, compounds over time |
| Learning | User writes better prompts | System learns from every edit |
| Intelligence | User runs scripts manually | Automated competitor monitoring daily |
| Validation | User checks metrics manually | Automated performance → taste correlation |
| Time investment | Same effort every time | Decreasing effort (AI converges to user's voice) |

**Core positioning**: OpenClaw gives you capability. TasteCraft gives you **compounding understanding**.

> "越用越懂你的内容合伙人 — 你负责方向，它负责越写越像你。"

The moat is NOT features (copyable). The moat is:
1. **Taste data asset** — 6 months of edits cannot be exported or replicated
2. **Three-way closed loop** — your style × lane intelligence × performance validation
3. **Decreasing marginal effort** — the more you use it, the less you need to edit

---

## 7. Phased Roadmap

### 7.1 Phase 1: MVP (Week 1-12) — "能跑通的共创闭环"

Goal: One user can onboard → co-create one piece → publish → see data. Taste learning works.

| Module | MVP Scope | Cut from MVP |
|--------|-----------|--------------|
| **Onboarding** | Lane dialogue + style interview (text chat) + manual content paste (up to 5 pieces) + 1-3 competitor accounts | Auto-import via TikHub (manual URL paste instead) |
| **Co-Creation** | Tiptap editor + right-panel chat for NL feedback + streaming generation + select-and-rewrite | Multi-variant generation, style sliders, version rollback |
| **Taste Vault** | Core vault structure + harness engineering (always-inject + conditional) | RAG dynamic retrieval, cross-line learning |
| **Diff Learning** | Capture every edit + immediate pattern apply + per-platform isolation | Confidence decay, conflict resolution UX |
| **Publishing** | WeChat (wechatpy API) + XHS (Camoufox + Guacamole login) | Weibo, batch publish, retry automation |
| **Visual Content** | User uploads images + basic text overlay template (1 style) | AI image generation, multiple templates, brand kit |
| **Calendar** | Simple list view of scheduled/published content | Drag-drop calendar, batch planning, holiday alerts |
| **Analytics** | Basic metrics display (likes/reads/comments per post) | Taste correlation, competitor benchmark, trend charts |
| **Notifications** | Email only: publish success/failure + session expiry | Daily digest, competitor alerts, evolution weekly |
| **Payment** | WeChat Pay + Alipay, single plan (¥49/month) | Usage-based tiers, annual plans, enterprise |

**MVP delivers**: Onboard → Co-create → Publish to XHS + WeChat → Learn from edits → Repeat (improving each time).

**MVP does NOT deliver**: Competitor monitoring, multi-variant gen, analytics dashboard, mobile optimization, content calendar, Weibo.

---

### 7.2 Phase 2: Growth (Week 13-20) — "数据飞轮启动"

Goal: Close the data loop. Competitor intelligence feeds into generation. Analytics prove value.

| Module | Phase 2 Scope |
|--------|---------------|
| **Competitor Monitoring** | TikHub daily pull (XHS/Weibo/Zhihu/Douyin) + trend extraction + lane-trends.md auto-update |
| **Analytics Dashboard** | Full performance view + cross-platform comparison + taste correlation insights |
| **Notifications** | Daily digest push + competitor alerts + evolution weekly report |
| **Content Calendar** | Week/month drag-drop view + batch topic planning + optimal time suggestions |
| **Multi-Variant Gen** | Generate 2-3 approaches per topic, user picks direction to expand |
| **Visual Content v2** | 3-5 templates + brand color kit + AI-assisted image selection |
| **Onboarding v2** | Auto-import via TikHub (paste profile URL → auto-fetch) + competitor auto-analysis |
| **Diff Learning v2** | Confidence decay + conflict detection + "你之前偏好X，现在偏好Y" 确认UX |
| **Weibo Publish** | Camoufox, same architecture as XHS |

**Phase 2 delivers**: Full data loop (publish → metrics → correlate with taste → improve). Competitor intelligence injected into topic suggestions. User sees measurable improvement.

---

### 7.3 Phase 3: Scale (Week 21-30) — "产品成熟+增长引擎"

Goal: Polish, scale, monetize power users. Mobile. Advanced taste evolution.

| Module | Phase 3 Scope |
|--------|---------------|
| **Taste Vault v2** | RAG dynamic retrieval + cross-line learning (shared global prefs) + vault health monitoring |
| **Mobile** | Responsive web / PWA for review + approve on mobile |
| **Usage-based Pricing** | Exponential tiers (posts × platforms × lines) + taste monitoring add-on |
| **Landing Page + Demo** | No-signup taste test + SEO landing pages |
| **Version History** | Full version comparison + partial rollback |
| **Style Sliders** | Real-time tone adjustment (formal↔casual, long↔short) |
| **Advanced Scheduling** | Multi-timezone + optimal posting time AI + series management |
| **Team Collaboration** | Multi-user access + approval flow (basic) |
| **API / Integrations** | Webhook on publish + API for power users |
| **Recall & Retention** | Inactive user recall sequences + churn prediction |

**Phase 3 delivers**: Product-market fit validated, growth engine running, power users generating revenue via exponential pricing.

---

### 7.4 Feature Phase Matrix (Quick Reference)

| Feature | MVP | Phase 2 | Phase 3 |
|---------|:---:|:-------:|:-------:|
| Onboarding dialogue (text chat) | ✅ | Enhanced (auto-import) | — |
| Co-creation workspace | ✅ (basic) | ✅ (multi-variant) | ✅ (sliders + versions) |
| Diff learning | ✅ (immediate apply) | ✅ (confidence + decay) | ✅ (cross-line) |
| Taste Vault + harness | ✅ (static injection) | ✅ (conditional) | ✅ (RAG dynamic) |
| WeChat publish | ✅ | ✅ | ✅ |
| XHS publish | ✅ | ✅ | ✅ |
| Weibo publish | — | ✅ | ✅ |
| Visual content | ✅ (upload + 1 template) | ✅ (multi-template) | ✅ (AI generation) |
| Competitor monitoring | — | ✅ | ✅ |
| Analytics dashboard | — (basic metrics only) | ✅ | ✅ (advanced) |
| Content calendar | — (list view) | ✅ (calendar view) | ✅ (series + auto) |
| Notifications | ✅ (email, minimal) | ✅ (push, daily digest) | ✅ (smart recall) |
| Multi-variant generation | — | ✅ | ✅ |
| Mobile | — | — | ✅ (PWA) |
| Usage-based pricing tiers | — (flat ¥49) | — | ✅ |
| Team collaboration | — | — | ✅ (basic) |
| Landing page + demo | — | — | ✅ |
| No-signup taste test | — | — | ✅ |

---

### 7.5 Launch Strategy

**MVP launch**: Invite-only beta (50 users). Focus on onboarding quality and diff learning accuracy.

**Phase 2 launch**: Open beta. Focus on data loop proof (show users their taste is evolving + content is improving).

**Phase 3 launch**: Public launch. Focus on growth (landing page, referral, content marketing).

Key onboarding metric: Time from signup to aha moment (first content that feels like user's voice) < 20 minutes.

---

## 8. Competitive Moat

| Layer | Moat Type | Strength Over Time |
|-------|-----------|-------------------|
| Taste memory (edit diffs) | Data network effect | Exponential (more edits → better output → more usage) |
| Competitor monitoring | Intelligence accumulation | Linear (more data → better trends) |
| Three-way closed loop | System integration | Exponential (style × intelligence × validation) |
| Low base price | Pricing pressure | Constant (forces competitors to race to bottom) |
| Exponential usage pricing | Revenue scaling | Grows with user success |
| Decreasing user effort | Switching cost | The longer you use, the less you need to edit |

**Key insight**: Competitors can clone features overnight. They cannot clone 6 months of accumulated taste preferences for each user. This is TasteCraft's defensibility.

**vs Generic AI Tools** (OpenClaw, Claude Code, Hermes): These give capability, TasteCraft gives compounding understanding. A tool resets every session; TasteCraft compounds every interaction.

---

## 9. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Platform detects Patchright → bans | HIGH | Fallback to local helper; fingerprint tuning; conservative operation patterns |
| XHS session expires frequently | MEDIUM | Auto-detect + prompt user re-auth; keep-alive mechanisms |
| TikHub API becomes unavailable | MEDIUM | Abstract data layer; backup with MediaCrawler (self-hosted) |
| AI content quality insufficient | HIGH | Taste evolution + diff learning converge quality; human-in-loop always available |
| Pricing too low to cover browser infra | MEDIUM | Monitor unit economics; adjust base price; push power users to higher tiers |
| User churn before taste profile matures | HIGH | First-week full experience; immediate diff application (instant learning perception) |

---

## 10. Success Metrics

| Metric | Target (Month 3) | Target (Month 6) |
|--------|------------------|------------------|
| Registered users | 200 | 1,000 |
| Free→Paid conversion | 8% | 12% |
| Monthly churn (paid) | <10% | <7% |
| Avg edits per content | <2 (quality improving) | <1.5 |
| Publishing success rate | >90% | >95% |
| User taste profile depth | 15+ preferences | 30+ preferences |

---

## 11. Open Questions

- [x] Remote browser anti-fingerprint feasibility for XHS → **Feasible with Camoufox, ¥27/user**
- [x] Competitor product detailed comparison → **No competitor does taste learning**
- [x] TikHub WeChat MP actual API testing → **Limited: no list-by-account, search only**
- [x] Open-source anti-detect solutions → **Camoufox 8.3K stars, best option**
- [ ] Exact session duration per platform before re-auth needed (verify in production)
- [ ] Visual content generation pipeline (DALL-E vs SD vs template engine)
- [ ] Mobile responsiveness strategy (PWA vs responsive web)
- [ ] WeChat service account for push notifications (requires ICP filing)
- [ ] Legal/compliance for browser automation in China
- [ ] Payment integration (WeChat Pay + Alipay) licensing requirements

---

## Appendix A: Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-16 | Co-creation over automation | Product is collaborative partner, not set-and-forget tool |
| 2026-05-16 | Onboarding = deep dialogue | Must build taste vault BEFORE first generation |
| 2026-05-16 | Camoufox for anti-detect | 8.3K stars, C++ native, $390/month for 100 users |
| 2026-05-16 | ¥49 base viable | Per-user infra cost ¥27 (open-source), break-even ~150 users |
| 2026-05-16 | Moat is compounding understanding | vs tools that reset every session |
| 2026-05-15 | SaaS website (not CLI) | Customer research: users want guided review |
| 2026-05-15 | Remote browser over extension | Server-controlled, supports scheduling, zero user install |
| 2026-05-15 | Hybrid publish (API + Patchright + Helper) | Best reliability per platform |
| 2026-05-15 | TikHub for all READ operations | 5-platform coverage, $55/month, SDK ready |
| 2026-05-15 | Loosely coupled modules | Users can self-select, pricing scales with usage |
| 2026-05-15 | All Python | Ecosystem (Anthropic SDK, TikHub, Patchright) outweighs perf |
| 2026-05-15 | Vite + React (not Next.js) | SPA sufficient, existing codebase, no SEO need for dashboard |
| 2026-05-15 | Price below competitors | Usage-based exponential growth compensates low base |
| 2026-05-15 | Diff learning = core IP | Switching cost + quality improvement + retention |
| 2026-04-05 | Self-Use Edition first | Validate core assumption (deprecated by v3 pivot to SaaS) |

## Appendix B: Technology References

| Project | Stars | Use Case |
|---------|-------|----------|
| `dreammis/social-auto-upload` | 11K | Multi-platform publish reference |
| `patchright-python` | 1.3K | Anti-detect browser automation |
| `white0dew/XiaohongshuSkills` | 2.7K | XHS-specific automation |
| `leaperone/MultiPost-Extension` | 2.2K | Browser extension reference (fallback path) |
| `wechatpy/wechatpy` | 4.3K | WeChat Official Account API |
| `xhs_ai_publisher` | 1.9K | AI + XHS publish pattern |

---

_Last updated: 2026-05-15_
