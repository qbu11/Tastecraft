from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import Team, TeamMember, TeamRole
from app.models.user import User


class TeamService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_team(self, owner_id: int, name: str) -> Team:
        team = Team(name=name, owner_id=owner_id)
        self.db.add(team)
        await self.db.flush()
        await self.db.refresh(team)

        # Add owner as a member with owner role
        member = TeamMember(
            team_id=team.id,
            user_id=owner_id,
            role=TeamRole.owner,
            accepted_at=datetime.utcnow(),
        )
        self.db.add(member)
        await self.db.flush()
        return team

    async def invite_member(
        self, team_id: int, email: str, role: str
    ) -> TeamMember:
        # Find user by email
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User with email {email} not found")

        # Check if already a member
        result = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user.id,
            )
        )
        if result.scalar_one_or_none():
            raise ValueError("User is already a team member")

        member = TeamMember(
            team_id=team_id,
            user_id=user.id,
            role=TeamRole(role),
            accepted_at=datetime.utcnow(),
        )
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def remove_member(self, team_id: int, user_id: int) -> None:
        result = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("Member not found")
        if member.role == TeamRole.owner:
            raise ValueError("Cannot remove the team owner")
        await self.db.delete(member)

    async def get_team(self, user_id: int) -> Team | None:
        result = await self.db.execute(
            select(Team)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .where(TeamMember.user_id == user_id)
            .options(selectinload(Team.members))
        )
        return result.scalar_one_or_none()

    async def get_members(self, team_id: int) -> list[dict]:
        result = await self.db.execute(
            select(TeamMember, User.email)
            .join(User, TeamMember.user_id == User.id)
            .where(TeamMember.team_id == team_id)
        )
        rows = result.all()
        members = []
        for member, email in rows:
            members.append({
                "id": member.id,
                "user_id": member.user_id,
                "email": email,
                "role": member.role.value,
                "invited_at": member.invited_at,
                "accepted_at": member.accepted_at,
            })
        return members

    async def check_permission(self, user_id: int, team_id: int, action: str) -> bool:
        result = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False

        role = member.role
        if action in ("delete_team", "invite", "remove_member", "change_role"):
            return role == TeamRole.owner
        if action in ("create_content", "edit_content", "publish"):
            return role in (TeamRole.owner, TeamRole.editor)
        if action in ("view_content", "view_analytics"):
            return True
        return False

    async def update_member_role(
        self, team_id: int, user_id: int, new_role: str
    ) -> TeamMember:
        result = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("Member not found")
        if member.role == TeamRole.owner:
            raise ValueError("Cannot change owner role")
        member.role = TeamRole(new_role)
        await self.db.flush()
        await self.db.refresh(member)
        return member
