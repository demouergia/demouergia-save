from __future__ import annotations
import uuid
from sqlalchemy.orm import Session
from .models_db import SaveAssessment

def create_assessment(db: Session, profile_id: str | None, consent_research: bool, meta_public: dict, responses_norm: dict, results: dict) -> SaveAssessment:
    pid = profile_id or str(uuid.uuid4())
    obj = SaveAssessment(
        profile_id=pid,
        consent_research=consent_research,
        meta_public=meta_public or {},
        responses_norm=responses_norm or {},
        results=results or {},
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_assessment(db: Session, assessment_id: str) -> SaveAssessment | None:
    return db.get(SaveAssessment, assessment_id)

def list_assessments_for_export(db: Session, limit: int = 50000):
    return (
        db.query(SaveAssessment)
        .filter(SaveAssessment.consent_research == True)
        .order_by(SaveAssessment.created_at.asc())
        .limit(limit)
        .all()
    )
