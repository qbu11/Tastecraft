"""Version history API routes — list, diff, rollback, partial rollback."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.version import (
    ContentVersionResponse,
    DiffLineResponse,
    PartialRollbackRequest,
    VersionDiffResponse,
)
from app.services.version_manager import VersionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["versions"])


@router.get(
    "/{content_id}/versions",
    response_model=list[ContentVersionResponse],
)
async def list_versions(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    """List all versions for a content piece."""
    manager = VersionManager(db)
    versions = await manager.get_versions(content_id)
    return versions


@router.get(
    "/{content_id}/versions/{v1}/diff/{v2}",
    response_model=VersionDiffResponse,
)
async def get_version_diff(
    content_id: int,
    v1: int,
    v2: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionDiffResponse:
    """Get diff between two versions of a content piece."""
    manager = VersionManager(db)

    try:
        diff = await manager.get_diff(content_id, v1, v2)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return VersionDiffResponse(
        version_from=diff.version_from,
        version_to=diff.version_to,
        title_changed=diff.title_changed,
        body_lines=[
            DiffLineResponse(
                type=line.type,
                content=line.content,
                line_number_old=line.line_number_old,
                line_number_new=line.line_number_new,
            )
            for line in diff.body_lines
        ],
        additions=diff.additions,
        deletions=diff.deletions,
    )


@router.post(
    "/{content_id}/versions/{version_number}/rollback",
    response_model=ContentVersionResponse,
)
async def rollback_to_version(
    content_id: int,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentVersionResponse:
    """Rollback content to a specific version. Creates a new version."""
    manager = VersionManager(db)

    try:
        content = await manager.rollback(content_id, version_number, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Return the latest version (the rollback version)
    versions = await manager.get_versions(content_id)
    if not versions:
        raise HTTPException(status_code=500, detail="Rollback succeeded but no versions found")

    return versions[0]


@router.post(
    "/{content_id}/versions/partial-rollback",
    response_model=ContentVersionResponse,
)
async def partial_rollback(
    content_id: int,
    payload: PartialRollbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentVersionResponse:
    """Take specific sections from an older version.

    Useful for: "Use this version's opening + current version's body".
    """
    manager = VersionManager(db)

    try:
        content = await manager.partial_rollback(
            content_id=content_id,
            from_version=payload.from_version,
            sections=payload.sections,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Return the latest version
    versions = await manager.get_versions(content_id)
    if not versions:
        raise HTTPException(status_code=500, detail="Partial rollback succeeded but no versions found")

    return versions[0]
