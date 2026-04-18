"""
Standardized API response envelope.
Every endpoint wraps its payload in this schema.
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Envelope for all API responses.

    Example::

        {"success": true, "data": {...}, "message": "OK"}
    """

    success: bool
    data: Optional[T] = None
    message: str

    @classmethod
    def ok(cls, data: T, message: str = "Success") -> "APIResponse[T]":
        return cls(success=True, data=data, message=message)

    @classmethod
    def error(cls, message: str, data: Any = None) -> "APIResponse[None]":
        return cls(success=False, data=data, message=message)


class ErrorDetail(BaseModel):
    """Used in the exception handler to return structured error info."""

    success: bool = False
    data: None = None
    message: str
    error_code: Optional[str] = None
