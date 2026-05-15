from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TasteEdit(Base):
    __tablename__ = "taste_edits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(Integer, ForeignKey("contents.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    original_text: Mapped[str] = mapped_column(Text)
    modified_text: Mapped[str] = mapped_column(Text)
    diff_type: Mapped[str] = mapped_column(String(50))
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    content: Mapped["Content"] = relationship(back_populates="taste_edits")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="taste_edits")  # noqa: F821
