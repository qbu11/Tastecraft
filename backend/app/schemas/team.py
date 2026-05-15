from datetime import datetime

from pydantic import BaseModel, EmailStr


class TeamCreate(BaseModel):
    name: str


class TeamResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberInvite(BaseModel):
    email: EmailStr
    role: str = "viewer"


class TeamMemberResponse(BaseModel):
    id: int
    user_id: int
    email: str
    role: str
    invited_at: datetime
    accepted_at: datetime | None

    model_config = {"from_attributes": True}


class TeamWithMembers(BaseModel):
    team: TeamResponse
    members: list[TeamMemberResponse]


class RoleUpdate(BaseModel):
    role: str
