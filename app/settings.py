"""Application configuration and dependency management.

This module defines a Pydantic `Settings` class for loading configuration
values from environment variables (via a `.env` file) and exposes a
`get_settings` function which can be used as a FastAPI dependency.  The
function uses `lru_cache` so that settings are read only once during the
lifetime of the application.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment and application settings.

    Attributes:
        openai_api_key: API key for OpenAI services.
        db_url: Database connection string.
        regulation_index_path: Path to the JSONL index of regulations.
        evidence_storage_dir: Directory where uploaded evidence files are stored.
    """

    openai_api_key: str | None = None
    db_url: str = "sqlite:///./app.db"
    regulation_index_path: str = "data/regulation_index.jsonl"
    evidence_storage_dir: str = "uploads"
    chroma_persist_directory: str = "./chroma_db"
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket_name: str | None = None
    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of the Settings object.

    Using a cache here ensures that reading environment variables and parsing
    them occurs only once per process, improving performance when the
    dependency is injected frequently.
    """

    return Settings()