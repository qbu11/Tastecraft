# 同步计划：workspace/crew-hotspot → C:\11projects\Crew

> 创建日期：2026-03-23
> 最后更新：2026-03-23
> 状态：待执行

## ⚠️ 重要提示

**在开始迁移前，请务必阅读以下文档：**

1. **[MIGRATION-RISKS.md](docs/MIGRATION-RISKS.md)** — 风险评估与缓解方案（必读）
2. **[DATABASE-REWRITE-GUIDE.md](docs/DATABASE-REWRITE-GUIDE.md)** — 数据库重写指南
3. **运行检查脚本：** `python scripts/pre_migration_check.py`

**关键风险（P0 - 必须解决）：**
- 🚨 数据库架构完全不兼容（WS 用 sqlite3，ORIG 用 SQLAlchemy）
- 🚨 缺失 HotspotDetectionCrew 和 ContentCreationCrew
- 🚨 gstack-browse 外部依赖可能不存在

**预计工作量：6-8 个工作日（44 小时）**

---

## 背景

开发过程中，部分新功能在 `C:\Users\puzzl\metabot_workspace\crew-hotspot`（以下简称 **WS**）中开发，
而正式项目在 `C:\11projects\Crew`（以下简称 **ORIG**）。两个目录的架构和包结构不同，
需要将 WS 中的新功能合并到 ORIG 中。

## 两个项目对照

| 维度 | ORIG (`C:\11projects\Crew`) | WS (`workspace/crew-hotspot`) |
|------|---------------------------|-------------------------------|
| Python 包 | `src/` 扁平布局 | `src/crew_hotspot/` 命名空间 |
| 包管理 | uv + pyproject.toml | pip + requirements.txt |
| Agent | 7 个专用 Agent 类 | 2 个简化 Agent |
| Crew | 5 个 Crew（含 analytics, publish） | 2 个 Crew（content, hotspot） |
| 平台工具 | 每平台独立文件（含海外平台） | 合并为单文件 |
| 数据库 | SQLAlchemy + aiosqlite | 自定义 SQLite ORM |
| 安全层 | JWT auth + audit + error handling | 无 |
| Schema | Pydantic 验证层 | 内联模型 |
| 测试 | 284 个测试用例 | 4 个测试文件 |

## 核心策略

**保留 ORIG 的架构优势，迁入 WS 的 8 个全新模块。**

ORIG 拥有的优势不动：完整 agent 体系、schema 验证层、auth/audit 安全层、284 个测试、海外平台支持。
WS 中独有的实用功能，适配 ORIG 的包结构后合并进来。

---

## Phase 1: 新增独立模块（无冲突，直接复制适配）

这 8 个模块在 ORIG 中完全没有对应物，可以安全新增。

### 架构适配规范

**必须遵循 ORIG 的 pattern：**
- ✅ 所有 import 用绝对路径 `from src.xxx import`（无相对导入）
- ✅ 日志用 `logger = logging.getLogger(__name__)`
- ✅ 配置从 `src.core.config import settings`
- ✅ 错误处理用 `Result[T]` pattern（`from src.core.error_handling import Result, success, error`）
- ✅ 自定义异常继承 `CrewException`（`from src.core.exceptions import CrewException`）
- ✅ 类型注解用 `X | None`（非 `Optional[X]`）
- ✅ 代码行长 100 字符
- ✅ 通过 `mypy --strict` 和 `ruff check`

### 1.1 Cookie 管理器
- **源文件**：`WS/src/crew_hotspot/cookie_manager.py` (365 行)
- **目标**：`ORIG/src/services/cookie_manager.py`
- **改动**：
  - `from crew_hotspot.xxx` → `from src.xxx`
  - `logging.getLogger(__name__)` 替换任何自定义 logger
  - 配置从 `settings` 读取（如有硬编码路径）
  - 补充类型注解（返回值、参数）
  - 异常处理改用 `Result[T]` pattern

### 1.2 Rate Limiter
- **源文件**：`WS/src/crew_hotspot/rate_limiter.py` (280 行)
- **目标**：`ORIG/src/services/rate_limiter.py`
- **改动**：
  - 适配 import
  - 补充类型注解
  - 考虑与 ORIG 的 `tenacity` 依赖整合（如有重复功能）

### 1.3 Retry 装饰器
- **源文件**：`WS/src/crew_hotspot/retry.py` (296 行)
- **目标**：`ORIG/src/utils/retry.py`
- **改动**：
  - 适配 import
  - **重要**：ORIG 已依赖 `tenacity>=9.0.0`，检查是否可直接用 tenacity 替代
  - 如保留自定义实现，需与 `src/core/error_handling.py` 的 retry 逻辑协调

