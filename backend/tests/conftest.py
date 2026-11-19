import os
os.environ["TESTING"] = "1"
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from backend.app.database.session import Base, get_db
from backend.app.main import app
from backend.app.models.models import User, UserRole
from backend.app.security.passwords import get_password_hash
from backend.app.security.jwt import create_access_token
from scripts.seed_database import seed_database

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Seed the complete dataset into in-memory test database
    seed_database(target_engine=test_engine)

    # Add dedicated test users for assertions
    db = TestingSessionLocal()
    admin = User(
        email="test_admin@opspilot.ai",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Test Admin",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    agent = User(
        email="test_agent@opspilot.ai",
        hashed_password=get_password_hash("AgentPass123!"),
        full_name="Test Agent",
        role=UserRole.OPERATIONS_AGENT.value,
        is_active=True,
    )
    customer = User(
        email="test_customer@opspilot.ai",
        hashed_password=get_password_hash("CustPass123!"),
        full_name="Test Customer",
        role=UserRole.CUSTOMER.value,
        is_active=True,
    )
    db.add_all([admin, agent, customer])
    db.commit()
    db.close()

    yield

    test_engine.dispose()


@pytest.fixture
def db_session() -> Generator:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator:
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token() -> str:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "test_admin@opspilot.ai").first()
    db.close()
    return create_access_token(subject=str(user.id), role=user.role)


@pytest.fixture
def agent_token() -> str:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "test_agent@opspilot.ai").first()
    db.close()
    return create_access_token(subject=str(user.id), role=user.role)


@pytest.fixture
def customer_token() -> str:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "test_customer@opspilot.ai").first()
    db.close()
    return create_access_token(subject=str(user.id), role=user.role)


@pytest.fixture
def auth_headers(agent_token: str) -> dict:
    return {"Authorization": f"Bearer {agent_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}

