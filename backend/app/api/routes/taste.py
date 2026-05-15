from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.content import Content
from app.models.taste_edit import TasteEdit
from app.models.taste_preference import TastePreference
from app.models.user import User
from app.schemas.diff import (
    CaptureEditResponse,
    EditCapture,
    TastePreferenceResponse,
    TasteSummary,
)
from app.services.diff_engine import DiffEngine
from app.services.pattern_extractor import PatternExtractor

router = APIRouter(prefix="/taste", tags=["taste"])

# Threshold: trigger pattern extraction after this many edits
_EXTRACTION_THRESHOLD = 3


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


@router.put("/capture-edit")
async def capture_edit(
    payload: EditCapture,
    content_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CaptureEditResponse:
    """Capture an edit and extract signals. Triggers pattern extraction at threshold."""
    engine = DiffEngine(db)

    # Classify the edit
    classification = engine.classify_edit(payload.original, payload.modified)

    # If no content_id provided, use 0 as placeholder (standalone capture)
    effective_content_id = content_id or 0

    edit = await engine.capture_edit(
        content_id=effective_content_id,
        user_id=current_user.id,
        original=payload.original,
        modified=payload.modified,
        platform=payload.platform,
        content_line_id=payload.content_line_id,
    )

    # Check if we should trigger pattern extraction
    total_edits = await engine.get_user_edit_count(current_user.id, payload.platform)
    new_prefs_count = 0

    if total_edits >= _EXTRACTION_THRESHOLD and total_edits % _EXTRACTION_THRESHOLD == 0:
        extractor = PatternExtractor(db)
        new_prefs = await extractor.run_extraction_pipeline(
            current_user.id, payload.platform
        )
        new_prefs_count = len(new_prefs)

    return CaptureEditResponse(
        edit_id=edit.id,
        classification=classification,
        new_preferences_extracted=new_prefs_count,
        total_edits=total_edits,
    )


@router.get("/preferences", response_model=list[TastePreferenceResponse])
async def list_preferences(
    platform: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TastePreference]:
    """List all extracted preferences for the current user."""
    query = (
        select(TastePreference)
        .where(TastePreference.user_id == current_user.id)
        .order_by(TastePreference.confidence.desc())
    )
    if platform:
        query = query.where(TastePreference.platform == platform)

    result = await db.execute(query)
    preferences = list(result.scalars().all())

    # Enrich with edit_count from source_edit_ids
    for pref in preferences:
        if not hasattr(pref, "edit_count"):
            pref.edit_count = len(pref.source_edit_ids) if pref.source_edit_ids else 0  # type: ignore[attr-defined]

    return preferences


@router.delete("/preferences/{preference_id}")
async def delete_preference(
    preference_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """User rejects a learned preference — removes it permanently."""
    result = await db.execute(
        select(TastePreference).where(
            TastePreference.id == preference_id,
            TastePreference.user_id == current_user.id,
        )
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    await db.delete(pref)
    await db.flush()
    return {"deleted": True, "id": preference_id}


@router.post("/preferences/{preference_id}/confirm")
async def confirm_preference(
    preference_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """User confirms a preference — boosts confidence to maximum."""
    result = await db.execute(
        select(TastePreference).where(
            TastePreference.id == preference_id,
            TastePreference.user_id == current_user.id,
        )
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    pref.confirmed = True
    pref.confidence = 0.95  # Max confidence on user confirmation
    await db.flush()

    return {
        "id": pref.id,
        "dimension": pref.dimension,
        "rule": pref.rule,
        "confidence": pref.confidence,
        "confirmed": True,
    }


@router.get("/summary", response_model=TasteSummary)
async def get_taste_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Complete taste summary — score + preferences + history."""
    engine = DiffEngine(db)
    summary = await engine.get_preference_summary(current_user.id)

    # Convert preference models to response format
    pref_responses = []
    for p in summary["preferences"]:
        pref_responses.append(
            TastePreferenceResponse(
                id=p.id,
                dimension=p.dimension,
                rule=p.rule,
                confidence=p.confidence,
                platform=p.platform,
                edit_count=len(p.source_edit_ids) if p.source_edit_ids else 0,
                confirmed=p.confirmed,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )

    return {
        "preferences": pref_responses,
        "total_edits": summary["total_edits"],
        "taste_score": summary["taste_score"],
        "platforms": summary["platforms"],
        "dimensions_covered": summary["dimensions_covered"],
    }
