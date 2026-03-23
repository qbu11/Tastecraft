# 数据库重写指南：sqlite3 → SQLAlchemy

> 将 WS 的自定义 ORM 迁移到 ORIG 的 SQLAlchemy 架构

## 背景

**WS 架构：**
- 同步 `sqlite3` 原生操作
- 自定义 Manager 类（ClientManager, AccountManager 等）
- 手动 SQL 字符串

**ORIG 架构：**
- 异步 `SQLAlchemy + aiosqlite`
- Declarative Base + TimestampMixin
- Query API + 类型安全

---

## 步骤 1：创建 SQLAlchemy 模型

### 1.1 Task 模型（for task_queue）

**文件：`src/models/task.py`**

```python
"""任务队列模型"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class TaskStatus(str):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base, TimestampMixin):
    """任务表"""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: f"task-{uuid4().hex[:12]}"
    )
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING, index=True)
    payload: Mapped[dict | None] = mapped_column()  # JSON
    result: Mapped[dict | None] = mapped_column()  # JSON
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_terminal(self) -> bool:
        """是否为终态"""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    @property
    def duration(self) -> float | None:
        """执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, type={self.task_type}, status={self.status})>"
```

### 1.2 更新 models/__init__.py

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
from src.models.task import Task, TaskStatus

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
    # Task Queue
    "Task",
    "TaskStatus",
]
```

---

## 步骤 2：创建 Service 层

### 2.1 ClientService

**文件：`src/services/client_service.py`**

```python
"""客户管理服务"""
import logging
from typing import Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.client import Client
from src.core.error_handling import Result, success, error
from src.core.exceptions import IntegrityError, NotFoundError

logger = logging.getLogger(__name__)


class ClientService:
    """客户服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_client(
        self,
        name: str,
        industry: str | None = None,
        description: str | None = None,
    ) -> Result[Client]:
        """创建客户"""
        try:
            # 检查重名
            result = await self.session.execute(
                select(Client).where(Client.name == name)
            )
            if result.scalar_one_or_none():
                return error(f"客户名称已存在: {name}", "CLIENT_NAME_EXISTS")

            client = Client(name=name, industry=industry, description=description)
            self.session.add(client)
            await self.session.commit()
            await self.session.refresh(client)

            logger.info(f"创建客户成功: {client.id}")
            return success(client)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建客户失败: {e}")
            return error(f"创建客户失败: {e}", "CLIENT_CREATE_ERROR")

    async def get_client(self, client_id: str) -> Result[Client]:
        """获取客户"""
        try:
            result = await self.session.execute(
                select(Client).where(Client.id == client_id)
            )
            client = result.scalar_one_or_none()

            if not client:
                return error(f"客户不存在: {client_id}", "CLIENT_NOT_FOUND")

            return success(client)

        except Exception as e:
            logger.error(f"获取客户失败: {e}")
            return error(f"获取客户失败: {e}", "CLIENT_GET_ERROR")

    async def list_clients(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Result[list[Client]]:
        """列出客户"""
        try:
            result = await self.session.execute(
                select(Client).offset(skip).limit(limit)
            )
            clients = result.scalars().all()
            return success(list(clients))

        except Exception as e:
            logger.error(f"列出客户失败: {e}")
            return error(f"列出客户失败: {e}", "CLIENT_LIST_ERROR")

    async def update_client(
        self,
        client_id: str,
        **kwargs: Any,
    ) -> Result[Client]:
        """更新客户"""
        try:
            result = await self.session.execute(
                select(Client).where(Client.id == client_id)
            )
            client = result.scalar_one_or_none()

            if not client:
                return error(f"客户不存在: {client_id}", "CLIENT_NOT_FOUND")

            for key, value in kwargs.items():
                if hasattr(client, key):
                    setattr(client, key, value)

            await self.session.commit()
            await self.session.refresh(client)

            logger.info(f"更新客户成功: {client.id}")
            return success(client)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新客户失败: {e}")
            return error(f"更新客户失败: {e}", "CLIENT_UPDATE_ERROR")

    async def delete_client(self, client_id: str) -> Result[None]:
        """删除客户"""
        try:
            result = await self.session.execute(
                select(Client).where(Client.id == client_id)
            )
            client = result.scalar_one_or_none()

            if not client:
                return error(f"客户不存在: {client_id}", "CLIENT_NOT_FOUND")

            await self.session.delete(client)
            await self.session.commit()

            logger.info(f"删除客户成功: {client_id}")
            return success(None)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除客户失败: {e}")
            return error(f"删除客户失败: {e}", "CLIENT_DELETE_ERROR")
```

### 2.2 AccountService

**文件：`src/services/account_service.py`**

```python
"""账号管理服务"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account, AccountStatus
from src.core.error_handling import Result, success, error