### 1.4 任务队列
- **源文件**：`WS/src/crew_hotspot/task_queue.py` (287 行)
- **目标**：`ORIG/src/services/task_queue.py`
- **改动**：
  - 适配 import
  - SQLite 操作改用 SQLAlchemy（如 WS 用原生 sqlite3）
  - 补充类型注解

### 1.5 调度器
- **源文件**：`WS/src/crew_hotspot/scheduler.py` (372 行)
- **目标**：`ORIG/src/services/scheduler.py`
- **改动**：
  - 适配 import
  - 配置从 `settings` 读取（cron 表达式、时区等）
  - 补充类型注解
  - 日志用 `logger = logging.getLogger(__name__)`

### 1.6 Publish Engine V2（Chrome MCP 原生发布）
- **源文件**：`WS/src/crew_hotspot/publish_engine_v2.py` (371 行)
- **目标**：`ORIG/src/services/publish_engine_v2.py`
- **改动**：
  - 适配 import
  - 与 ORIG 的 `src/tools/platform/` 体系共存（不冲突）
  - 补充完整类型注解（mypy strict 要求）
  - 错误处理改用 `Result[T]` pattern

### 1.7 Data Collector（Chrome MCP 数据采集）
- **源文件**：`WS/src/crew_hotspot/data_collector.py` (558 行)
- **目标**：`ORIG/src/services/data_collector.py`
- **改动**：
  - 适配 import
  - **关键**：数据存储改用 ORIG 的 SQLAlchemy 模型（`HotTopic`, `Metrics`）
  - 补充类型注解
  - 错误处理改用 `Result[T]` pattern

### 1.8 Image Router（图片生成 API）
- **源文件**：`WS/src/crew_hotspot/api_routes/image_router.py` (269 行)
- **目标**：`ORIG/src/api/routes/images.py`
- **改动**：
  - 适配 import，对接 `src/services/image_generator.py`
  - 路由定义用 `router = APIRouter(prefix="/images", tags=["Images"])`
  - 返回类型统一为 `dict[str, Any]`（非 Pydantic Response Model）
  - 错误处理：404 用 `raise HTTPException(status_code=404)` 或 `return {"success": False, "error": "..."}`
  - 注册到 ORIG 的 `src/api/main.py`：`app.include_router(images.router)`

---

## Phase 2: 合并/升级已有模块

### 2.1 Database 模块

**WS 独有的 4 个表需要转换为 SQLAlchemy 模型。**

#### 模型定义规范（必须遵循）

**文件：`src/models/client.py`**

```python
"""客户管理模型"""
from uuid import uuid4
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class Client(Base, TimestampMixin):  # 双继承
    """客户表"""
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: f"client-{uuid4().hex[:12]}"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    industry: Mapped[str | None] = mapped_column(String(50))  # 用 | None，非 Optional
    description: Mapped[str | None] = mapped_column(Text)

    # 关系
    accounts: Mapped[list["Account"]] = relationship(
        "Account", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name={self.name})>"
```

**文件：`src/models/account.py`**

```python
"""账号管理模型"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class AccountStatus(str):  # 注意：模型侧枚举只继承 str，不继承 Enum
    """账号状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Account(Base, TimestampMixin):
    """账号表"""
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: f"account-{uuid4().hex[:12]}"
    )
    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.ACTIVE)
    is_logged_in: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 关系
    client: Mapped["Client"] = relationship("Client", back_populates="accounts")

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, platform={self.platform}, username={self.username})>"
```

**文件：`src/models/hot_topic.py`**

```python
"""热点话题模型"""
from uuid import uuid4
from sqlalchemy import String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class HotTopic(Base, TimestampMixin):
    """热点话题表"""
    __tablename__ = "hot_topics"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: f"topic-{uuid4().hex[:12]}"
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    rank: Mapped[int | None] = mapped_column(Integer)
    heat_score: Mapped[float | None] = mapped_column(Float)
    category: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    raw_data: Mapped[dict | None] = mapped_column()  # JSON 类型，SQLAlchemy 2.x 自动识别

    def __repr__(self) -> str:
        return f"<HotTopic(id={self.id}, platform={self.platform}, title={self.title[:30]})>"
```

**文件：`src/models/metrics.py`**

