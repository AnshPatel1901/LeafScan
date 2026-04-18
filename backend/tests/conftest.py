"""
Shared pytest fixtures for the entire test suite.

Uses an in-memory SQLite database via aiosqlite for fast, isolated tests.
The application is re-created fresh for every test session.
"""

from __future__ import annotations

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.base import Base
from app.main import create_app
from app.models.user import User

# ── In-memory test database ───────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

_TestSession = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh, rolled-back session for each test."""
    async with _TestSession() as session:
        yield session
        await session.rollback()


# ── Test application & HTTP client ────────────────────────────────────────────


@pytest.fixture()
def app(db_session: AsyncSession):
    """Return a FastAPI app wired to the test DB session."""
    from app.core.dependencies import get_db

    fastapi_app = create_app()

    async def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    return fastapi_app


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Reusable domain fixtures ──────────────────────────────────────────────────


@pytest.fixture()
async def test_user(db_session: AsyncSession) -> User:
    """
    Insert a user with a unique username per test.
    The UUID suffix prevents UNIQUE constraint collisions across
    tests sharing the same in-memory SQLite engine.
    """
    import uuid as _uuid
    from app.repositories.user_repository import UserRepository

    suffix = _uuid.uuid4().hex[:8]
    username = f"testuser_{suffix}"
    repo = UserRepository(db_session)
    user = await repo.create(
        username=username,
        password_hash=hash_password("TestPass@1"),
    )
    # Attach plain username for use by auth_headers fixture
    user._test_username = username  # type: ignore[attr-defined]
    return user


@pytest.fixture()
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """Return Authorization headers for *test_user*."""
    username = getattr(test_user, "_test_username", test_user.username)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "TestPass@1"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    token = resp.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── ML service mocks ──────────────────────────────────────────────────────────


@pytest.fixture()
def mock_plant_validator():
    """PlantValidatorService stub — always returns is_plant=True."""
    from app.services.plant_validator_service import PlantValidationResult

    svc = MagicMock()
    svc.validate = AsyncMock(
        return_value=PlantValidationResult(
            is_plant=True, confidence=0.95, message="Is a plant"
        )
    )
    return svc


@pytest.fixture()
def mock_plant_validator_negative():
    """PlantValidatorService stub — always returns is_plant=False."""
    from app.services.plant_validator_service import PlantValidationResult

    svc = MagicMock()
    svc.validate = AsyncMock(
        return_value=PlantValidationResult(
            is_plant=False, confidence=0.10, message="Not a plant"
        )
    )
    return svc


@pytest.fixture()
def mock_disease_model_high_confidence():
    """DiseaseModelService stub — returns result above threshold."""
    from app.services.disease_model_service import DiseaseDetectionResult

    svc = MagicMock()
    svc.detect = AsyncMock(
        return_value=DiseaseDetectionResult(
            plant_name="Tomato",
            disease_name="Early Blight",
            confidence_score=0.92,
        )
    )
    return svc


@pytest.fixture()
def mock_disease_model_low_confidence():
    """DiseaseModelService stub — returns result below threshold (triggers fallback)."""
    from app.services.disease_model_service import DiseaseDetectionResult

    svc = MagicMock()
    svc.detect = AsyncMock(
        return_value=DiseaseDetectionResult(
            plant_name="Tomato",
            disease_name="Early Blight",
            confidence_score=0.45,
        )
    )
    return svc


@pytest.fixture()
def mock_fallback_service():
    """FallbackService stub — returns a fixed Gemini prediction."""
    from app.services.fallback_service import FallbackPrediction

    svc = MagicMock()
    svc.predict = AsyncMock(
        return_value=FallbackPrediction(
            plant_name="Tomato",
            disease_name="Late Blight",
            confidence_score=0.88,
        )
    )
    return svc


@pytest.fixture()
def mock_llm_service():
    """LLMService stub — returns static precautions text."""
    from app.services.llm_service import LLMResult

    svc = MagicMock()
    svc.generate_precautions = AsyncMock(
        return_value=LLMResult(
            precautions_text="Apply fungicide. Remove affected leaves. "
                             "Ensure good air circulation.",
            audio_url=None,
        )
    )
    return svc


# ── Minimal valid JPEG bytes (1×1 pixel) ──────────────────────────────────────

TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
    b"B=3\x1c\x1c\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04"
    b"\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa"
    b"\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n"
    b"\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz"
    b"\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99"
    b"\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7"
    b"\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5"
    b"\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1"
    b"\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00"
    b"\x00?\x00\xfb\xd4\xff\xd9"
)
