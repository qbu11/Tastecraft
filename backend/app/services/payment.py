"""Payment service — placeholder for WeChat Pay / Alipay integration."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Payment
from app.schemas.billing import PaymentIntent, PaymentResponse

logger = logging.getLogger(__name__)


class PaymentService:
    """Handle payment creation, webhook processing, and history queries.

    For MVP this returns mock payment URLs.
    Production: integrate with Stripe, WeChat Pay native SDK, or Alipay SDK.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_payment_intent(
        self,
        user_id: int,
        subscription_id: int,
        amount_cents: int,
        method: str = "wechat_pay",
        description: str | None = None,
    ) -> PaymentIntent:
        """Create a payment intent (WeChat Pay / Alipay).

        For MVP: returns a mock payment URL.
        """
        payment_id = f"pay_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)

        # Persist payment record
        payment = Payment(
            user_id=user_id,
            subscription_id=subscription_id,
            amount_cents=amount_cents,
            method=method,
            status="pending",
            external_id=payment_id,
            description=description,
        )
        self.db.add(payment)
        await self.db.flush()

        # Mock payment URL — replace with actual provider SDK in production
        mock_url = f"https://pay.tastecraft.cn/checkout/{payment_id}"

        return PaymentIntent(
            payment_id=payment_id,
            amount_cents=amount_cents,
            currency="CNY",
            method=method,
            payment_url=mock_url,
            expires_at=now + timedelta(minutes=30),
        )

    async def handle_webhook(self, payload: dict) -> None:
        """Handle payment callback from payment provider.

        In production, verify the signature and update payment status.
        """
        external_id = payload.get("payment_id", "")
        status = payload.get("status", "")

        if not external_id or not status:
            logger.warning("Invalid webhook payload: %s", payload)
            return

        result = await self.db.execute(
            select(Payment).where(Payment.external_id == external_id)
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            logger.warning("Payment not found for webhook: %s", external_id)
            return

        if status == "paid":
            payment.status = "paid"
            payment.paid_at = datetime.now(timezone.utc)
        elif status == "failed":
            payment.status = "failed"
        elif status == "refunded":
            payment.status = "refunded"

        await self.db.flush()
        logger.info("Payment %s updated to %s", external_id, status)

    async def get_payment_history(self, user_id: int) -> list[PaymentResponse]:
        """Get payment history for a user."""
        result = await self.db.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(50)
        )
        payments = result.scalars().all()
        return [PaymentResponse.model_validate(p) for p in payments]
