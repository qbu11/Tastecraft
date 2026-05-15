"""Billing API routes — subscription management, usage tracking, and payments."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.billing import (
    OverageBill,
    PaymentIntent,
    PaymentResponse,
    PayRequest,
    PlanFeatures,
    PlanInfo,
    SubscribeRequest,
    SubscriptionResponse,
    UpgradeRequest,
    UsageSummary,
)
from app.services.billing import BillingService
from app.services.payment import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ── Helpers ──


def _billing(db: AsyncSession) -> BillingService:
    return BillingService(db)


def _payment(db: AsyncSession) -> PaymentService:
    return PaymentService(db)


# ── Subscription ──


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Get current subscription details."""
    svc = _billing(db)
    sub = await svc.get_subscription(current_user.id)
    if sub is None:
        sub = await svc.create_subscription(current_user.id, "free")
    return SubscriptionResponse.model_validate(sub)


@router.post("/subscribe", response_model=SubscriptionResponse, status_code=201)
async def subscribe(
    payload: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Subscribe to a plan. Creates subscription if none exists."""
    svc = _billing(db)
    existing = await svc.get_subscription(current_user.id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Subscription already exists. Use /upgrade to change plans.",
        )
    try:
        sub = await svc.create_subscription(current_user.id, payload.plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SubscriptionResponse.model_validate(sub)


@router.post("/upgrade", response_model=SubscriptionResponse)
async def upgrade_plan(
    payload: UpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Upgrade to a new plan."""
    svc = _billing(db)
    try:
        sub = await svc.upgrade_plan(current_user.id, payload.new_plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SubscriptionResponse.model_validate(sub)


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Cancel subscription (active until period end)."""
    svc = _billing(db)
    try:
        sub = await svc.cancel_subscription(current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SubscriptionResponse.model_validate(sub)


# ── Usage ──


@router.get("/usage", response_model=UsageSummary)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageSummary:
    """Get current period usage summary."""
    svc = _billing(db)
    return await svc.get_usage_summary(current_user.id)


# ── Overage ──


@router.get("/overage", response_model=OverageBill)
async def get_overage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OverageBill:
    """Calculate overage charges for the current period."""
    svc = _billing(db)
    return await svc.calculate_overage(current_user.id)


# ── Plans ──


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlanInfo]:
    """List all available plans with feature comparison."""
    svc = _billing(db)
    sub = await svc.get_subscription(current_user.id)
    current_plan = sub.plan if sub else "free"

    plans = []
    labels = {"free": "Free", "basic": "Basic", "pro": "Pro", "enterprise": "Enterprise"}
    for name, config in BillingService.PLANS.items():
        plans.append(
            PlanInfo(
                name=name,
                label=labels.get(name, name.title()),
                features=PlanFeatures(
                    price=config["price"],
                    posts=config["posts"],
                    platforms=config["platforms"],
                    lines=config["lines"],
                    competitors=config.get("competitors", 0),
                    publish_trial_days=config.get("publish_trial_days"),
                ),
                is_current=(name == current_plan),
            )
        )
    return plans


# ── Payments ──


@router.post("/pay", response_model=PaymentIntent)
async def create_payment(
    payload: PayRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentIntent:
    """Initiate a payment (returns payment URL for WeChat Pay / Alipay)."""
    svc = _billing(db)
    sub = await svc.get_subscription(current_user.id)
    if sub is None:
        raise HTTPException(status_code=400, detail="No subscription found. Subscribe first.")

    pay_svc = _payment(db)
    return await pay_svc.create_payment_intent(
        user_id=current_user.id,
        subscription_id=sub.id,
        amount_cents=payload.amount_cents,
        method=payload.method,
        description=payload.description,
    )


@router.get("/payments", response_model=list[PaymentResponse])
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentResponse]:
    """Get payment history."""
    pay_svc = _payment(db)
    return await pay_svc.get_payment_history(current_user.id)


@router.post("/webhook")
async def payment_webhook(
    payload: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle payment provider webhook callback."""
    pay_svc = _payment(db)
    await pay_svc.handle_webhook(payload)
    return {"status": "ok"}
