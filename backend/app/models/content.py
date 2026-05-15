from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    taste_score: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="contents")  # noqa: F821
    project: Mapped["Project | None"] = relationship(back_populates="contents")  # noqa: F821
    taste_edits: Mapped[list["TasteEdit"]] = relationship(back_populates="content")  # noqa: F821
    analytics_entries: Mapped[list["Analytics"]] = relationship(back_populates="content")  # noqa: F821
    versions: Mapped[list["ContentVersion"]] = relationship(  # noqa: F821
        back_populates="content", order_by="ContentVersion.version_number"
    )
