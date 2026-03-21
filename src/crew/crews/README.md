# CrewAI Crews 模块

3 个核心 Crew 的实现，用于自媒体内容生产、发布和分析。

## 目录结构

```
crews/
├── __init__.py           # 模块导出
├── base_crew.py          # Crew 基类
├── content_crew.py       # 内容生产线
├── publish_crew.py       # 发布线
├── analytics_crew.py     # 分析线
├── examples.py           # 使用示例
└── README.md            # 本文档
```

## 核心 Crew

### 1. ContentCrew - 内容生产线

**流程**: TopicResearcher → ContentWriter → ContentReviewer

**职责**:
- 追踪热点，研究选题
- 创作原创内容
- 审核内容质量和合规性

**使用示例**:

```python
from src.crew.crews import ContentCrew, ContentCrewInput

# 创建 Crew
crew = ContentCrew.create(
    enable_human_review=True,  # 启用人工审核
    verbose=True,
)

# 准备输入
inputs = ContentCrewInput(
    industry="科技",
    keywords=["AI", "大模型", "ChatGPT"],
    target_platform="xiaohongshu",
    content_type="article",
    research_depth="standard",
)

# 执行
result = crew.execute(inputs)

# 检查结果
if result.is_success() and result.is_approved:
    print(f"标题: {result.content_draft['title']}")
    print(f"内容: {result.content_draft['content']}")
```

**输入参数**:
- `industry` (str): 行业领域
- `keywords` (List[str]): 关键词列表
- `target_platform` (str): 目标平台 (wechat, xiaohongshu, douyin, bilibili, zhihu, weibo)
- `content_type` (str): 内容类型 (article, video, image_post)
- `research_depth` (str): 研究深度 (basic, standard, deep)
- `enable_human_review` (bool): 是否启用人工审核

**输出结果**:
- `topic_report` (Dict): 选题报告
- `content_draft` (Dict): 内容草稿
- `review_report` (Dict): 审核报告
- `is_approved` (bool): 是否通过审核

---

### 2. PublishCrew - 发布线

**流程**: PlatformAdapter → [各平台 Publisher 并行]

**职责**:
- 将内容适配到各平台格式
- 并行发布到多个平台
- 管理发布状态和重试

**使用示例**:

```python
from src.crew.crews import PublishCrew, PublishCrewInput

# 创建 Crew
crew = PublishCrew.create(
    enable_retry=True,
    max_retries=3,
)

# 准备输入
inputs = PublishCrewInput(
    content_id="content_001",
    content_draft={
        "title": "AI 大模型的未来发展趋势",
        "content": "随着 ChatGPT 的爆火...",
        "summary": "探讨 AI 大模型的技术发展",
        "tags": ["AI", "大模型", "科技"],
    },
    target_platforms=["xiaohongshu", "weibo", "zhihu"],
    schedule_time=None,  # 立即发布
)

# 执行
result = crew.execute(inputs)

# 检查结果
if result.is_success():
    print(f"成功平台: {result.successful_platforms}")
    print(f"失败平台: {result.failed_platforms}")
    print(f"成功率: {result.data['summary']['success_rate']}")
```

**输入参数**:
- `content_id` (str): 内容 ID
- `content_draft` (Dict): 内容草稿数据
- `target_platforms` (List[str]): 目标平台列表
- `schedule_time` (Optional[str]): 定时发布时间
- `enable_retry` (bool): 是否启用失败重试

**输出结果**:
- `adapted_contents` (Dict): 各平台适配后的内容
- `publish_records` (List[Dict]): 发布记录列表
- `successful_platforms` (List[str]): 成功平台列表
- `failed_platforms` (List[str]): 失败平台列表
- `all_success` (bool): 是否所有平台都成功

---

### 3. AnalyticsCrew - 分析线

**流程**: DataAnalyst（采集）→ DataAnalyst（分析）→ DataAnalyst（建议）

**职责**:
- 采集各平台内容表现数据
- 分析数据趋势和模式
- 生成优化建议和策略调整

**使用示例**:

```python
from src.crew.crews import AnalyticsCrew, AnalyticsCrewInput

# 创建 Crew
crew = AnalyticsCrew.create()

# 准备输入
inputs = AnalyticsCrewInput(
    content_ids=["content_001", "content_002", "content_003"],
    time_range="7d",
    platforms=["xiaohongshu", "weibo"],
    metrics=["views", "likes", "comments", "shares"],
    report_format="json",
)

# 执行
result = crew.execute(inputs)

# 检查结果
if result.is_success():
    print(f"采集数据: {len(result.collected_data)} 条")

    # 关键发现
    for finding in result.key_findings:
        print(f"- {finding}")

    # 优化建议
    for rec in result.recommendations:
        print(f"- {rec}")

    # 生成 Markdown 报告
    print(result.to_markdown_report())
```

**输入参数**:
- `content_ids` (List[str]): 已发布内容 ID 列表
- `time_range` (str): 时间范围 (24h, 7d, 30d, 90d)
- `platforms` (Optional[List[str]]): 平台列表
- `metrics` (Optional[List[str]]): 指标列表
- `report_format` (str): 报告格式 (json, markdown)

**输出结果**:
- `collected_data` (List[Dict]): 采集的数据
- `analysis_report` (Dict): 分析报告
- `recommendations` (List[str]): 优化建议
- `top_performers` (List[Dict]): 表现最佳内容
- `underperformers` (List[Dict]): 表现不佳内容
- `key_findings` (List[str]): 关键发现

---

## 基类接口

### BaseCrew

所有 Crew 的基类，提供标准化接口。

**核心方法**:

