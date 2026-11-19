import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    if os.environ.get("TESTING") == "1":
        from backend.tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
    else:
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

