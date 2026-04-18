"""
Auth endpoints — signup, login, refresh-token.
No authentication required for these routes.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    SignupRequest,
    SignupResponse,
)
from app.schemas.response import APIResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


@router.post(
    "/signup",
    response_model=APIResponse[SignupResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def signup(
    body: SignupRequest,
    svc: AuthService = Depends(_get_auth_service),
) -> APIResponse[SignupResponse]:
    result = await svc.signup(username=body.username, password=body.password)
    return APIResponse.ok(result, "Account created successfully")


@router.post(
    "/login",
    response_model=APIResponse[LoginResponse],
    summary="Authenticate and receive token pair",
)
async def login(
    body: LoginRequest,
    svc: AuthService = Depends(_get_auth_service),
) -> APIResponse[LoginResponse]:
    result = await svc.login(username=body.username, password=body.password)
    return APIResponse.ok(result, "Login successful")


@router.post(
    "/refresh-token",
    response_model=APIResponse[RefreshTokenResponse],
    summary="Exchange a refresh token for a new access token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    svc: AuthService = Depends(_get_auth_service),
) -> APIResponse[RefreshTokenResponse]:
    result = await svc.refresh_token(body.refresh_token)
    return APIResponse.ok(result, "Token refreshed successfully")