logger = logging.getLogger(__name__)


class AccountService:
    """账号服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_account(
        self,
        client_id: str,
        platform: str,
        username: str,
        status: str = AccountStatus.ACTIVE,
    ) -> Result[Account]:
        """创建账号"""
        try:
            account = Account(
                client_id=client_id,
                platform=platform,
                username=username,
                status=status,
            )
            self.session.add(account)
            await self.session.commit()
            await self.session.refresh(account)

            logger.info(f"创建账号成功: {account.id}")
            return success(account)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建账号失败: {e}")
            return error(f"创建账号失败: {e}", "ACCOUNT_CREATE_ERROR")

    async def list_accounts(
        self,
        client_id: str | None = None,
        platform: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Result[list[Account]]:
        """列出账号"""
        try:
            query = select(Account)

            if client_id:
                query = query.where(Account.client_id == client_id)
            if platform:
                query = query.where(Account.platform == platform)

            query = query.offset(skip).limit(limit)

            result = await self.session.execute(query)
            accounts = result.scalars().all()
            return success(list(accounts))

        except Exception as e:
            logger.error(f"列出账号失败: {e}")
            return error(f"列出账号失败: {e}", "ACCOUNT_LIST_ERROR")

    async def update_login_status(
        self,
        account_id: str,
        is_logged_in: bool,
    ) -> Result[Account]:
        """更新登录状态"""
        try:
            result = await self.session.execute(
                select(Account).where(Account.id == account_id)
            )
            account = result.scalar_one_or_none()

            if not account:
                return error(f"账号不存在: {account_id}", "ACCOUNT_NOT_FOUND")

            account.is_logged_in = is_logged_in
            if is_logged_in:
                account.last_login = datetime.utcnow()

            await self.session.commit()
            await self.session.refresh(account)

            logger.info(f"更新账号登录状态: {account.id} -> {is_logged_in}")
            return success(account)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新登录状态失败: {e}")
            return error(f"更新登录状态失败: {e}", "ACCOUNT_UPDATE_ERROR")
```

### 2.3 MetricsService

**文件：`src/services/metrics_service.py`**

```python
"""数据指标服务"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.metrics import Metrics
from src.core.error_handling import Result, success, error

logger = logging.getLogger(__name__)


class MetricsService:
    """指标服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_metric(
        self,
        platform: str,
        post_url: str | None = None,
        content_id: str | None = None,
        views: int | None = None,
        likes: int | None = None,
        comments: int | None = None,
        shares: int | None = None,
        raw_metrics: dict | None = None,
    ) -> Result[Metrics]:
        """记录指标"""
        try:
            # 计算互动率
            engagement_rate = None
            if views and views > 0:
                total_engagement = (likes or 0) + (comments or 0) + (shares or 0)
                engagement_rate = total_engagement / views

            metric = Metrics(
                platform=platform,
                post_url=post_url,
                content_id=content_id,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                engagement_rate=engagement_rate,
                raw_metrics=raw_metrics,
            )
            self.session.add(metric)
            await self.session.commit()
            await self.session.refresh(metric)

            logger.info(f"记录指标成功: {metric.id}")
            return success(metric)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"记录指标失败: {e}")
            return error(f"记录指标失败: {e}", "METRIC_RECORD_ERROR")

    async def get_metrics_by_content(
        self,
        content_id: str,
    ) -> Result[list[Metrics]]:
        """获取内容的所有指标"""
        try:
            result = await self.session.execute(
                select(Metrics).where(Metrics.content_id == content_id)
            )
            metrics = result.scalars().all()
            return success(list(metrics))

        except Exception as e:
            logger.error(f"获取指标失败: {e}")
            return error(f"获取指标失败: {e}", "METRIC_GET_ERROR")
```

---

## 步骤 3：重写 TaskQueue

**文件：`src/services/task_queue.py`**

```python
"""任务队列服务"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.models.task import Task, TaskStatus
from src.core.error_handling import Result, success, error
from src.core.config import settings

