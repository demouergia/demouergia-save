# SAVE Model API + Database Starter (FastAPI + Postgres)

This starter supports **GDPR-friendly research storage**, saving only:
- `profile_id` (UUID)
- `meta_public` (non-identifying: sector, employment, years_experience, etc.)
- `responses_norm` (0..1) *(optionally cleared after 90 days)*
- `results` (SAVE score, capital vector, bottlenecks, risk)

## Local run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit DATABASE_URL and SAVE_API_KEY
uvicorn app.main:app --reload
```
Swagger UI: http://127.0.0.1:8000/docs

## Endpoints
- POST `/v1/save/diagnose` (compute only)
- POST `/v1/save/assessments` (compute + store)
- GET  `/v1/save/assessments/{assessment_id}`
- GET  `/v1/save/research/export?format=csv|json` (admin)
- GET  `/v1/save/research/stats?...` (admin JSON aggregates)
- GET  `/v1/save/research/stats.csv?...` (admin CSV aggregates)
- GET  `/v1/save/profile/{assessment_id}?lang=en|el` (admin; UI-ready personal profile)

### k-anonymity
Use `k_min` (default 5) on stats endpoints to suppress groups with `count < k_min`.

## Retention / anonymization
Run daily:
```bash
python scripts/cleanup.py
```
Defaults:
- `ANONYMIZE_AFTER_DAYS=90` → clears `responses_norm` (keeps `results` + `meta_public`)
- Optional: `RETENTION_DELETE_DAYS=0` (disabled). Set e.g. `365` to hard-delete after 1 year.


## Imported questionnaire (SAVER Model 1)
This build includes a questionnaire imported from the provided PDF (0–5 scale) and mapped to SAVE/SAVER keys.
