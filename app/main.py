from __future__ import annotations
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import io, csv, json
from sqlalchemy.orm import Session

from .config import SAVE_API_KEY
from .models_api import DiagnoseRequest, AssessmentCreateRequest
from .questionnaire import load_schema
from .save_engine import diagnose
from .db import init_db, get_session, Base, get_engine
from . import models_db  # registers table model
from .crud import create_assessment, get_assessment, list_assessments_for_export
from .profile_engine import build_profile

app = FastAPI(title="SAVE Model API (with DB)", version="1.0")

def check_auth(authorization: Optional[str]) -> None:
    if not SAVE_API_KEY:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.replace("Bearer ", "", 1).strip()
    if token != SAVE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid token")

@app.on_event("startup")
def on_startup():
    init_db()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

@app.get("/v1/health")
def health():
    return {"status": "ok"}

@app.get("/v1/save/questionnaire")
def questionnaire(lang: str = "en"):
    schema = load_schema()
    if lang not in schema.get("languages", []):
        raise HTTPException(status_code=400, detail=f"Unsupported lang: {lang}")
    return schema

@app.post("/v1/save/diagnose")
def save_diagnose(req: DiagnoseRequest, authorization: Optional[str] = Header(default=None)):
    check_auth(authorization)
    return diagnose(req.meta, req.responses)

@app.post("/v1/save/assessments")
def create_save_assessment(
    req: AssessmentCreateRequest,
    db: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
):
    check_auth(authorization)

    computed = diagnose(req.meta_public, req.responses)
    responses_norm = computed.pop("responses_norm")
    results = computed

    obj = create_assessment(
        db=db,
        profile_id=req.profile_id,
        consent_research=req.consent_research,
        meta_public=req.meta_public,
        responses_norm=responses_norm,
        results=results,
    )

    return {
        "assessment_id": obj.assessment_id,
        "profile_id": obj.profile_id,
        "created_at": obj.created_at.isoformat(),
        "consent_research": obj.consent_research,
        "meta_public": obj.meta_public,
        "responses_norm": obj.responses_norm,
        "results": obj.results,
    }

@app.get("/v1/save/assessments/{assessment_id}")
def read_save_assessment(
    assessment_id: str,
    db: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
):
    check_auth(authorization)
    obj = get_assessment(db, assessment_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "assessment_id": obj.assessment_id,
        "profile_id": obj.profile_id,
        "created_at": obj.created_at.isoformat(),
        "consent_research": obj.consent_research,
        "meta_public": obj.meta_public,
        "responses_norm": obj.responses_norm,
        "results": obj.results,
    }