```python
class BaseCrew(ABC):
    def execute(self, inputs: CrewInput) -> CrewResult:
        """执行 Crew"""

    def kickoff(self, **inputs) -> CrewResult:
        """便捷方法：执行 Crew"""

    @classmethod
    def create(cls, **kwargs) -> "BaseCrew":
        """工厂方法：创建 Crew 实例"""

    @abstractmethod
    def get_agents(self) -> List[Any]:
        """返回 Agent 列表"""

    @abstractmethod
    def get_tasks(self, inputs: CrewInput) -> List[Any]:
        """返回 Task 列表"""
```

**生命周期钩子**:

```python
def validate_inputs(self, inputs: CrewInput) -> tuple[bool, Optional[str]]:
    """验证输入参数"""

def pre_execute(self, inputs: CrewInput) -> None:
    """执行前钩子"""

def post_execute(self, result: CrewResult) -> CrewResult:
    """执行后钩子"""
```

---

## 数据类

### CrewInput

标准化输入数据类。

```python
@dataclass
class CrewInput:
    inputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Optional[Dict[str, Any]] = None
```

### CrewResult

标准化输出数据类。

```python
@dataclass
class CrewResult:
    status: CrewStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_outputs: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def is_success(self) -> bool:
        """检查执行是否成功"""

    def is_failed(self) -> bool:
        """检查执行是否失败"""
```

---

## 快速开始

### 方式 1: 使用 execute()

```python
from src.crew.crews import ContentCrew, ContentCrewInput

crew = ContentCrew.create()
inputs = ContentCrewInput(
    industry="科技",
    keywords=["AI"],
    target_platform="xiaohongshu",
)
result = crew.execute(inputs)
```

### 方式 2: 使用 kickoff()

```python
from src.crew.crews import ContentCrew

crew = ContentCrew.create()
result = crew.kickoff(
    industry="科技",
    keywords=["AI"],
    target_platform="xiaohongshu",
)
```

### 方式 3: 链式调用

```python
from src.crew.crews import ContentCrew

result = ContentCrew.create().kickoff(
    industry="科技",
    keywords=["AI"],
    target_platform="xiaohongshu",
)
```

---

## 端到端流程

完整的内容生产 → 发布 → 分析流程：

```python
from src.crew.crews import ContentCrew, PublishCrew, AnalyticsCrew

# 步骤 1: 内容生产
content_result = ContentCrew.create().kickoff(
    industry="科技",
    keywords=["AI", "大模型"],
    target_platform="xiaohongshu",
)

if not content_result.is_success():
    print(f"内容生产失败: {content_result.error}")
    exit(1)

content_draft = content_result.content_draft

# 步骤 2: 发布
publish_result = PublishCrew.create().kickoff(
    content_id="content_001",
    content_draft=content_draft,
    target_platforms=["xiaohongshu", "weibo"],
)

if not publish_result.is_success():
    print(f"发布失败: {publish_result.error}")
    exit(1)

# 步骤 3: 数据分析
analytics_result = AnalyticsCrew.create().kickoff(
    content_ids=["content_001"],
    time_range="24h",
)

if analytics_result.is_success():
    print(f"分析完成，发现 {len(analytics_result.key_findings)} 条关键洞察")
```

---

## 配置选项

### ContentCrew

```python
ContentCrew.create(
    enable_human_review=True,  # 启用人工审核
    verbose=True,              # 详细日志
    process=Process.sequential, # 执行流程
    memory=True,               # 使用记忆
    max_rpm=None,              # 每分钟最大执行次数
    llm="claude-sonnet-4-20250514",  # LLM 模型
)
```

### PublishCrew

```python
PublishCrew.create(
    enable_retry=True,         # 启用失败重试
    max_retries=3,             # 最大重试次数
    verbose=True,
    process=Process.sequential,
    memory=False,
    max_rpm=10,                # 限制发布速率
    llm="claude-sonnet-4-20250514",
)
```

### AnalyticsCrew

```python
AnalyticsCrew.create(
    verbose=True,
    process=Process.sequential,
    memory=True,
    max_rpm=30,
    llm="claude-sonnet-4-20250514",
)
```

---

## 错误处理

```python
from src.crew.crews import ContentCrew, CrewStatus

crew = ContentCrew.create()
result = crew.kickoff(industry="科技", keywords=["AI"])

if result.status == CrewStatus.COMPLETED:
    print("执行成功")
elif result.status == CrewStatus.FAILED:
    print(f"执行失败: {result.error}")
    print(f"执行时间: {result.execution_time}秒")
```

---

## 日志记录

所有 Crew 使用 `loguru` 记录日志：

```python
from loguru import logger

# Crew 会自动记录以下信息：
# - 执行开始/结束
# - 任务进度
# - 错误和异常
# - 执行时间

# 查看日志
logger.info("[ContentProduction] Starting execution")
logger.info("[ContentProduction] Execution completed with status: completed")
```

---

## 扩展 Crew

创建自定义 Crew：

```python
from src.crew.crews.base_crew import BaseCrew, CrewInput, CrewResult
from crewai import Task

class CustomCrew(BaseCrew):
    def get_crew_name(self) -> str:
        return "CustomCrew"

    def get_agents(self) -> List[Any]:
        # 返回 Agent 列表
        return [agent1, agent2]

    def get_tasks(self, inputs: CrewInput) -> List[Any]:
        # 返回 Task 列表
        return [task1, task2]

    def validate_inputs(self, inputs: CrewInput) -> tuple[bool, Optional[str]]:
        # 自定义验证逻辑
        return True, None
```

---

## 依赖

- `crewai[tools]>=0.80.0`
- `loguru` (日志)
- `src.agents` (Agent 模块)
- `src.tools` (工具模块)

---

## 更多示例

查看 `examples.py` 获取更多使用示例。
