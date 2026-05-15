"""Notification creation, delivery, and management service."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.schemas.notification import NotificationList, NotificationOut

logger = logging.getLogger(__name__)


class NotificationService:
    """Create, store, and query user notifications."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Creation helpers ──

    async def create_notification(
        self,
        user_id: int,
        type: str,
        title: str,
        body: str,
        metadata: dict | None = None,
    ) -> Notification:
        """Create and store a notification."""
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            metadata_json=metadata,
        )
        self.db.add(notif)
        await self.db.flush()
        await self.db.refresh(notif)
        return notif

    async def send_daily_digest(self, user_id: int) -> Notification:
        """Generate and send daily content performance digest."""
        from app.models.analytics import Analytics
        from app.models.content import Content

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)

        # Yesterday's published count
        pub_result = await self.db.execute(
            select(func.count()).select_from(Content).where(
                Content.user_id == user_id,
                Content.status == "published",
                Content.published_at >= yesterday,
            )
        )
        published_count = pub_result.scalar_one()

        # Pending review count
        pending_result = await self.db.execute(
            select(func.count()).select_from(Content).where(
                Content.user_id == user_id,
                Content.status == "reviewing",
            )
        )
        pending_count = pending_result.scalar_one()

        # Yesterday total views/likes
        metrics_result = await self.db.execute(
            select(
                func.coalesce(func.sum(Analytics.views), 0),
                func.coalesce(func.sum(Analytics.likes), 0),
            ).where(
                Analytics.user_id == user_id,
                Analytics.collected_at >= yesterday,
            )
        )
        row = metrics_result.one()
        views, likes = int(row[0]), int(row[1])

        body_parts = []
        if published_count > 0:
            body_parts.append(f"昨日发布 {published_count} 篇内容")
        if views > 0 or likes > 0:
            body_parts.append(f"获得 {views} 次浏览、{likes} 个点赞")
        if pending_count > 0:
            body_parts.append(f"{pending_count} 篇内容待审核")

        body = "；".join(body_parts) if body_parts else "暂无新数据"

        return await self.create_notification(
            user_id=user_id,
            type="daily_digest",
            title="每日数据速览",
            body=body,
            metadata={
                "published": published_count,
                "pending_review": pending_count,
                "views": views,
                "likes": likes,
            },
        )

    async def send_publish_status(
        self,
        user_id: int,
        content_id: int,
        success: bool,
        url: str | None = None,
    ) -> Notification:
        """Notify about publish success/failure."""
        if success:
            title = "发布成功"
            body = f"内容 #{content_id} 已成功发布"
            if url:
                body += f"：{url}"
        else:
            title = "发布失败"
            body = f"内容 #{content_id} 发布失败，请检查后重试"

        return await self.create_notification(
            user_id=user_id,
            type="publish_status",
            title=title,
            body=body,
            metadata={"content_id": content_id, "success": success, "url": url},
        )

    async def send_competitor_alert(
        self,
        user_id: int,
        competitor_name: str,
        viral_post: dict,
    ) -> Notification:
        """Alert about competitor viral content."""
        return await self.create_notification(
            user_id=user_id,
            type="competitor_alert",
            title=f"竞品动态：{competitor_name}",
            body=f"热门内容：{viral_post.get('title', '未知标题')}",
            metadata={"competitor": competitor_name, "post": viral_post},
        )

    async def send_evolution_weekly(self, user_id: int) -> Notification:
        """Weekly taste evolution summary."""
        return await self.create_notification(
            user_id=user_id,
            type="taste_evolution",
            title="本周品味进化报告",
            body="你的品味画像已更新，点击查看本周学到的内容偏好",
            metadata={"week": datetime.now(timezone.utc).isocalendar()[1]},
        )

    async def send_session_expiry(
        self, user_id: int, platform: str, days_left: int
    ) -> Notification:
        """Warn about expiring platform session."""
        return await self.create_notification(
            user_id=user_id,
            type="session_expiry",
            title=f"{platform} 登录即将过期",
            body=f"你的 {platform} 登录将在 {days_left} 天后过期，请及时续期",
            metadata={"platform": platform, "days_left": days_left},
        )

    # ── Query ──

    async def get_notifications(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> NotificationList:
        """Get notifications, paginated, unread first."""
        base = select(Notification).where(Notification.user_id == user_id)

        total_result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id
            )
        )
        total = total_result.scalar_one()

        unread_result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        unread = unread_result.scalar_one()

        query = (
            base.order_by(Notification.is_read, Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = [
            NotificationOut.model_validate(n) for n in result.scalars().all()
        ]

        return NotificationList(items=items, total=total, unread=unread)

    async def get_unread_count(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return result.scalar_one()

    async def mark_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a single notification as read. Returns True if found."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True)
        )
        return result.rowcount > 0

    async def mark_all_read(self, user_id: int) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        return result.rowcount

    async def delete_notification(
        self, notification_id: int, user_id: int
    ) -> bool:
        """Delete a notification. Returns True if found."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notif = result.scalar_one_or_none()
        if notif is None:
            return False
        await self.db.delete(notif)
        return True
