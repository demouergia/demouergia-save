"""SAVE data retention cleanup.

Default policy:
- After 90 days: clear `responses_norm` (set to empty JSON) while keeping `results` + `meta_public` for aggregated research.
- Optional: hard-delete records older than RETENTION_DELETE_DAYS (disabled by default).
"""

from __future__ import annotations
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

ANONYMIZE_AFTER_DAYS = int(os.getenv("ANONYMIZE_AFTER_DAYS", "90"))
RETENTION_DELETE_DAYS = int(os.getenv("RETENTION_DELETE_DAYS", "0"))  # 0 = disabled

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def main():
    with SessionLocal() as db:
        q1 = text("""
            UPDATE save_assessments
            SET responses_norm = '{}'::jsonb
            WHERE created_at < (NOW() - (:days || ' days')::interval)
              AND responses_norm IS NOT NULL
              AND responses_norm <> '{}'::jsonb;
        """)
        r1 = db.execute(q1, {"days": ANONYMIZE_AFTER_DAYS}).rowcount

        r2 = 0
        if RETENTION_DELETE_DAYS and RETENTION_DELETE_DAYS > 0:
            q2 = text("""
                DELETE FROM save_assessments
                WHERE created_at < (NOW() - (:days || ' days')::interval);
            """)
            r2 = db.execute(q2, {"days": RETENTION_DELETE_DAYS}).rowcount

        db.commit()

    print(f"Anonymized responses_norm for {r1} records (>= {ANONYMIZE_AFTER_DAYS} days old).") 
    if RETENTION_DELETE_DAYS and RETENTION_DELETE_DAYS > 0:
        print(f"Deleted {r2} records (>= {RETENTION_DELETE_DAYS} days old).") 

if __name__ == "__main__":
    main()
