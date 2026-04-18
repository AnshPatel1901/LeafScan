"""
Image service — file validation, saving to disk, and cleanup.

The save path is deterministic: uploads/<user_id>/<uuid>.<ext>
This makes it easy to swap to S3/GCS later by only changing this service.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Tuple

import aiofiles
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.exceptions import (
    FileTooLargeError,
    InvalidImageError,
    UnsupportedFileTypeError,
)

# Supported content-type → canonical extension
_ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
}

_MAX_BYTES = settings.max_file_size_bytes


class ImageService:
    """Handles image validation and persistence."""

    def __init__(self, upload_dir: str = settings.UPLOAD_DIR) -> None:
        self._upload_dir = Path(upload_dir)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    async def validate_and_save(
        self, file: UploadFile, user_id: str
    ) -> Tuple[str, bytes]:
        """
        Validate *file* and persist it.

        Returns
        -------
        (image_url, raw_bytes)
            *image_url* is the relative path stored in the DB.
            *raw_bytes* is the image content for downstream ML inference.

        Raises
        ------
        UnsupportedFileTypeError, FileTooLargeError, InvalidImageError
        """
        self._validate_content_type(file.content_type)
        raw = await self._read_with_size_limit(file)
        self._validate_image_bytes(raw)

        ext = _ALLOWED_CONTENT_TYPES[file.content_type]
        image_url = await self._persist(raw, user_id, ext)
        return image_url, raw

    async def delete(self, image_url: str) -> None:
        """Remove a stored image file (best-effort, no exception on missing)."""
        path = self._upload_dir / image_url
        if path.exists():
            path.unlink(missing_ok=True)

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _validate_content_type(content_type: str | None) -> None:
        if content_type not in _ALLOWED_CONTENT_TYPES:
            raise UnsupportedFileTypeError(
                f"Content-Type '{content_type}' is not allowed. "
                f"Accepted: {', '.join(_ALLOWED_CONTENT_TYPES)}"
            )

    @staticmethod
    async def _read_with_size_limit(file: UploadFile) -> bytes:
        """Read the upload stream, enforcing the configured size limit."""
        chunks: list[bytes] = []
        total = 0

        while True:
            chunk = await file.read(64 * 1024)  # 64 KB blocks
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_BYTES:
                raise FileTooLargeError(
                    f"File exceeds the {settings.MAX_FILE_SIZE_MB} MB limit"
                )
            chunks.append(chunk)

        return b"".join(chunks)

    @staticmethod
    def _validate_image_bytes(raw: bytes) -> None:
        """Use Pillow to confirm the bytes represent a valid image."""
        try:
            with Image.open(io.BytesIO(raw)) as img:
                img.verify()
        except (UnidentifiedImageError, Exception) as exc:
            raise InvalidImageError(
                f"File is not a valid image: {exc}"
            ) from exc

    async def _persist(self, raw: bytes, user_id: str, ext: str) -> str:
        """Write raw bytes to disk and return the relative URL path."""
        user_dir = self._upload_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4()}.{ext}"
        file_path = user_dir / filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(raw)

        # Relative path stored in DB — portable across environments
        return f"{user_id}/{filename}"
