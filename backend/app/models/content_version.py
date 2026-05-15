"""ContentVersion model — tracks every version of a content piece.

Every generation, user edit, style adjustment, or variant expansion creates
a new version. Users can compare versions side-by-side and rollback.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ContentVersion(Base):
    __tablename__ = "content_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contents.id"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(50))
    created_by: Mapped[str] = mapped_column(
        String(30), default="user_edited"
    )  # ai_generated | user_edited | style_adjusted | variant_expanded
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    content: Mapped["Content"] = relationship(back_populates="versions")  # noqa: F821
