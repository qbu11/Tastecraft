from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.demo_engine import DemoEngine

router = APIRouter(prefix="/demo", tags=["demo"])

# Simple in-memory rate limiter: IP -> list of timestamps
_rate_limit: dict[str, list[float]] = defaultdict(list)
_MAX_REQUESTS = 3
_WINDOW_SECONDS = 3600  # 1 hour


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    timestamps = _rate_limit[ip]
    # Purge old entries
    _rate_limit[ip] = [t for t in timestamps if now - t < _WINDOW_SECONDS]
    if len(_rate_limit[ip]) >= _MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="每小时最多体验 3 次，注册后可无限使用",
        )
    _rate_limit[ip].append(now)


class TasteTestRequest(BaseModel):
    text: str = Field(..., min_length=50, max_length=500)


class TasteTestResponse(BaseModel):
    style_features: list[str]
    imitation: str
    similarity_score: float


_engine = DemoEngine()


@router.post("/taste-test", response_model=TasteTestResponse)
async def taste_test(payload: TasteTestRequest, request: Request) -> TasteTestResponse:
    """Public demo: paste your writing, see AI mimic your style."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    result = await _engine.taste_test(payload.text)
    return TasteTestResponse(
        style_features=result.style_features,
        imitation=result.imitation,
        similarity_score=result.similarity_score,
    )