@app.get("/v1/save/profile/{assessment_id}")
def get_profile(
    assessment_id: str,
    lang: str = "en",
    db: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
):
    # Admin-only (API key). You can adjust later for end-user access.
    check_auth(authorization)
    obj = get_assessment(db, assessment_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return build_profile(
        assessment_id=obj.assessment_id,
        profile_id=obj.profile_id,
        meta_public=obj.meta_public or {},
        results=obj.results or {},
        lang=lang,
    )

@app.get("/v1/save/research/stats")
def research_stats(
    group_by: str = "sector",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    k_min: int = 5,
    limit: int = 50000,
    db: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
):
    check_auth(authorization)

    groups = [g.strip() for g in group_by.split(",") if g.strip()]
    allowed = {"sector","employment","years_experience"}
    for g in groups:
        if g not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid group_by field: {g}")

    q = db.query(models_db.SaveAssessment).filter(models_db.SaveAssessment.consent_research == True)
    if date_from:
        q = q.filter(models_db.SaveAssessment.created_at >= date_from)
    if date_to:
        q = q.filter(models_db.SaveAssessment.created_at < date_to)

    rows = q.order_by(models_db.SaveAssessment.created_at.asc()).limit(limit).all()

    def group_key(meta: dict):
        meta = meta or {}
        return tuple(meta.get(g, "") for g in groups)

    agg = {}
    for r in rows:
        meta = r.meta_public or {}
        res = r.results or {}
        k = group_key(meta)
        bucket = agg.setdefault(k, {"count": 0, "save": [], "riskV": [], "S": [], "H": [], "C": [], "E": [], "I": []})
        bucket["count"] += 1

        if isinstance(res.get("save_score"), (int, float)):
            bucket["save"].append(float(res["save_score"]))

        risk = res.get("risk") or {}
        if isinstance(risk.get("V"), (int, float)):
            bucket["riskV"].append(float(risk["V"]))

        cv = res.get("capital_vector") or {}
        for c in ["S","H","C","E","I"]:
            if isinstance(cv.get(c), (int, float)):
                bucket[c].append(float(cv[c]))

    out = []
    k_min = max(1, int(k_min))
    for k, b in agg.items():
        rec = {groups[i]: k[i] for i in range(len(groups))}
        rec["count"] = b["count"]
        if rec["count"] < k_min:
            continue
        rec["mean_save_score"] = (sum(b["save"]) / len(b["save"])) if b["save"] else None
        rec["mean_risk_V"] = (sum(b["riskV"]) / len(b["riskV"])) if b["riskV"] else None
        rec["mean_capital_vector"] = {c: (sum(b[c]) / len(b[c])) if b[c] else None for c in ["S","H","C","E","I"]}
        out.append(rec)

    out.sort(key=lambda x: x["count"], reverse=True)
    return {"group_by": groups, "k_min": k_min, "count_groups": len(out), "rows": out}

@app.get("/v1/save/research/stats.csv")
def research_stats_csv(
    group_by: str = "sector",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    k_min: int = 5,
    limit: int = 50000,
    db: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
):
    check_auth(authorization)
    data = research_stats(
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
        k_min=k_min,
        limit=limit,
        db=db,
        authorization=authorization,
    )
    rows = data.get("rows", [])
    groups = data.get("group_by", [])

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    header = list(groups) + ["count","mean_save_score","mean_risk_V","mean_S","mean_H","mean_C","mean_E","mean_I"]
    writer.writerow(header)

    for r in rows:
        cv = r.get("mean_capital_vector") or {}
        writer.writerow(
            [r.get(g,"") for g in groups] + [
                r.get("count",""),
                r.get("mean_save_score",""),
                r.get("mean_risk_V",""),
                cv.get("S",""),
                cv.get("H",""),
                cv.get("C",""),
                cv.get("E",""),
                cv.get("I",""),
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition":"attachment; filename=save_stats.csv"},
    )

@app.get("/v1/save/research/export")
def research_export(
    format: str = "csv",
    limit: int = 50000,
    db: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
):
    check_auth(authorization)
    rows = list_assessments_for_export(db, limit=limit)

    if format.lower() == "json":
        out = []
        for r in rows:
            out.append({
                "assessment_id": r.assessment_id,
                "profile_id": r.profile_id,
                "created_at": r.created_at.isoformat(),
                "meta_public": r.meta_public,
                "results": r.results,
            })
        return JSONResponse({"count": len(out), "records": out})

    def stream():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["assessment_id","profile_id","created_at","sector","employment","years_experience","save_score","capital_vector","risk_V","bottlenecks"])
        yield buffer.getvalue()
        buffer.seek(0); buffer.truncate(0)
        for r in rows:
            meta = r.meta_public or {}
            res = r.results or {}
            writer.writerow([
                r.assessment_id,
                r.profile_id,
                r.created_at.isoformat(),
                meta.get("sector",""),
                meta.get("employment",""),
                meta.get("years_experience",""),
                res.get("save_score",""),
                json.dumps(res.get("capital_vector",{}), ensure_ascii=False),
                (res.get("risk",{}) or {}).get("V",""),
                json.dumps(res.get("bottlenecks",[]), ensure_ascii=False),
            ])
            yield buffer.getvalue()
            buffer.seek(0); buffer.truncate(0)

    return StreamingResponse(stream(), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=save_export.csv"})
