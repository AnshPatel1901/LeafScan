"""
Unit tests for ImageService — validation, size enforcement, Pillow checks.
Disk I/O is mocked; only the validation logic is exercised.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from PIL import Image

from app.core.exceptions import (
    FileTooLargeError,
    InvalidImageError,
    UnsupportedFileTypeError,
)
from app.services.image_service import ImageService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_upload_file(content_type: str, data: bytes) -> UploadFile:
    """Build a minimal UploadFile-like mock."""
    file = MagicMock(spec=UploadFile)
    file.content_type = content_type

    chunks = [data[i:i+65536] for i in range(0, len(data), 65536)] + [b""]
    file.read = AsyncMock(side_effect=chunks)
    return file


def _make_valid_jpeg_bytes(width: int = 10, height: int = 10) -> bytes:
    """Generate a minimal valid JPEG in memory."""
    img = Image.new("RGB", (width, height), color=(100, 200, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_valid_png_bytes() -> bytes:
    img = Image.new("RGB", (10, 10), color=(50, 100, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Content-type validation ───────────────────────────────────────────────────


class TestContentTypeValidation:
    def test_unsupported_type_raises(self):
        with pytest.raises(UnsupportedFileTypeError):
            ImageService._validate_content_type("image/gif")

    def test_none_content_type_raises(self):
        with pytest.raises(UnsupportedFileTypeError):
            ImageService._validate_content_type(None)

    def test_jpeg_accepted(self):
        # Should not raise
        ImageService._validate_content_type("image/jpeg")

    def test_jpg_accepted(self):
        ImageService._validate_content_type("image/jpg")

    def test_png_accepted(self):
        ImageService._validate_content_type("image/png")

    def test_pdf_rejected(self):
        with pytest.raises(UnsupportedFileTypeError):
            ImageService._validate_content_type("application/pdf")


# ── File size enforcement ─────────────────────────────────────────────────────


class TestFileSizeLimit:
    async def test_oversized_file_raises(self):
        oversized = b"x" * (11 * 1024 * 1024)  # 11 MB > 10 MB limit
        file = _make_upload_file("image/jpeg", oversized)
        with pytest.raises(FileTooLargeError):
            await ImageService._read_with_size_limit(file)

    async def test_exactly_at_limit_accepted(self):
        # 1 byte under the 10 MB limit
        data = b"x" * (10 * 1024 * 1024 - 1)
        file = _make_upload_file("image/jpeg", data)
        result = await ImageService._read_with_size_limit(file)
        assert len(result) == len(data)

    async def test_small_file_accepted(self):
        data = b"x" * 1024
        file = _make_upload_file("image/jpeg", data)
        result = await ImageService._read_with_size_limit(file)
        assert result == data


# ── Image-bytes validation ────────────────────────────────────────────────────


class TestImageBytesValidation:
    def test_valid_jpeg_bytes_accepted(self):
        raw = _make_valid_jpeg_bytes()
        ImageService._validate_image_bytes(raw)  # should not raise

    def test_valid_png_bytes_accepted(self):
        raw = _make_valid_png_bytes()
        ImageService._validate_image_bytes(raw)

    def test_random_bytes_raise(self):
        with pytest.raises(InvalidImageError):
            ImageService._validate_image_bytes(b"this is not an image at all")

    def test_empty_bytes_raise(self):
        with pytest.raises(InvalidImageError):
            ImageService._validate_image_bytes(b"")

    def test_truncated_jpeg_raise(self):
        raw = _make_valid_jpeg_bytes()[:20]  # Cut header short
        with pytest.raises(InvalidImageError):
            ImageService._validate_image_bytes(raw)


# ── validate_and_save integration (mocked disk) ───────────────────────────────


class TestValidateAndSave:
    @patch("app.services.image_service.aiofiles.open")
    async def test_returns_url_and_bytes(self, mock_open):
        # Mock file write
        mock_file = AsyncMock()
        mock_open.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_open.return_value.__aexit__ = AsyncMock(return_value=False)

        raw = _make_valid_jpeg_bytes()
        upload_file = _make_upload_file("image/jpeg", raw)

        svc = ImageService(upload_dir="/tmp/test_uploads")
        url, returned_bytes = await svc.validate_and_save(
            upload_file, user_id="user-123"
        )

        assert url.startswith("user-123/")
        assert url.endswith(".jpg")
        assert returned_bytes == raw

    async def test_wrong_content_type_raises_before_read(self):
        file = _make_upload_file("image/bmp", b"")
        svc = ImageService(upload_dir="/tmp/test_uploads")
        with pytest.raises(UnsupportedFileTypeError):
            await svc.validate_and_save(file, user_id="user-123")
