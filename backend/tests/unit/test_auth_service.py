"""
Unit tests for AuthService.
The UserRepository is mocked so no DB is needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.security import create_refresh_token, hash_password
from app.services.auth_service import AuthService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_repo(*, exists=False, user=None):
    repo = MagicMock()
    repo.username_exists = AsyncMock(return_value=exists)
    repo.create = AsyncMock(return_value=user)
    repo.get_by_username = AsyncMock(return_value=user)
    repo.get_by_id = AsyncMock(return_value=user)
    return repo


def _make_user(username="alice", password="Secret@99"):
    import uuid
    from datetime import datetime, timezone

    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = username
    user.password_hash = hash_password(password)
    user.created_at = datetime.now(timezone.utc)
    return user


# ── Signup ────────────────────────────────────────────────────────────────────


class TestSignup:
    async def test_success_returns_user_and_tokens(self):
        user = _make_user()
        repo = _make_repo(exists=False, user=user)
        svc = AuthService(repo)

        result = await svc.signup("alice", "Secret@99")

        assert result.user.username == "alice"
        assert result.tokens.access_token
        assert result.tokens.refresh_token
        assert result.tokens.token_type == "bearer"

    async def test_duplicate_username_raises(self):
        repo = _make_repo(exists=True)
        svc = AuthService(repo)

        with pytest.raises(UserAlreadyExistsError):
            await svc.signup("alice", "Secret@99")

    async def test_create_called_with_hashed_password(self):
        user = _make_user()
        repo = _make_repo(exists=False, user=user)
        svc = AuthService(repo)

        await svc.signup("alice", "Secret@99")

        repo.create.assert_awaited_once()
        call_kwargs = repo.create.call_args.kwargs
        # Must store hash, never plain text
        assert call_kwargs["password_hash"] != "Secret@99"
        assert call_kwargs["username"] == "alice"


# ── Login ─────────────────────────────────────────────────────────────────────


class TestLogin:
    async def test_valid_credentials_return_tokens(self):
        user = _make_user(password="Secret@99")
        repo = _make_repo(user=user)
        svc = AuthService(repo)

        result = await svc.login("alice", "Secret@99")

        assert result.tokens.access_token
        assert result.tokens.refresh_token

    async def test_wrong_password_raises(self):
        user = _make_user(password="Secret@99")
        repo = _make_repo(user=user)
        svc = AuthService(repo)

        with pytest.raises(InvalidCredentialsError):
            await svc.login("alice", "WrongPass@1")

    async def test_unknown_user_raises(self):
        repo = _make_repo(user=None)
        svc = AuthService(repo)

        with pytest.raises(InvalidCredentialsError):
            await svc.login("ghost", "Secret@99")


# ── Refresh token ─────────────────────────────────────────────────────────────


class TestRefreshToken:
    async def test_valid_refresh_token_returns_access_token(self):
        user = _make_user()
        repo = _make_repo(user=user)
        svc = AuthService(repo)
        refresh = create_refresh_token(str(user.id))

        result = await svc.refresh_token(refresh)

        assert result.access_token
        assert result.token_type == "bearer"

    async def test_garbage_token_raises(self):
        repo = _make_repo(user=None)
        svc = AuthService(repo)

        with pytest.raises(InvalidTokenError):
            await svc.refresh_token("not.a.token")

    async def test_access_token_rejected_as_refresh(self):
        from app.core.security import create_access_token
        user = _make_user()
        repo = _make_repo(user=user)
        svc = AuthService(repo)
        access = create_access_token(str(user.id))

        with pytest.raises(InvalidTokenError):
            await svc.refresh_token(access)

    async def test_missing_user_raises(self):
        import uuid
        repo = _make_repo(user=None)
        svc = AuthService(repo)
        refresh = create_refresh_token(str(uuid.uuid4()))

        with pytest.raises(InvalidTokenError):
            await svc.refresh_token(refresh)
