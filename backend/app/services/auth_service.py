"""
Auth service — business logic for registration, login, and token refresh.
Sits between the route layer and the repository/security layers.
"""

from __future__ import annotations

import logging

from jose import JWTError

from app.core.config import settings
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginResponse,
    RefreshTokenResponse,
    SignupResponse,
    TokenPair,
    UserProfile,
)

logger = logging.getLogger(__name__)


def _build_token_pair(user_id: str) -> TokenPair:
    logger.debug(f"Building token pair for user_id: {user_id}")
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def signup(self, username: str, password: str) -> SignupResponse:
        """
        Create a new user account.

        Raises
        ------
        UserAlreadyExistsError
            If *username* is already taken.
        """
        logger.info(f"Signup attempt for username: {username}")
        if await self._user_repo.username_exists(username):
            logger.warn(f"Signup failed: username '{username}' already exists")
            raise UserAlreadyExistsError(
                f"Username '{username}' is already taken"
            )

        logger.debug(f"Hashing password for user: {username}")
        hashed = hash_password(password)
        logger.debug(f"Creating user record in database: {username}")
        user = await self._user_repo.create(
            username=username, password_hash=hashed
        )

        logger.info(f"User created successfully: {username} (id: {user.id})")
        token_pair = _build_token_pair(str(user.id))
        logger.debug(f"Tokens generated for new user: {username}")
        return SignupResponse(
            user=UserProfile.model_validate(user),
            tokens=token_pair,
        )

    async def login(self, username: str, password: str) -> LoginResponse:
        """
        Authenticate a user and return a token pair.

        Raises
        ------
        InvalidCredentialsError
            If the credentials are wrong (deliberately vague for security).
        """
        logger.info(f"Login attempt for username: {username}")
        user = await self._user_repo.get_by_username(username)
        
        if user is None:
            logger.warn(f"Login failed: user not found - {username}")
            raise InvalidCredentialsError()
        
        logger.debug(f"Verifying password for user: {username}")
        if not verify_password(password, user.password_hash):
            logger.warn(f"Login failed: invalid password for user - {username}")
            raise InvalidCredentialsError()

        logger.info(f"Login successful for user: {username} (id: {user.id})")
        token_pair = _build_token_pair(str(user.id))
        logger.debug(f"Tokens generated for login user: {username}")
        return LoginResponse(
            user=UserProfile.model_validate(user),
            tokens=token_pair,
        )

    async def refresh_token(self, refresh_token: str) -> RefreshTokenResponse:
        """
        Validate a refresh token and issue a new access token.

        Raises
        ------
        InvalidTokenError
            If the refresh token is invalid or the user no longer exists.
        """
        logger.debug(f"Token refresh attempt with token length: {len(refresh_token)}")
        try:
            user_id = decode_refresh_token(refresh_token)
            logger.debug(f"Refresh token decoded successfully for user_id: {user_id}")
        except JWTError as exc:
            logger.warn(f"Token refresh failed: invalid token - {exc}")
            raise InvalidTokenError(str(exc)) from exc

        logger.debug(f"Looking up user for refresh: {user_id}")
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            logger.warn(f"Token refresh failed: user not found - {user_id}")
            raise InvalidTokenError("User associated with token not found")

        logger.info(f"Token refreshed successfully for user: {user.username} (id: {user_id})")
        new_access_token = create_access_token(str(user.id))
        logger.debug(f"New access token created for user: {user.username}")
        return RefreshTokenResponse(
            access_token=new_access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