```python
"""数据指标模型"""
from uuid import uuid4
from sqlalchemy import String, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Metrics(Base, TimestampMixin):
    """数据指标表"""
    __tablename__ = "metrics"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: f"metric-{uuid4().hex[:12]}"
    )
    content_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_drafts.id", ondelete="SET NULL")
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    post_url: Mapped[str | None] = mapped_column(String(500))
    views: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    raw_metrics: Mapped[dict | None] = mapped_column()  # JSON

    @property
    def total_engagement(self) -> int:
        """总互动数"""
        return (self.likes or 0) + (self.comments or 0) + (self.shares or 0)

    def __repr__(self) -> str:
        return f"<Metrics(id={self.id}, platform={self.platform}, views={self.views})>"
```

#### 更新 `src/models/__init__.py`

```python
"""数据模型"""
from src.models.base import Base, TimestampMixin
from src.models.content import Content
from src.models.publish_log import PublishLog
from src.models.analytics import AnalyticsReport
from src.models.client import Client
from src.models.account import Account, AccountStatus
from src.models.hot_topic import HotTopic
from src.models.metrics import Metrics

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Content
    "Content",
    # Publish Log
    "PublishLog",
    # Analytics
    "AnalyticsReport",
    # Client & Account
    "Client",
    "Account",
    "AccountStatus",
    # Hotspot
    "HotTopic",
    "Metrics",
]
```

#### 创建 Alembic 迁移

```bash
cd /c/11projects/Crew
alembic revision --autogenerate -m "add client account hot_topic metrics tables"
alembic upgrade head
```

---

### 2.2 API 路由

**新增 2 个路由文件，遵循 ORIG 的路由范式。**

#### 文件：`src/api/routes/clients.py`

```python
"""客户管理路由"""
from typing import Any
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.client import Client
from src.schemas.client import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/", status_code=201)
async def create_client(client: ClientCreate) -> dict[str, Any]:
    """创建客户"""
    # TODO: 实现数据库操作（需要 get_db dependency）
    return {"success": True, "data": {"id": "client-xxx", **client.model_dump()}}


@router.get("/")
async def list_clients(skip: int = 0, limit: int = 100) -> dict[str, Any]:
    """列出所有客户"""
    # TODO: 实现数据库查询
    return {"success": True, "items": [], "total": 0}


@router.get("/{client_id}")
async def get_client(client_id: str) -> dict[str, Any]:
    """获取客户详情"""
    # TODO: 实现数据库查询
    # 404 处理：raise HTTPException(status_code=404, detail="客户不存在")
    return {"success": True, "data": {"id": client_id}}


@router.put("/{client_id}")
async def update_client(client_id: str, client_update: ClientUpdate) -> dict[str, Any]:
    """更新客户"""
    # TODO: 实现数据库更新
    return {"success": True, "data": {"id": client_id}}


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: str) -> None:
    """删除客户"""
    # TODO: 实现数据库删除
    pass
```

#### 文件：`src/api/routes/accounts.py`

```python
"""账号管理路由"""
from typing import Any
from fastapi import APIRouter

from src.schemas.account import AccountCreate, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post("/", status_code=201)
async def create_account(account: AccountCreate) -> dict[str, Any]:
    """创建账号"""
    return {"success": True, "data": {"id": "account-xxx", **account.model_dump()}}


@router.get("/")
async def list_accounts(
    client_id: str | None = None,
    platform: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """列出账号"""
    return {"success": True, "items": [], "total": 0}


@router.get("/{account_id}")
async def get_account(account_id: str) -> dict[str, Any]:
    """获取账号详情"""
    return {"success": True, "data": {"id": account_id}}


@router.put("/{account_id}")
async def update_account(account_id: str, account_update: AccountUpdate) -> dict[str, Any]:
    """更新账号"""
    return {"success": True, "data": {"id": account_id}}


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: str) -> None:
    """删除账号"""
    pass
```

#### Schema 定义

**文件：`src/schemas/client.py`**

```python
"""客户 Schema"""
from enum import Enum
from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    """客户基础 Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="客户名称")
    industry: str | None = Field(None, max_length=50, description="行业")
    description: str | None = Field(None, description="描述")


class ClientCreate(ClientBase):
    """创建客户"""
    pass


class ClientUpdate(BaseModel):
    """更新客户"""
    name: str | None = Field(None, min_length=1, max_length=100)
    industry: str | None = Field(None, max_length=50)
    description: str | None = None


class ClientResponse(ClientBase):
    """客户响应"""
    id: str
    created_at: str  # ISO 8601 格式
    updated_at: str

    model_config = {"from_attributes": True}
```

