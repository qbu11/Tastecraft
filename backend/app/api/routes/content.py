import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.content import Content
from app.models.user import User
from app.schemas.content import ContentCreate, ContentList, ContentResponse, ContentUpdate
from app.services.diff_engine import DiffEngine
from app.services.pattern_extractor import PatternExtractor
from app.tasks.celery_app import generate_content_task, publish_content_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])

# Trigger pattern extraction after this many accumulated edits
_EXTRACTION_THRESHOLD = 3


@router.post("/generate", status_code=202)
async def generate_content(
    payload: ContentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    content = Content(
        user_id=current_user.id,
        project_id=payload.project_id,
        title="",
        body="",
        platform=payload.platform,
        status="draft",
    )
    db.add(content)
    await db.flush()
    await db.refresh(content)

    task = generate_content_task.delay(content.id, payload.prompt, payload.platform)
    return {"task_id": task.id, "content_id": content.id}


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Content:
    result = await db.execute(
        select(Content).where(Content.id == content_id, Content.user_id == current_user.id)
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: int,
    payload: ContentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Content:
    result = await db.execute(
        select(Content).where(Content.id == content_id, Content.user_id == current_user.id)
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    engine = DiffEngine(db)
    edits_captured = 0

    if payload.title is not None and payload.title != content.title:
        await engine.capture_edit(
            content_id=content.id,
            user_id=current_user.id,
            original=content.title,
            modified=payload.title,
            platform=content.platform,
        )
        content.title = payload.title
        edits_captured += 1

    if payload.body is not None and payload.body != content.body:
        await engine.capture_edit(
            content_id=content.id,
            user_id=current_user.id,
            original=content.body,
            modified=payload.body,
            platform=content.platform,
        )
        content.body = payload.body
        edits_captured += 1

    await db.flush()
    await db.refresh(content)

    # Trigger pattern extraction if threshold reached
    if edits_captured > 0:
        total_edits = await engine.get_user_edit_count(current_user.id, content.platform)
        if total_edits >= _EXTRACTION_THRESHOLD and total_edits % _EXTRACTION_THRESHOLD == 0:
            try:
                extractor = PatternExtractor(db)
                await extractor.run_extraction_pipeline(current_user.id, content.platform)
                logger.info(
                    "Pattern extraction triggered for user %d (total_edits=%d)",
                    current_user.id,
                    total_edits,
                )
            except Exception as e:
                # Pattern extraction is non-critical — don't fail the update
                logger.warning("Pattern extraction failed: %s", e)

    return content


@router.post("/{content_id}/publish", status_code=202)
async def publish_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Content).where(Content.id == content_id, Content.user_id == current_user.id)
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    content.status = "publishing"
    await db.flush()

    task = publish_content_task.delay(content.id, content.platform)
    return {"task_id": task.id, "content_id": content.id}


@router.get("/", response_model=ContentList)
async def list_content(
    skip: int = 0,
    limit: int = 20,
    platform: str | None = None,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Content).where(Content.user_id == current_user.id)
    count_query = select(func.count()).select_from(Content).where(
        Content.user_id == current_user.id
    )

    if platform:
        query = query.where(Content.platform == platform)
        count_query = count_query.where(Content.platform == platform)
    if status:
        query = query.where(Content.status == status)
        count_query = count_query.where(Content.status == status)

    query = query.order_by(Content.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    total_result = await db.execute(count_query)

    return {"items": list(result.scalars().all()), "total": total_result.scalar_one()}
