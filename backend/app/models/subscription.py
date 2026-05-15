"""Subscription and usage tracking models."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Subscription(Base):
    """User subscription plan and limits."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, index=True
    )
    plan: Mapped[str] = mapped_column(String(20), default="free")  # free/basic/pro/enterprise
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/cancelled/expired/trial
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    current_period_end: Mapped[datetime] = mapped_column(DateTime)
    monthly_post_limit: Mapped[int] = mapped_column(Integer, default=10)
    platform_limit: Mapped[int] = mapped_column(Integer, default=1)
    content_line_limit: Mapped[int] = mapped_column(Integer, default=1)
    competitor_account_limit: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="subscription")  # noqa: F821

    usage_records: Mapped[list["UsageRecord"]] = relationship(back_populates="subscription")
    payments: Mapped[list["Payment"]] = relationship(back_populates="subscription")


class UsageRecord(Base):
    """Per-period usage tracking."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscriptions.id"), index=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    posts_generated: Mapped[int] = mapped_column(Integer, default=0)
    posts_published: Mapped[int] = mapped_column(Integer, default=0)
    platforms_used: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    content_lines_used: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subscription: Mapped["Subscription"] = relationship(back_populates="usage_records")


class Payment(Base):
    """Payment history."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscriptions.id"), index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer)  # in CNY fen
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    method: Mapped[str] = mapped_column(String(30), default="wechat_pay")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/paid/failed/refunded
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subscription: Mapped["Subscription"] = relationship(back_populates="payments")
