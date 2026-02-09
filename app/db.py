from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import DATABASE_URL

class Base(DeclarativeBase):
    pass

def get_engine():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )

ENGINE = None
SessionLocal = None

def init_db():
    global ENGINE, SessionLocal
    ENGINE = get_engine()
    SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)

def get_session():
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