**文件：`src/schemas/account.py`**

```python
"""账号 Schema"""
from enum import Enum
from pydantic import BaseModel, Field


class PlatformType(str, Enum):  # Schema 侧枚举用 str + Enum
    """平台类型"""
    XIAOHONGSHU = "xiaohongshu"
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    BILIBILI = "bilibili"
    DOUYIN = "douyin"


class AccountStatusEnum(str, Enum):
    """账号状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class AccountBase(BaseModel):
    """账号基础 Schema"""
    client_id: str = Field(..., description="客户 ID")
    platform: PlatformType = Field(..., description="平台")
    username: str = Field(..., min_length=1, max_length=100, description="用户名")
    status: AccountStatusEnum = Field(default=AccountStatusEnum.ACTIVE, description="状态")


class AccountCreate(AccountBase):
    """创建账号"""
    pass


class AccountUpdate(BaseModel):
    """更新账号"""
    platform: PlatformType | None = None
    username: str | None = Field(None, min_length=1, max_length=100)
    status: AccountStatusEnum | None = None
    is_logged_in: bool | None = None


class AccountResponse(AccountBase):
    """账号响应"""
    id: str
    is_logged_in: bool
    last_login: str | None  # ISO 8601
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
```

#### 注册路由到 `src/api/main.py`

```python
# 在 imports 中添加
from src.api.routes import health, content, tasks, analytics, dashboard, research, search, clients, accounts, images

# 在路由注册部分添加
app.include_router(clients.router)
app.include_router(accounts.router)
app.include_router(images.router)  # Phase 1.8 的图片路由
```

#### 调度器集成（修改 `src/api/main.py`）

```python
from contextlib import asynccontextmanager
from src.services.scheduler import HotspotScheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import logging
    logger = logging.getLogger(__name__)

    # 启动时
    logger.info("Starting application...")

    # 初始化调度器
    scheduler = HotspotScheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduler started")

    yield

    # 关闭时
    logger.info("Shutting down application...")
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        logger.info("Scheduler stopped")


app = FastAPI(
    title="Crew Media Ops API",
    description="Multi-agent system for social media operations",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,  # 使用 lifespan 替代 on_event
)
```

---

### 2.3 Image Generator 工具

**文件：`src/tools/image_generator.py`**

- 从 `WS/src/crew_hotspot/tools/image_generator.py` 复制
- 适配 import：`from src.services.image_generator import ImageGenerator`
- 补充类型注解
- 确保符合 CrewAI Tool 规范

**文件：`src/services/image_generator.py`**

- ORIG 已有此文件（untracked），内容与 WS 相同
- 执行 `git add src/services/image_generator.py`

---

## Phase 3: 数据和配置文件

### 3.1 Cookie 数据
- `WS/data/cookies/*.json` → `ORIG/data/cookies/`
- 添加到 `.gitignore`（含敏感信息）

### 3.2 内容草稿
- `WS/data/drafts/*.md` → `ORIG/data/drafts/`
- 作为示例模板保留

### 3.3 生成的图片
- `WS/output_images/` → 不同步（运行时生成）
- 在 `.gitignore` 中添加 `output_images/`

### 3.4 依赖更新
- 在 `pyproject.toml` 的 dependencies 中添加：
  ```toml
  "pillow>=10.0.0",  # 图片生成
  ```
  （其他依赖如 apscheduler、httpx 等 ORIG 已有）

---

## Phase 4: 文档同步

### 4.1 新增文档
| WS 文档 | → ORIG 位置 |
|---------|------------|
| `DEPLOY.md` | `docs/DEPLOY.md` |
| `QUICKSTART.md` | `docs/QUICKSTART.md` |
| `PUBLISH.md` | `docs/PUBLISH.md` |
| `Dockerfile` | `Dockerfile` |
| `docs/feishu_upload_guide.md` | `docs/features/feishu-upload-guide.md` |
| `docs/*-image-research.md` | `docs/research/` |

### 4.2 更新 CLAUDE.md
- 将 WS 的新模块信息补充到 ORIG 的 CLAUDE.md 中
- 更新目录结构说明

---

## Phase 5: 测试补充

