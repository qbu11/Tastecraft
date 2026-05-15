from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.content import Content
from app.models.taste_edit import TasteEdit
from app.models.user import User

router = APIRouter(prefix="/taste", tags=["taste"])


@router.get("/profile")
async def get_taste_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    total_result = await db.execute(
        select(func.count()).select_from(Content).where(Content.user_id == current_user.id)
    )
    total_content = total_result.scalar_one()

    edit_result = await db.execute(
        select(func.count()).select_from(TasteEdit).where(TasteEdit.user_id == current_user.id)
    )
    total_edits = edit_result.scalar_one()

    platform_result = await db.execute(
        select(Content.platform, func.count())
        .where(Content.user_id == current_user.id)
        .group_by(Content.platform)
    )
    platform_breakdown = {row[0]: row[1] for row in platform_result.all()}

    return {
        "user_id": current_user.id,
        "total_content": total_content,
        "total_edits": total_edits,
        "platform_breakdown": platform_breakdown,
        "phase": "manual" if total_content < 10 else "semi_auto" if total_content < 50 else "auto",
    }


@router.get("/score")
async def get_taste_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(func.avg(Content.taste_score))
        .where(Content.user_id == current_user.id)
        .where(Content.taste_score.isnot(None))
    )
    avg_score = result.scalar_one()

    return {
        "user_id": current_user.id,
        "average_taste_score": round(avg_score, 2) if avg_score else None,
    }


@router.get("/edits")
async def get_edit_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = (
        select(TasteEdit)
        .where(TasteEdit.user_id == current_user.id)
        .order_by(TasteEdit.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    edits = result.scalars().all()

    return {
        "items": [
            {
                "id": e.id,
                "content_id": e.content_id,
                "diff_type": e.diff_type,
                "platform": e.platform,
                "original_text": e.original_text[:100],
                "modified_text": e.modified_text[:100],
                "created_at": e.created_at.isoformat(),
            }
            for e in edits
        ],
        "total": len(edits),
    }
