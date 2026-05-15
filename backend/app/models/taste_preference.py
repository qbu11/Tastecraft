from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TastePreference(Base):
    __tablename__ = "taste_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True, index=True
    )
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    dimension: Mapped[str] = mapped_column(String(100))
    rule: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_edit_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confirmed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship()  # noqa: F821
    project: Mapped["Project | None"] = relationship()  # noqa: F821
