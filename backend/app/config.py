import json
from functools import cached_property, lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str
    jwt_secret: str
    jwt_alg: str = "HS256"
    jwt_expires_min: int = 60
    # Accepts JSON (["a","b"]) or comma-separated ("a,b") from CORS_ORIGINS.
    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    @cached_property
    def cors_origins(self) -> list[str]:
        value = self.cors_origins_raw.strip()
        if not value:
            return []
        if value.startswith("["):
            return json.loads(value)
        return [v.strip() for v in value.split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def sync_database_url(url: str) -> str:
    """Swap the async driver for a sync one (used by Alembic)."""
    return url.replace("mssql+aioodbc://", "mssql+pyodbc://", 1)
