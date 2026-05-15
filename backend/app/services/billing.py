"""Billing service — plan management, usage tracking, and overage calculation."""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Payment, Subscription, UsageRecord
from app.schemas.billing import (
    OverageBill,
    OverageLineItem,
    UsageLimitResult,
    UsageSummary,
)

logger = logging.getLogger(__name__)


class BillingService:
    """Manage subscriptions, track usage, and calculate overage charges."""

    PLANS: dict[str, dict] = {
        "free": {
            "price": 0,
            "posts": 10,
            "platforms": 1,
            "lines": 1,
            "competitors": 0,
            "publish_trial_days": 7,
        },
        "basic": {
            "price": 4900,
            "posts": 30,
            "platforms": 1,
            "lines": 1,
            "competitors": 0,
        },
        "pro": {
            "price": 14900,
            "posts": 100,
            "platforms": 3,
            "lines": 3,
            "competitors": 10,
        },
        "enterprise": {
            "price": None,
            "posts": -1,
            "platforms": 5,
            "lines": 5,
            "competitors": 50,
        },
    }

    # Exponential overage pricing (per unit above plan limit)
    OVERAGE_RATES: dict[str, object] = {
        "posts": staticmethod(lambda n: int(49 * (1.5 ** (n // 10)))),
        "platforms": staticmethod(lambda n: int(2900 * (2 ** (n - 1)))),
        "lines": staticmethod(lambda n: int(3900 * (2.5 ** (n - 1)))),
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Subscription CRUD ──

    async def get_subscription(self, user_id: int) -> Subscription | None:
        """Get the user's current subscription."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_subscription(self, user_id: int, plan: str) -> Subscription:
        """Create a new subscription for the user."""
        if plan not in self.PLANS:
            raise ValueError(f"Invalid plan: {plan}")

        plan_config = self.PLANS[plan]
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        trial_ends_at = None
        if plan == "free" and plan_config.get("publish_trial_days"):
            trial_ends_at = now + timedelta(days=plan_config["publish_trial_days"])

        sub = Subscription(
            user_id=user_id,
            plan=plan,
            status="trial" if trial_ends_at else "active",
            trial_ends_at=trial_ends_at,
            current_period_start=now,
            current_period_end=period_end,
            monthly_post_limit=plan_config["posts"],
            platform_limit=plan_config["platforms"],
            content_line_limit=plan_config["lines"],
            competitor_account_limit=plan_config.get("competitors", 0),
        )
        self.db.add(sub)
        await self.db.flush()

        # Create initial usage record
        usage = UsageRecord(
            user_id=user_id,
            subscription_id=sub.id,
            period_start=now,
            period_end=period_end,
        )
        self.db.add(usage)
        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    async def upgrade_plan(self, user_id: int, new_plan: str) -> Subscription:
        """Upgrade user to a new plan."""
        if new_plan not in self.PLANS:
            raise ValueError(f"Invalid plan: {new_plan}")

        sub = await self.get_subscription(user_id)
        if sub is None:
            return await self.create_subscription(user_id, new_plan)

        plan_config = self.PLANS[new_plan]
        sub.plan = new_plan
        sub.status = "active"
        sub.monthly_post_limit = plan_config["posts"]
        sub.platform_limit = plan_config["platforms"]
        sub.content_line_limit = plan_config["lines"]
        sub.competitor_account_limit = plan_config.get("competitors", 0)
        sub.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    async def cancel_subscription(self, user_id: int) -> Subscription:
        """Cancel subscription (remains active until period end)."""
        sub = await self.get_subscription(user_id)
        if sub is None:
            raise ValueError("No active subscription found")

        sub.status = "cancelled"
        sub.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    # ── Usage Tracking ──

    async def _get_current_usage(self, user_id: int) -> UsageRecord | None:
        """Get usage record for the current billing period."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(UsageRecord)
            .where(
                UsageRecord.user_id == user_id,
                UsageRecord.period_start <= now,
                UsageRecord.period_end >= now,
            )
            .order_by(UsageRecord.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def check_usage_limit(
        self, user_id: int, action: str
    ) -> UsageLimitResult:
        """Check if user can perform an action within their plan limits.

        Args:
            action: 'generate' or 'publish'
        """
        sub = await self.get_subscription(user_id)
        if sub is None:
            # Auto-create free tier
            sub = await self.create_subscription(user_id, "free")

        usage = await self._get_current_usage(user_id)
        if usage is None:
            return UsageLimitResult(allowed=True, current=0, limit=sub.monthly_post_limit)

        if action == "generate":
            current = usage.posts_generated
            limit = sub.monthly_post_limit
        elif action == "publish":
            current = usage.posts_published
            limit = sub.monthly_post_limit
            # Check trial publishing window for free tier
            if sub.plan == "free" and not await self.is_trial_active(user_id):
                return UsageLimitResult(
                    allowed=False,
                    reason="Free tier publishing trial has expired. Upgrade to continue publishing.",
                    current=current,
                    limit=limit,
                )
        else:
            return UsageLimitResult(allowed=True, current=0, limit=-1)

        # -1 means unlimited
        if limit == -1:
            return UsageLimitResult(allowed=True, current=current, limit=limit)

        if current >= limit:
            return UsageLimitResult(
                allowed=False,
                reason=f"Monthly {action} limit reached ({current}/{limit}). Upgrade your plan or wait for the next billing period.",
                current=current,
                limit=limit,
            )

        return UsageLimitResult(allowed=True, current=current, limit=limit)

    async def record_usage(self, user_id: int, action: str, **kwargs: str) -> None:
        """Record a usage event.

        Args:
            action: 'generate', 'publish', 'platform', 'content_line'
            kwargs: Additional context (platform name, content line id, etc.)
        """
        usage = await self._get_current_usage(user_id)
        if usage is None:
            sub = await self.get_subscription(user_id)
            if sub is None:
                sub = await self.create_subscription(user_id, "free")
            usage = UsageRecord(
                user_id=user_id,
                subscription_id=sub.id,
                period_start=sub.current_period_start,
                period_end=sub.current_period_end,
            )
            self.db.add(usage)
            await self.db.flush()

        if action == "generate":
            usage.posts_generated += 1
        elif action == "publish":
            usage.posts_published += 1
        elif action == "platform":
            platforms = json.loads(usage.platforms_used)
            platform_name = kwargs.get("platform", "")
            if platform_name and platform_name not in platforms:
                platforms.append(platform_name)
                usage.platforms_used = json.dumps(platforms)
        elif action == "content_line":
            lines = json.loads(usage.content_lines_used)
            line_id = kwargs.get("line_id", "")
            if line_id and line_id not in lines:
                lines.append(line_id)
                usage.content_lines_used = json.dumps(lines)

        await self.db.flush()

    # ── Overage Calculation ──

    async def calculate_overage(self, user_id: int) -> OverageBill:
        """Calculate overage charges for the current period."""
        sub = await self.get_subscription(user_id)
        if sub is None:
            return OverageBill(items=[], total_cents=0)

        usage = await self._get_current_usage(user_id)
        if usage is None:
            return OverageBill(items=[], total_cents=0)

        items: list[OverageLineItem] = []

        # Posts overage
        post_limit = sub.monthly_post_limit
        posts_used = max(usage.posts_generated, usage.posts_published)
        if post_limit != -1 and posts_used > post_limit:
            overage = posts_used - post_limit
            rate_fn = self.OVERAGE_RATES["posts"]
            unit_price = rate_fn(overage)
            items.append(
                OverageLineItem(
                    resource="posts",
                    used=posts_used,
                    limit=post_limit,
                    overage=overage,
                    unit_price_cents=unit_price,
                    total_cents=unit_price * overage,
                )
            )

        # Platforms overage
        platforms = json.loads(usage.platforms_used)
        if len(platforms) > sub.platform_limit:
            overage = len(platforms) - sub.platform_limit
            rate_fn = self.OVERAGE_RATES["platforms"]
            unit_price = rate_fn(overage)
            items.append(
                OverageLineItem(
                    resource="platforms",
                    used=len(platforms),
                    limit=sub.platform_limit,
                    overage=overage,
                    unit_price_cents=unit_price,
                    total_cents=unit_price * overage,
                )
            )

        # Content lines overage
        lines = json.loads(usage.content_lines_used)
        if len(lines) > sub.content_line_limit:
            overage = len(lines) - sub.content_line_limit
            rate_fn = self.OVERAGE_RATES["lines"]
            unit_price = rate_fn(overage)
            items.append(
                OverageLineItem(
                    resource="lines",
                    used=len(lines),
                    limit=sub.content_line_limit,
                    overage=overage,
                    unit_price_cents=unit_price,
                    total_cents=unit_price * overage,
                )
            )

        total = sum(item.total_cents for item in items)
        return OverageBill(items=items, total_cents=total)

    # ── Trial ──

    async def is_trial_active(self, user_id: int) -> bool:
        """Check if the free tier publishing trial is still active."""
        sub = await self.get_subscription(user_id)
        if sub is None:
            return False
        if sub.trial_ends_at is None:
            return sub.plan != "free"  # Paid plans always have publish access
        return datetime.now(timezone.utc) < sub.trial_ends_at

    # ── Usage Summary ──

    async def get_usage_summary(self, user_id: int) -> UsageSummary:
        """Get a comprehensive usage summary for the current period."""
        sub = await self.get_subscription(user_id)
        if sub is None:
            sub = await self.create_subscription(user_id, "free")

        usage = await self._get_current_usage(user_id)
        posts_generated = usage.posts_generated if usage else 0
        posts_published = usage.posts_published if usage else 0
        platforms = json.loads(usage.platforms_used) if usage else []
        lines = json.loads(usage.content_lines_used) if usage else []

        post_limit = sub.monthly_post_limit
        if post_limit == -1:
            usage_percent = 0.0
        elif post_limit == 0:
            usage_percent = 100.0
        else:
            usage_percent = min(100.0, (max(posts_generated, posts_published) / post_limit) * 100)

        return UsageSummary(
            posts_generated=posts_generated,
            posts_published=posts_published,
            post_limit=post_limit,
            platforms_used=platforms,
            platform_limit=sub.platform_limit,
            content_lines_used=lines,
            content_line_limit=sub.content_line_limit,
            period_start=sub.current_period_start,
            period_end=sub.current_period_end,
            usage_percent=round(usage_percent, 1),
        )
