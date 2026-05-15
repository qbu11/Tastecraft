from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Analytics(Base):
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contents.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    platform: Mapped[str] = mapped_column(String(50))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    collection_type: Mapped[str] = mapped_column(
        String(10),
        comment="t24h | t72h | t7d",
    )

    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)

    content: Mapped["Content"] = relationship(back_populates="analytics_entries")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="analytics_entries")  # noqa: F821
