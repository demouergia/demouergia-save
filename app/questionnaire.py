from __future__ import annotations
import json
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "questionnaire_schema.json"

def load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
