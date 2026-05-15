from datetime import datetime

from pydantic import BaseModel, HttpUrl


class APIKeyCreate(BaseModel):
    name: str
    permissions: list[str] = []


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    permissions: list[str]
    last_used_at: datetime | None
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class APIKeyCreated(BaseModel):
    """Returned only on creation — contains the raw key (shown once)."""
    key: str
    api_key: APIKeyResponse


class WebhookCreate(BaseModel):
    url: HttpUrl
    events: list[str]
    secret: str


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookTestResult(BaseModel):
    success: bool
    status_code: int | None = None
    message: str
