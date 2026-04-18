"""
Core configuration — loads from .env via pydantic-settings.
All settings are validated at startup; missing required values raise immediately.
"""

from functools import lru_cache
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Crop Disease Detection API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── File Upload ───────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png,image/jpg"

    # ── ML Models ─────────────────────────────────────────────────────────────
    PLANT_VALIDATOR_MODEL_PATH: str = "models/plant_validator.h5"
    DISEASE_MODEL_PATH: str = "models/disease_model.keras"
    DISEASE_LABEL_MAP_PATH: str = "models/label_map.json"
    CONFIDENCE_THRESHOLD: float = 0.75

    # ── Gemini (Fallback) ─────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_API_URL: str = (
        "https://generativelanguage.googleapis.com/v1beta/models"
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "gemini"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g.:
    #   CORS_ORIGINS=http://localhost:3000,https://leafscan.example.com
    # Leave empty to deny all cross-origin requests (not recommended for dev).
    CORS_ORIGINS: str = "http://localhost:3000"

    # ── TTS (Text-to-Speech) ──────────────────────────────────────────────────
    TTS_ENABLED: bool = False
    TTS_PROVIDER: str = "google"  # Options: "google", "servaai"
    
    # Google Cloud TTS
    GOOGLE_TTS_API_KEY: str = ""
    GOOGLE_TTS_LANGUAGE_CODE: str = "en-US"
    
    # Servaai TTS
    SERVAAI_API_KEY: str = ""
    SERVAAI_VOICE_ID: str = "en-US-Neural2-A"
    
    # TTS Storage
    TTS_STORAGE_DIR: str = "uploads/tts"
    
    # ── Derived / computed ────────────────────────────────────────────────────
    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def allowed_image_types_list(self) -> List[str]:
        return [t.strip() for t in self.ALLOWED_IMAGE_TYPES.split(",")]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters long"
            )
        return v

    @field_validator("CONFIDENCE_THRESHOLD")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("CONFIDENCE_THRESHOLD must be between 0 and 1")
        return v

    @field_validator("TTS_PROVIDER")
    @classmethod
    def validate_tts_provider(cls, v: str) -> str:
        valid_providers = ["google", "servaai"]
        if v not in valid_providers:
            raise ValueError(f"TTS_PROVIDER must be one of {valid_providers}")
        return v

    @model_validator(mode="after")
    def validate_database_url(self) -> "Settings":
        if not self.DATABASE_URL.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton — called once, reused everywhere."""
    return Settings()


settings = get_settings()
