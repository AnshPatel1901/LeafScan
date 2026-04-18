"""
Integration tests for /api/v1/auth/* endpoints.
Uses real service layer + in-memory SQLite DB (via conftest fixtures).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


BASE = "/api/v1/auth"


# ── POST /auth/signup ─────────────────────────────────────────────────────────


class TestSignup:
    async def test_successful_signup(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/signup",
            json={"username": "newuser01", "password": "Secure@Pass1"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["user"]["username"] == "newuser01"
        assert "access_token" in body["data"]["tokens"]
        assert "refresh_token" in body["data"]["tokens"]

    async def test_duplicate_username_returns_409(self, client: AsyncClient):
        payload = {"username": "duplicate01", "password": "Secure@Pass1"}
        await client.post(f"{BASE}/signup", json=payload)
        resp = await client.post(f"{BASE}/signup", json=payload)
        assert resp.status_code == 409
        assert resp.json()["success"] is False

    async def test_weak_password_returns_422(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/signup",
            json={"username": "weakuser01", "password": "short"},
        )
        assert resp.status_code == 422

    async def test_missing_fields_returns_422(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/signup", json={"username": "only"})
        assert resp.status_code == 422

    async def test_invalid_username_characters_returns_422(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/signup",
            json={"username": "bad user!", "password": "Secure@Pass1"},
        )
        assert resp.status_code == 422

    async def test_username_stored_lowercase(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/signup",
            json={"username": "CamelCase01", "password": "Secure@Pass1"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["user"]["username"] == "camelcase01"

    async def test_response_has_standard_envelope(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/signup",
            json={"username": "envelopetest", "password": "Secure@Pass1"},
        )
        body = resp.json()
        assert "success" in body
        assert "data" in body
        assert "message" in body


# ── POST /auth/login ──────────────────────────────────────────────────────────


class TestLogin:
    async def test_valid_login_returns_tokens(
        self, client: AsyncClient, test_user
    ):
        resp = await client.post(
            f"{BASE}/login",
            json={"username": test_user.username, "password": "TestPass@1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        tokens = body["data"]["tokens"]
        assert tokens["access_token"]
        assert tokens["refresh_token"]
        assert tokens["token_type"] == "bearer"

    async def test_wrong_password_returns_401(
        self, client: AsyncClient, test_user
    ):
        resp = await client.post(
            f"{BASE}/login",
            json={"username": test_user.username, "password": "WrongPass@1"},
        )
        assert resp.status_code == 401
        assert resp.json()["success"] is False

    async def test_nonexistent_user_returns_401(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/login",
            json={"username": "ghost", "password": "TestPass@1"},
        )
        assert resp.status_code == 401

    async def test_login_includes_user_profile(
        self, client: AsyncClient, test_user
    ):
        resp = await client.post(
            f"{BASE}/login",
            json={"username": test_user.username, "password": "TestPass@1"},
        )
        user = resp.json()["data"]["user"]
        assert user["username"] == test_user.username
        assert "id" in user
        assert "created_at" in user
        # password_hash must never appear
        assert "password_hash" not in user
        assert "password" not in user


# ── POST /auth/refresh-token ──────────────────────────────────────────────────


class TestRefreshToken:
    async def test_valid_refresh_token_issues_new_access_token(
        self, client: AsyncClient, test_user
    ):
        login_resp = await client.post(
            f"{BASE}/login",
            json={"username": test_user.username, "password": "TestPass@1"},
        )
        refresh_token = login_resp.json()["data"]["tokens"]["refresh_token"]

        resp = await client.post(
            f"{BASE}/refresh-token",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["access_token"]
        assert data["token_type"] == "bearer"

    async def test_invalid_refresh_token_returns_401(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/refresh-token",
            json={"refresh_token": "totally.invalid.token"},
        )
        assert resp.status_code == 401

    async def test_access_token_rejected_as_refresh(
        self, client: AsyncClient, test_user
    ):
        login_resp = await client.post(
            f"{BASE}/login",
            json={"username": test_user.username, "password": "TestPass@1"},
        )
        access_token = login_resp.json()["data"]["tokens"]["access_token"]

        resp = await client.post(
            f"{BASE}/refresh-token",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401
