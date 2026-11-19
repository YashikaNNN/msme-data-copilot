from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime configuration. Secrets come from the environment, never from code."""

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_ROOT / ".env"), str(BACKEND_ROOT.parent / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "BizQuery : MSME Data Copilot"
    database_url: str = "sqlite:///./msme_copilot.db"
    cors_origins: str = "http://localhost:3000"
    storage_dir: str = "storage"
    max_upload_mb: int = 20
    max_rows: int = 100_000
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-001"
    llm_provider: str = "auto"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Accept Render/Heroku postgres:// URLs and use the psycopg driver."""
        url = str(value).strip()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://") and "+psycopg" not in url and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "+psycopg")
        return url

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def sample_dir(self) -> Path:
        return BACKEND_ROOT / "sample_data"


def get_settings() -> Settings:
    return Settings()
