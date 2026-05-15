from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.team import (
    MemberInvite,
    RoleUpdate,
    TeamCreate,
    TeamMemberResponse,
    TeamResponse,
    TeamWithMembers,
)
from app.services.team_service import TeamService

router = APIRouter(prefix="/team", tags=["team"])


def _get_service(db: AsyncSession = Depends(get_db)) -> TeamService:
    return TeamService(db)


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    current_user: User = Depends(get_current_user),
    svc: TeamService = Depends(_get_service),
) -> TeamResponse:
    team = await svc.create_team(current_user.id, payload.name)
    return TeamResponse.model_validate(team)


@router.get("/", response_model=TeamWithMembers)
async def get_team(
    current_user: User = Depends(get_current_user),
    svc: TeamService = Depends(_get_service),
) -> TeamWithMembers:
    team = await svc.get_team(current_user.id)
    if not team:
        raise HTTPException(status_code=404, detail="No team found")
    members_raw = await svc.get_members(team.id)
    members = [TeamMemberResponse(**m) for m in members_raw]
    return TeamWithMembers(
        team=TeamResponse.model_validate(team),
        members=members,
    )


@router.post("/invite", response_model=TeamMemberResponse)
async def invite_member(
    payload: MemberInvite,
    current_user: User = Depends(get_current_user),
    svc: TeamService = Depends(_get_service),
) -> TeamMemberResponse:
    team = await svc.get_team(current_user.id)
    if not team:
        raise HTTPException(status_code=404, detail="No team found")

    has_perm = await svc.check_permission(current_user.id, team.id, "invite")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Only owners can invite members")

    try:
        member = await svc.invite_member(team.id, payload.email, payload.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    members_raw = await svc.get_members(team.id)
    for m in members_raw:
        if m["user_id"] == member.user_id:
            return TeamMemberResponse(**m)

    raise HTTPException(status_code=500, detail="Failed to retrieve invited member")


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: int,
    current_user: User = Depends(get_current_user),
    svc: TeamService = Depends(_get_service),
) -> None:
    team = await svc.get_team(current_user.id)
    if not team:
        raise HTTPException(status_code=404, detail="No team found")

    has_perm = await svc.check_permission(current_user.id, team.id, "remove_member")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Only owners can remove members")

    try:
        await svc.remove_member(team.id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/members/{user_id}/role", response_model=TeamMemberResponse)
async def update_role(
    user_id: int,
    payload: RoleUpdate,
    current_user: User = Depends(get_current_user),
    svc: TeamService = Depends(_get_service),
) -> TeamMemberResponse:
    team = await svc.get_team(current_user.id)
    if not team:
        raise HTTPException(status_code=404, detail="No team found")

    has_perm = await svc.check_permission(current_user.id, team.id, "change_role")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Only owners can change roles")

    try:
        await svc.update_member_role(team.id, user_id, payload.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    members_raw = await svc.get_members(team.id)
    for m in members_raw:
        if m["user_id"] == user_id:
            return TeamMemberResponse(**m)

    raise HTTPException(status_code=500, detail="Failed to retrieve updated member")
