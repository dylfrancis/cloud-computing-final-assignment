from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str
    jwt_secret: str
    jwt_alg: str = "HS256"
    jwt_expires_min: int = 60
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    return Settings()


def sync_database_url(url: str) -> str:
    """Swap the async driver for a sync one (used by Alembic)."""
    return url.replace("mssql+aioodbc://", "mssql+pyodbc://", 1)
