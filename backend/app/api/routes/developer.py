import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.developer import (
    APIKeyCreate,
    APIKeyCreated,
    APIKeyResponse,
    WebhookCreate,
    WebhookResponse,
    WebhookTestResult,
)
from app.services.api_key_service import APIKeyService
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/developer", tags=["developer"])


def _key_svc(db: AsyncSession = Depends(get_db)) -> APIKeyService:
    return APIKeyService(db)


def _wh_svc(db: AsyncSession = Depends(get_db)) -> WebhookService:
    return WebhookService(db)


# ── API Keys ──────────────────────────────────────────────────────────────


@router.post("/api-keys", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    svc: APIKeyService = Depends(_key_svc),
) -> APIKeyCreated:
    raw_key, api_key = await svc.create_key(
        current_user.id, payload.name, payload.permissions
    )
    return APIKeyCreated(
        key=raw_key,
        api_key=APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            permissions=json.loads(api_key.permissions),
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            is_active=api_key.is_active,
        ),
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    svc: APIKeyService = Depends(_key_svc),
) -> list[APIKeyResponse]:
    keys = await svc.list_keys(current_user.id)
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            permissions=json.loads(k.permissions),
            last_used_at=k.last_used_at,
            created_at=k.created_at,
            is_active=k.is_active,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    svc: APIKeyService = Depends(_key_svc),
) -> None:
    try:
        await svc.revoke_key(key_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Webhooks ──────────────────────────────────────────────────────────────


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    payload: WebhookCreate,
    current_user: User = Depends(get_current_user),
    svc: WebhookService = Depends(_wh_svc),
) -> WebhookResponse:
    try:
        webhook = await svc.create_webhook(
            current_user.id, str(payload.url), payload.events, payload.secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=json.loads(webhook.events),
        is_active=webhook.is_active,
        created_at=webhook.created_at,
    )


@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    svc: WebhookService = Depends(_wh_svc),
) -> list[WebhookResponse]:
    webhooks = await svc.list_webhooks(current_user.id)
    return [
        WebhookResponse(
            id=wh.id,
            url=wh.url,
            events=json.loads(wh.events),
            is_active=wh.is_active,
            created_at=wh.created_at,
        )
        for wh in webhooks
    ]


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    svc: WebhookService = Depends(_wh_svc),
) -> None:
    try:
        await svc.delete_webhook(webhook_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/webhooks/{webhook_id}/test", response_model=WebhookTestResult)
async def test_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    svc: WebhookService = Depends(_wh_svc),
) -> WebhookTestResult:
    try:
        success, status_code = await svc.test_webhook(webhook_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return WebhookTestResult(
        success=success,
        status_code=status_code,
        message="Webhook test successful" if success else "Webhook test failed",
    )
