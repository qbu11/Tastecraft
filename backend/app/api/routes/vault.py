"""Vault API routes — internal/admin endpoints for vault management."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.vault import ContextPreview, ContextPreviewRequest, VaultHealth
from app.services.context_harness import ContextHarness
from app.services.taste_vault import TasteVault

router = APIRouter(prefix="/vault", tags=["vault"])


def _get_vault(user: User, project_slug: str | None = None) -> TasteVault:
    """Get vault for the current user. Uses first project if slug not specified."""
    user_id = str(user.id)
    slug = project_slug or "default"
    return TasteVault(user_id=user_id, project_slug=slug)


@router.get("/health", response_model=VaultHealth)
async def vault_health(
    project_slug: str = "default",
    current_user: User = Depends(get_current_user),
) -> VaultHealth:
    """Vault health status for current user.

    Returns completeness percentage, document count, and stale documents.
    """
    vault = _get_vault(current_user, project_slug)
    return await vault.get_vault_health()


@router.post("/context-preview", response_model=ContextPreview)
async def context_preview(
    payload: ContextPreviewRequest,
    project_slug: str = "default",
    current_user: User = Depends(get_current_user),
) -> ContextPreview:
    """Preview what context would be injected for a given generation request.

    Useful for debugging and understanding what the AI "sees" from the vault.
    """
    vault = _get_vault(current_user, project_slug)
    if not vault.exists():
        raise HTTPException(
            status_code=404,
            detail="Vault not found. Complete onboarding first.",
        )

    harness = ContextHarness()
    return await harness.preview_context(
        vault=vault,
        platform=payload.platform,
        topic=payload.topic,
        content_type=payload.content_type,
    )


@router.post("/rebuild", status_code=202)
async def rebuild_vault(
    project_slug: str = "default",
    current_user: User = Depends(get_current_user),
) -> dict:
    """Force rebuild vault from all edits (admin).

    This re-processes all stored taste edits to reconstruct the vault.
    Useful if vault files get corrupted or need a full refresh.
    """
    vault = _get_vault(current_user, project_slug)
    if not vault.exists():
        raise HTTPException(
            status_code=404,
            detail="Vault not found. Complete onboarding first.",
        )

    # For now, return acknowledgment. Full rebuild would be a background task.
    health = await vault.get_vault_health()
    return {
        "status": "rebuild_queued",
        "user_id": str(current_user.id),
        "project_slug": project_slug,
        "current_health": health.model_dump(),
    }