为新增模块编写测试，**必须遵循 ORIG 的测试 pattern**：
- 所有 fixture scope=function（每测试独立 DB）
- 用 in-memory SQLite：`create_engine("sqlite:///:memory:")`
- Base.metadata.create_all / drop_all 配对
- 使用 `@pytest.mark.unit` / `@pytest.mark.integration` 标记
- `asyncio_mode = "auto"`（无需手写 `@pytest.mark.asyncio`）
- 放在 `tests/unit/` 或 `tests/integration/` 下

| 新模块 | 测试文件 | 预期用例 | 标记 |
|--------|---------|---------|------|
| cookie_manager | `tests/unit/test_cookie_manager.py` | ~10 | unit |
| rate_limiter | `tests/unit/test_rate_limiter.py` | ~8 | unit |
| retry | `tests/unit/test_retry.py` | ~8 | unit |
| task_queue | `tests/unit/test_task_queue.py` | ~10 | unit |
| scheduler | `tests/unit/test_scheduler.py` | ~6 | unit |
| data_collector | `tests/integration/test_data_collector.py` | ~10 | integration |
| publish_engine_v2 | `tests/integration/test_publish_engine_v2.py` | ~8 | integration |
| image_router | `tests/unit/test_image_router.py` | ~6 | unit |
| clients route | `tests/unit/test_clients.py` | ~6 | unit |
| accounts route | `tests/unit/test_accounts.py` | ~6 | unit |

**测试样板（参考 ORIG 的 conftest 风格）：**

```python
"""tests/unit/test_cookie_manager.py"""
import pytest
from unittest.mock import MagicMock, patch

from src.services.cookie_manager import CookieManager


@pytest.mark.unit
class TestCookieManager:
    """Cookie 管理器测试"""

    def test_load_cookies(self) -> None:
        """加载 cookies"""
        manager = CookieManager()
        ...

    def test_save_cookies(self) -> None:
        """保存 cookies"""
        ...

    def test_cookie_expiry(self) -> None:
        """Cookie 过期检查"""
        ...
```

参考 WS 已有的 4 个测试文件中的测试用例，升级为 ORIG 的 conftest 风格。

**在 `tests/conftest.py` 中补充新的 fixture：**

```python
# 在已有 conftest.py 末尾添加

@pytest.fixture(scope="function")
def cookie_manager(tmp_path):
    """CookieManager fixture with temp data dir"""
    from src.services.cookie_manager import CookieManager
    return CookieManager(data_dir=str(tmp_path / "cookies"))


@pytest.fixture(scope="function")
def rate_limiter():
    """RateLimiter fixture"""
    from src.services.rate_limiter import RateLimiter
    return RateLimiter()
```

---

## 执行顺序

```
0. 迁移前准备                                    # ~1 小时
   - 运行 python scripts/pre_migration_check.py
   - 阅读 docs/MIGRATION-RISKS.md
   - 备份数据库和代码
   - 创建迁移分支

1. 阶段 1：基础设施（2 天）                       # ~16 小时
   - 创建 SQLAlchemy 模型
   - 创建 Service 层
   - 迁移独立模块（cookie_manager, rate_limiter, retry）
   - 编写单元测试

2. 阶段 2：核心功能（2 天）                       # ~16 小时
   - 重写 task_queue 为异步
   - 迁移 image_generator 和 API 路由
   - 编写集成测试

3. 阶段 3：高级功能（3 天）                       # ~24 小时
   - 创建 HotspotDetectionCrew
   - 重写 data_collector 为异步
   - 迁移 scheduler
   - 迁移 publish_engine

4. 阶段 4：测试和优化（1 天）                     # ~8 小时
   - 运行全量测试
   - 性能测试和优化
   - 文档更新

5. 合并和部署                                    # ~2 小时
   - 创建 PR
   - Code Review
   - 合并到 main
```

