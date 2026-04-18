"""
Prediction database model — stores ML/fallback disease detection result.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    plant_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    disease_name: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    is_plant: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    fallback_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    upload: Mapped["Upload"] = relationship(  # noqa: F821
        "Upload",
        back_populates="prediction",
    )
    ai_responses: Mapped[list["AIResponse"]] = relationship(  # noqa: F821
        "AIResponse",
        back_populates="prediction",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction id={self.id!s} "
            f"plant={self.plant_name!r} "
            f"disease={self.disease_name!r}>"
        )