logger = logging.getLogger(__name__)


class TaskQueue:
    """异步任务队列"""

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or settings.DATABASE_URL
        self.engine = create_async_engine(self.db_url)
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def submit_task(
        self,
        task_type: str,
        payload: dict | None = None,
    ) -> Result[Task]:
        """提交任务"""
        async with self.SessionLocal() as session:
            try:
                task = Task(
                    task_type=task_type,
                    payload=payload or {},
                    status=TaskStatus.PENDING,
                )
                session.add(task)
                await session.commit()
                await session.refresh(task)

                logger.info(f"提交任务成功: {task.id} ({task_type})")
                return success(task)

            except Exception as e:
                await session.rollback()
                logger.error(f"提交任务失败: {e}")
                return error(f"提交任务失败: {e}", "TASK_SUBMIT_ERROR")

    async def get_pending_tasks(self, limit: int = 10) -> Result[list[Task]]:
        """获取待处理任务"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    select(Task)
                    .where(Task.status == TaskStatus.PENDING)
                    .limit(limit)
                )
                tasks = result.scalars().all()
                return success(list(tasks))

            except Exception as e:
                logger.error(f"获取待处理任务失败: {e}")
                return error(f"获取待处理任务失败: {e}", "TASK_GET_ERROR")

    async def start_task(self, task_id: str) -> Result[Task]:
        """开始执行任务"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()

                if not task:
                    return error(f"任务不存在: {task_id}", "TASK_NOT_FOUND")

                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()

                await session.commit()
                await session.refresh(task)

                logger.info(f"开始执行任务: {task.id}")
                return success(task)

            except Exception as e:
                await session.rollback()
                logger.error(f"开始任务失败: {e}")
                return error(f"开始任务失败: {e}", "TASK_START_ERROR")

    async def complete_task(
        self,
        task_id: str,
        result_data: dict | None = None,
    ) -> Result[Task]:
        """完成任务"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()

                if not task:
                    return error(f"任务不存在: {task_id}", "TASK_NOT_FOUND")

                task.status = TaskStatus.COMPLETED
                task.result = result_data
                task.completed_at = datetime.utcnow()

                await session.commit()
                await session.refresh(task)

                logger.info(f"完成任务: {task.id}")
                return success(task)

            except Exception as e:
                await session.rollback()
                logger.error(f"完成任务失败: {e}")
                return error(f"完成任务失败: {e}", "TASK_COMPLETE_ERROR")

    async def fail_task(
        self,
        task_id: str,
        error_message: str,
    ) -> Result[Task]:
        """任务失败"""
        async with self.SessionLocal() as session:
            try:
                result = await session.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()

                if not task:
                    return error(f"任务不存在: {task_id}", "TASK_NOT_FOUND")

                task.status = TaskStatus.FAILED
                task.error = error_message
                task.completed_at = datetime.utcnow()

                await session.commit()
                await session.refresh(task)

                logger.error(f"任务失败: {task.id} - {error_message}")
                return success(task)

            except Exception as e:
                await session.rollback()
                logger.error(f"标记任务失败失败: {e}")
                return error(f"标记任务失败失败: {e}", "TASK_FAIL_ERROR")
```

---

## 步骤 4：修改 scheduler.py

**文件：`src/services/scheduler.py`**

```python
"""任务调度服务"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.services.client_service import ClientService
from src.services.account_service import AccountService
from src.services.metrics_service import MetricsService
from src.core.config import settings

