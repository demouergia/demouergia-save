from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class DiagnoseRequest(BaseModel):
    meta: Dict[str, Any] = Field(default_factory=dict)
    responses: Dict[str, Any]

class AssessmentCreateRequest(BaseModel):
    profile_id: Optional[str] = None
    consent_research: bool = True
    meta_public: Dict[str, Any] = Field(default_factory=dict)
    responses: Dict[str, Any]
