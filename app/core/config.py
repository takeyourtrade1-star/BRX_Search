from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "search-engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Debug mode")

    # MySQL (cards database)
    MYSQL_HOST: str = Field(default="localhost", description="MySQL host")
    MYSQL_PORT: int = Field(default=3306, description="MySQL port")
    MYSQL_USER: str = Field(default="root", description="MySQL user")
    MYSQL_PASSWORD: str = Field(default="", description="MySQL password")
    MYSQL_DATABASE: str = Field(default="cards", description="MySQL database name")

    # Meilisearch
    MEILISEARCH_URL: str = Field(
        default="http://localhost:7700",
        description="Meilisearch URL",
    )
    MEILISEARCH_MASTER_KEY: str = Field(
        default="masterKey123",
        description="Meilisearch master key",
    )
    MEILISEARCH_INDEX_NAME: str = Field(
        default="cards",
        description="Meilisearch index name",
    )

    # Indexer
    INDEXER_BATCH_SIZE: int = Field(
        default=5000,
        description="Number of documents per batch when indexing",
    )

    # Admin protection for reindex
    SEARCH_ADMIN_API_KEY: Optional[str] = Field(
        default=None,
        description="API key required for /api/admin/reindex (optional but recommended)",
    )

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