logger = logging.getLogger(__name__)


class HotspotScheduler:
    """热点调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)
        self.engine = create_async_engine(settings.DATABASE_URL)
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    def start(self) -> None:
        """启动调度器"""
        if not settings.SCHEDULER_ENABLED:
            logger.info("调度器已禁用")
            return

        # 注册定时任务
        self.scheduler.add_job(
            self.daily_hotspot_job,
            "cron",
            hour=8,
            minute=0,
            id="daily_hotspot",
        )

        self.scheduler.add_job(
            self.hourly_data_collection_job,
            "cron",
            minute=0,
            id="hourly_data_collection",
        )

        self.scheduler.start()
        logger.info("调度器已启动")

    def shutdown(self) -> None:
        """关闭调度器"""
        self.scheduler.shutdown()
        logger.info("调度器已关闭")

    async def daily_hotspot_job(self) -> None:
        """每日热点监控任务"""
        async with self.SessionLocal() as session:
            client_service = ClientService(session)
            account_service = AccountService(session)

            # 获取活跃客户
            result = await client_service.list_clients()
            if not result.is_success:
                logger.error(f"获取客户列表失败: {result.error}")
                return

            for client in result.data:
                # 获取客户的账号
                accounts_result = await account_service.list_accounts(
                    client_id=client.id
                )
                if not accounts_result.is_success:
                    continue

                # TODO: 调用 HotspotDetectionCrew
                logger.info(f"执行热点监控: {client.name}")

    async def hourly_data_collection_job(self) -> None:
        """每小时数据采集任务"""
        async with self.SessionLocal() as session:
            metrics_service = MetricsService(session)

            # TODO: 调用 DataCollector
            logger.info("执行数据采集")
```

---

## 步骤 5：创建数据库迁移

```bash
cd /c/11projects/Crew

# 生成迁移文件
alembic revision --autogenerate -m "add workspace tables (client, account, hot_topic, task)"

# 检查生成的迁移文件
cat migrations/versions/xxx_add_workspace_tables.py

# 应用迁移
alembic upgrade head

# 验证表结构
sqlite3 data/crew.db ".schema clients"
sqlite3 data/crew.db ".schema accounts"
sqlite3 data/crew.db ".schema hot_topics"
sqlite3 data/crew.db ".schema tasks"
```

---

## 步骤 6：编写测试

**文件：`tests/unit/test_client_service.py`**

```python
"""客户服务测试"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.models.base import Base
from src.models.client import Client
from src.services.client_service import ClientService


@pytest.fixture(scope="function")
def test_engine():
    """测试数据库引擎"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_session(test_engine) -> Session:
    """测试会话"""
    with Session(test_engine) as session:
        yield session


@pytest.mark.unit
class TestClientService:
    """客户服务测试"""

    async def test_create_client(self, test_session) -> None:
        """创建客户"""
        service = ClientService(test_session)
        result = await service.create_client(name="测试客户", industry="科技")

        assert result.is_success
        assert result.data.name == "测试客户"
        assert result.data.industry == "科技"

    async def test_create_duplicate_client(self, test_session) -> None:
        """创建重复客户"""
        service = ClientService(test_session)
        await service.create_client(name="测试客户")
        result = await service.create_client(name="测试客户")

        assert not result.is_success
        assert "已存在" in result.error

    async def test_list_clients(self, test_session) -> None:
        """列出客户"""
        service = ClientService(test_session)
        await service.create_client(name="客户1")
        await service.create_client(name="客户2")

        result = await service.list_clients()

        assert result.is_success
        assert len(result.data) == 2
```

---

## 验证清单

- [ ] 所有模型创建成功
- [ ] Alembic 迁移执行成功
- [ ] Service 层测试通过
- [ ] TaskQueue 测试通过
- [ ] Scheduler 启动成功
- [ ] 无 sqlite3 原生调用残留

```bash
# 检查是否还有 sqlite3 原生调用
grep -r "sqlite3.connect" src/
grep -r "conn.execute" src/
grep -r "conn.commit" src/
```
