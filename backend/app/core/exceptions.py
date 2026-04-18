"""
Domain-specific exceptions used across the application.
Each exception maps cleanly to an HTTP status code via the exception handler.
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base class for all application exceptions."""

    status_code: int = 500
    default_message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: Optional[str] = None,
        detail: Optional[Any] = None,
    ) -> None:
        self.message = message or self.default_message
        self.detail = detail
        super().__init__(self.message)


# ── Auth Exceptions ───────────────────────────────────────────────────────────


class AuthenticationError(AppException):
    status_code = 401
    default_message = "Authentication failed"


class InvalidCredentialsError(AuthenticationError):
    default_message = "Invalid username or password"


class InvalidTokenError(AuthenticationError):
    default_message = "Invalid or expired token"


class TokenExpiredError(AuthenticationError):
    default_message = "Token has expired"


# ── User Exceptions ───────────────────────────────────────────────────────────


class UserAlreadyExistsError(AppException):
    status_code = 409
    default_message = "Username already taken"


class UserNotFoundError(AppException):
    status_code = 404
    default_message = "User not found"


# ── Resource Exceptions ───────────────────────────────────────────────────────


class ResourceNotFoundError(AppException):
    status_code = 404
    default_message = "Resource not found"


class PermissionDeniedError(AppException):
    status_code = 403
    default_message = "You do not have permission to access this resource"


# ── Image / Upload Exceptions ─────────────────────────────────────────────────


class InvalidImageError(AppException):
    status_code = 422
    default_message = "Invalid image file"


class FileTooLargeError(AppException):
    status_code = 413
    default_message = "File size exceeds the allowed limit"


class UnsupportedFileTypeError(AppException):
    status_code = 415
    default_message = "Unsupported file type — only JPG and PNG are allowed"


class InvalidRequestError(AppException):
    status_code = 422
    default_message = "Invalid request data"


# ── ML / Prediction Exceptions ────────────────────────────────────────────────


class NotAPlantError(AppException):
    status_code = 422
    default_message = "The uploaded image does not appear to be a plant"


class PredictionError(AppException):
    status_code = 500
    default_message = "Disease prediction failed"


class ModelNotLoadedError(AppException):
    status_code = 503
    default_message = "ML model is not available"


# ── External Service Exceptions ───────────────────────────────────────────────


class ExternalServiceError(AppException):
    status_code = 502
    default_message = "External service call failed"


class GeminiAPIError(ExternalServiceError):
    default_message = "Gemini API call failed"
