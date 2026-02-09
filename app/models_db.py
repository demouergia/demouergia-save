from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class SaveAssessment(Base):
    __tablename__ = "save_assessments"

    assessment_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    consent_research: Mapped[bool] = mapped_column(Boolean, default=True)

    meta_public: Mapped[dict] = mapped_column(JSONB, default=dict)
    responses_norm: Mapped[dict] = mapped_column(JSONB, default=dict)
    results: Mapped[dict] = mapped_column(JSONB, default=dict)
