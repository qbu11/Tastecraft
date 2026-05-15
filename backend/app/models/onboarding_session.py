"""Onboarding session model — tracks conversational onboarding state."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OnboardingSession(Base):
    __tablename__ = "onboarding_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    current_step: Mapped[str] = mapped_column(String(50), default="lane_positioning")
    step_index: Mapped[int] = mapped_column(Integer, default=0)

    # Conversation history and collected structured data
    messages: Mapped[dict] = mapped_column(JSON, default=list)
    collected_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Import/competitor tracking
    imported_content_urls: Mapped[dict] = mapped_column(JSON, default=list)
    imported_content_count: Mapped[int] = mapped_column(Integer, default=0)
    style_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    competitors_added: Mapped[int] = mapped_column(Integer, default=0)
    competitor_urls: Mapped[dict] = mapped_column(JSON, default=list)

    # Timestamps
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Generated first content (aha moment)
    first_generated_content: Mapped[str | None] = mapped_column(Text, nullable=True)