**详细执行计划见：[MIGRATION-RISKS.md - 分阶段执行计划](docs/MIGRATION-RISKS.md#分阶段执行计划)**

---

## 不同步的内容

以下 WS 文件**不需要同步**（ORIG 有更好的实现或不适用）：

| WS 文件 | 原因 |
|---------|------|
| `WS/src/crew_hotspot/agents/` | ORIG 有 7 个更完善的 Agent |
| `WS/src/crew_hotspot/crews/hotspot_crew.py` | 需要重新基于 ORIG 的 base_crew 实现 |
| `WS/src/crew_hotspot/models.py` | ORIG 有完整 schema 体系 |
| `WS/src/crew_hotspot/tools/platform_search.py` | ORIG 有更细粒度的平台工具 |
| `WS/src/crew_hotspot/tools/content_generation.py` | ORIG 有 content_tools.py |
| `WS/main.py` | ORIG 有自己的入口 |
| `WS/publish_service.py` | 功能已被 publish_engine_v2 覆盖 |
| `WS/generate_images.py` | 早期原型，功能已在 image_generator 中 |
| `WS/requirements.txt` | ORIG 用 pyproject.toml + uv |

---

## 风险点

1. **import 路径**：WS 用 `crew_hotspot.xxx`，ORIG 用 `src.xxx`，需逐文件检查并替换
2. **数据库架构差异**：WS 用自定义 ORM，ORIG 用 SQLAlchemy，data_collector 和 task_queue 需要适配
3. **测试兼容性**：ORIG 的 conftest.py 有 1042 行，新模块的测试需要兼容现有 fixture
4. **mypy strict**：ORIG 开启了 mypy strict，WS 代码缺少类型注解，需要补全
5. **依赖注入**：ORIG 的 `src/api/dependencies/__init__.py` 为空，路由中没有用 `Depends(get_db)`，需要先实现 get_db dependency 或直接在路由中创建 session
6. **错误处理一致性**：ORIG 有 `Result[T]` pattern，但部分路由直接返回 dict，需要统一风格
7. **调度器生命周期**：ORIG 用 `@app.on_event("startup")`，需改为 `lifespan` context manager（FastAPI 新版推荐）
8. **Retry 模块冲突**：ORIG 已依赖 `tenacity>=9.0.0`，WS 的自定义 retry 可能重复，需评估是否保留

---

## 完成标准

- [ ] 所有新模块复制并适配完成
- [ ] 所有 import 路径改为 `from src.xxx`
- [ ] 所有类型注解补全（`X | None` 风格）
- [ ] 4 个新 SQLAlchemy 模型创建完成
- [ ] Alembic 迁移执行成功
- [ ] 2 个新路由（clients, accounts）+ 1 个图片路由注册完成
- [ ] 调度器集成到 lifespan
- [ ] `pytest` 全部通过（原有 284 + 新增 ~76）
- [ ] `mypy src/ --strict` 无新增错误
- [ ] `ruff check src/` 通过
- [ ] 文档更新完成（README, CLAUDE.md）
- [ ] SYNC-PLAN.md 标记为已完成

---

## 附录：快速检查清单

### Import 路径检查

```bash
# 检查是否还有 crew_hotspot 引用
grep -r "crew_hotspot" src/

# 检查是否有相对导入
grep -r "from \." src/
```

### 类型检查

```bash
# 检查新增文件的类型注解
mypy src/services/cookie_manager.py --strict
mypy src/services/rate_limiter.py --strict
mypy src/services/retry.py --strict
mypy src/services/task_queue.py --strict
mypy src/services/scheduler.py --strict
mypy src/services/publish_engine_v2.py --strict
mypy src/services/data_collector.py --strict
mypy src/api/routes/images.py --strict
mypy src/api/routes/clients.py --strict
mypy src/api/routes/accounts.py --strict
```

### 代码风格检查

```bash
ruff check src/services/ src/api/routes/ src/models/ src/schemas/
```

### 测试执行

```bash
# 只运行新增的测试
pytest tests/unit/test_cookie_manager.py -v
pytest tests/unit/test_rate_limiter.py -v
pytest tests/unit/test_retry.py -v
pytest tests/unit/test_task_queue.py -v
pytest tests/unit/test_scheduler.py -v
pytest tests/integration/test_data_collector.py -v
pytest tests/integration/test_publish_engine_v2.py -v
pytest tests/unit/test_image_router.py -v
pytest tests/unit/test_clients.py -v
pytest tests/unit/test_accounts.py -v

# 全量测试
pytest --cov=src --cov-report=term-missing
```

### 数据库迁移验证

```bash
# 检查迁移文件
alembic history

# 应用迁移
alembic upgrade head

# 验证表结构
sqlite3 data/crew_hotspot.db ".schema clients"
sqlite3 data/crew_hotspot.db ".schema accounts"
sqlite3 data/crew_hotspot.db ".schema hot_topics"
sqlite3 data/crew_hotspot.db ".schema metrics"
```

### API 路由验证

```bash
# 启动服务
uvicorn src.api.main:app --reload

# 测试新路由
curl http://localhost:8000/clients
curl http://localhost:8000/accounts
curl http://localhost:8000/images/generate -X POST -H "Content-Type: application/json" -d '{"platform":"xiaohongshu"}'

# 查看 API 文档
open http://localhost:8000/docs
```
