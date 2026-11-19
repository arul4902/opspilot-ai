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

_db_initialized = False

def ensure_database_initialized():
    global _db_initialized
    if _db_initialized:
        return
    
    if os.environ.get("TESTING") == "1":
        _db_initialized = True
        return

    from backend.app.core.logging import logger
    try:
        import backend.app.database.base
        Base.metadata.create_all(bind=engine)
        
        from backend.app.models.models import User
        with SessionLocal() as check_db:
            if check_db.query(User).count() == 0:
                logger.info("Database empty on boot, auto-seeding demo accounts...")
                from backend.app.database.seeder import seed_database
                seed_database(target_engine=engine)
        _db_initialized = True
    except Exception as e:
        logger.warning(f"ensure_database_initialized warning: {e}")

def get_db():
    if os.environ.get("TESTING") == "1":
        from backend.tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
    else:
        ensure_database_initialized()
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

