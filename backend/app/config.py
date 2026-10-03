"""
Configuration — Pydantic Settings loaded from .env file.
All environment variables have sensible defaults for local development.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


# Determine the backend base directory dynamically
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_file_path = os.path.join(base_dir, ".env")


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str = f"sqlite+aiosqlite:///{os.path.join(base_dir, 'sme_platform.db')}"

    # --- Ollama / Gemma AI Backend ---
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "gemma4:latest"
    OLLAMA_FALLBACK_MODEL: str = "gemma4:e4b"
    OLLAMA_TIMEOUT_SECONDS: float = 180.0
    OLLAMA_TEMPERATURE: float = 0.2

    # Backwards-compatible aliases used by the rest of the backend.
    GEMMA_API_URL: str = "http://127.0.0.1:11434/api/chat"
    GEMMA_MODEL: str = "gemma4:latest"

    # --- App ---
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    UPLOAD_DIR: str = "./uploads"
    SECRET_KEY: str = "super-secret-key-change-in-production"

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure upload directory structure exists at boot
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
