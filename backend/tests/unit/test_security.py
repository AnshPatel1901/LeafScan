"""
Unit tests for app.core.security — password hashing and JWT functions.
No database or HTTP involved.
"""

from __future__ import annotations

import uuid

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# ── Password hashing ──────────────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_is_not_plain_text(self):
        hashed = hash_password("MySecret@1")
        assert hashed != "MySecret@1"

    def test_verify_correct_password(self):
        hashed = hash_password("MySecret@1")
        assert verify_password("MySecret@1", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("MySecret@1")
        assert verify_password("WrongPass@1", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        # bcrypt uses random salt — same input → different hashes
        h1 = hash_password("Same@Pass1")
        h2 = hash_password("Same@Pass1")
        assert h1 != h2

    def test_empty_password_can_be_hashed(self):
        # Edge case — schema validation blocks empty passwords; security
        # layer must still be robust
        hashed = hash_password("")
        assert verify_password("", hashed) is True


# ── Access token ──────────────────────────────────────────────────────────────


class TestAccessToken:
    def test_create_and_decode_roundtrip(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        decoded = decode_access_token(token)
        assert decoded == user_id

    def test_decode_returns_string(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        result = decode_access_token(token)
        assert isinstance(result, str)

    def test_tampered_token_raises(self):
        token = create_access_token(str(uuid.uuid4()))
        bad_token = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_access_token(bad_token)

    def test_garbage_string_raises(self):
        with pytest.raises(JWTError):
            decode_access_token("not.a.jwt.at.all")

    def test_refresh_token_rejected_by_access_decoder(self):
        user_id = str(uuid.uuid4())
        refresh = create_refresh_token(user_id)
        with pytest.raises(JWTError):
            decode_access_token(refresh)


# ── Refresh token ─────────────────────────────────────────────────────────────


class TestRefreshToken:
    def test_create_and_decode_roundtrip(self):
        user_id = str(uuid.uuid4())
        token = create_refresh_token(user_id)
        decoded = decode_refresh_token(token)
        assert decoded == user_id

    def test_access_token_rejected_by_refresh_decoder(self):
        user_id = str(uuid.uuid4())
        access = create_access_token(user_id)
        with pytest.raises(JWTError):
            decode_refresh_token(access)

    def test_tampered_refresh_token_raises(self):
        token = create_refresh_token(str(uuid.uuid4()))
        bad = token[:10] + "BAD" + token[13:]
        with pytest.raises(JWTError):
            decode_refresh_token(bad)


# ── decode_token (raw payload) ────────────────────────────────────────────────


class TestDecodeToken:
    def test_payload_contains_expected_claims(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        payload = decode_token(token)

        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    def test_refresh_token_payload_type(self):
        token = create_refresh_token(str(uuid.uuid4()))
        payload = decode_token(token)
        assert payload["type"] == "refresh"
