import hashlib
import json
import secrets
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey


class APIKeyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_key(
        self, user_id: int, name: str, permissions: list[str]
    ) -> tuple[str, APIKey]:
        """Create API key. Returns (raw_key, key_record). Raw key shown once only."""
        raw_key = f"tc_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]

        api_key = APIKey(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            permissions=json.dumps(permissions),
        )
        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)
        return raw_key, api_key

    async def validate_key(self, raw_key: str) -> APIKey | None:
        """Validate and return API key record."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active.is_(True),
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            await self.db.execute(
                update(APIKey)
                .where(APIKey.id == api_key.id)
                .values(last_used_at=datetime.utcnow())
            )
        return api_key

    async def revoke_key(self, key_id: int, user_id: int) -> None:
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise ValueError("API key not found")
        api_key.is_active = False
        await self.db.flush()

    async def list_keys(self, user_id: int) -> list[APIKey]:
        result = await self.db.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id, APIKey.is_active.is_(True))
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())
