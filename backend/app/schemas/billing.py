"""Billing & subscription Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


# ── Plan Info ──


class PlanFeatures(BaseModel):
    price: int | None  # CNY fen, None = custom
    posts: int  # -1 = unlimited
    platforms: int
    lines: int
    competitors: int
    publish_trial_days: int | None = None


class PlanInfo(BaseModel):
    name: str
    label: str
    features: PlanFeatures
    is_current: bool = False


# ── Subscription ──


class SubscriptionResponse(BaseModel):
    id: int
    plan: str
    status: str
    trial_ends_at: datetime | None
    current_period_start: datetime
    current_period_end: datetime
    monthly_post_limit: int
    platform_limit: int
    content_line_limit: int
    competitor_account_limit: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubscribeRequest(BaseModel):
    plan: str  # free/basic/pro/enterprise


class UpgradeRequest(BaseModel):
    new_plan: str


# ── Usage ──


class UsageSummary(BaseModel):
    posts_generated: int
    posts_published: int
    post_limit: int  # -1 = unlimited
    platforms_used: list[str]
    platform_limit: int
    content_lines_used: list[str]
    content_line_limit: int
    period_start: datetime
    period_end: datetime
    usage_percent: float  # 0-100 based on posts


# ── Overage ──


class OverageLineItem(BaseModel):
    resource: str  # posts / platforms / lines
    used: int
    limit: int
    overage: int
    unit_price_cents: int
    total_cents: int


class OverageBill(BaseModel):
    items: list[OverageLineItem]
    total_cents: int
    currency: str = "CNY"


# ── Payment ──


class PaymentIntent(BaseModel):
    payment_id: str
    amount_cents: int
    currency: str = "CNY"
    method: str
    payment_url: str  # WeChat Pay / Alipay redirect
    expires_at: datetime


class PaymentResponse(BaseModel):
    id: int
    amount_cents: int
    currency: str
    method: str
    status: str
    description: str | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PayRequest(BaseModel):
    amount_cents: int
    method: str = "wechat_pay"
    description: str | None = None


# ── Usage Limit Check Result ──


class UsageLimitResult(BaseModel):
    allowed: bool
    reason: str | None = None
    current: int
    limit: int  # -1 = unlimited
