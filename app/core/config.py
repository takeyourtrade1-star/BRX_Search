"""
12-Factor config: no hardcoded secrets, fail fast on missing critical env.
SecretStr ensures secrets are never logged in plain text.
"""
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App (non-sensitive, safe defaults)
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "BRX Search"
    APP_NAME: str = "search-engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Debug mode")

    # MySQL — required, no defaults (fail fast)
    MYSQL_HOST: str = Field(..., description="MySQL host")
    MYSQL_PORT: int = Field(default=3306, description="MySQL port")
    MYSQL_USER: str = Field(..., description="MySQL user")
    MYSQL_PASSWORD: SecretStr = Field(..., description="MySQL password")
    MYSQL_DATABASE: str = Field(..., description="MySQL database name")

    # Meilisearch — required, no defaults
    MEILISEARCH_URL: str = Field(..., description="Meilisearch URL (e.g. http://localhost:7700)")
    MEILISEARCH_MASTER_KEY: SecretStr = Field(..., description="Meilisearch master key")
    MEILISEARCH_INDEX_NAME: str = Field(default="cards", description="Meilisearch index name")

    # Indexer (non-sensitive)
    INDEXER_BATCH_SIZE: int = Field(
        default=5000,
        description="Number of documents per batch when indexing",
    )

    # Security — required (no optional bypass)
    SEARCH_ADMIN_API_KEY: SecretStr = Field(
        ...,
        description="API key required for POST /api/admin/reindex (X-Admin-Key header)",
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings; fails at first access if required env vars are missing."""
    return Settings()
