import hashlib
import hmac
import json
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = logging.getLogger(__name__)


class WebhookService:
    EVENTS = [
        "content.generated",
        "content.published",
        "content.failed",
        "taste.preference_learned",
        "competitor.viral_detected",
    ]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_webhook(
        self, user_id: int, url: str, events: list[str], secret: str
    ) -> Webhook:
        invalid = [e for e in events if e not in self.EVENTS]
        if invalid:
            raise ValueError(f"Invalid events: {', '.join(invalid)}")

        webhook = Webhook(
            user_id=user_id,
            url=url,
            events=json.dumps(events),
            secret=secret,
        )
        self.db.add(webhook)
        await self.db.flush()
        await self.db.refresh(webhook)
        return webhook

    async def fire_event(self, user_id: int, event: str, payload: dict) -> None:
        """Send webhook payload to all registered URLs for this event."""
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.user_id == user_id,
                Webhook.is_active.is_(True),
            )
        )
        webhooks = list(result.scalars().all())

        for wh in webhooks:
            events = json.loads(wh.events)
            if event not in events:
                continue

            body = json.dumps({"event": event, "payload": payload})
            signature = hmac.HMAC(
                wh.secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()

            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        wh.url,
                        content=body,
                        headers={
                            "Content-Type": "application/json",
                            "X-TasteCraft-Signature": signature,
                            "X-TasteCraft-Event": event,
                        },
                    )
            except Exception:
                logger.warning("Webhook delivery failed for %s to %s", event, wh.url)

    async def list_webhooks(self, user_id: int) -> list[Webhook]:
        result = await self.db.execute(
            select(Webhook)
            .where(Webhook.user_id == user_id, Webhook.is_active.is_(True))
            .order_by(Webhook.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_webhook(self, webhook_id: int, user_id: int) -> None:
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.id == webhook_id, Webhook.user_id == user_id
            )
        )
        webhook = result.scalar_one_or_none()
        if not webhook:
            raise ValueError("Webhook not found")
        webhook.is_active = False
        await self.db.flush()

    async def test_webhook(self, webhook_id: int, user_id: int) -> tuple[bool, int | None]:
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.id == webhook_id, Webhook.user_id == user_id
            )
        )
        webhook = result.scalar_one_or_none()
        if not webhook:
            raise ValueError("Webhook not found")

        test_payload = json.dumps({
            "event": "test",
            "payload": {"message": "This is a test webhook from TasteCraft"},
        })
        signature = hmac.HMAC(
            webhook.secret.encode(), test_payload.encode(), hashlib.sha256
        ).hexdigest()

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    webhook.url,
                    content=test_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-TasteCraft-Signature": signature,
                        "X-TasteCraft-Event": "test",
                    },
                )
                return resp.status_code < 400, resp.status_code
        except Exception as exc:
            logger.warning("Webhook test failed: %s", exc)
            return False, None
