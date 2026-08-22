"""Application configuration loaded from environment variables (.env)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central settings object. Overridable via environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- application ---
    APP_NAME: str = "NeuroOmics-AD"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    # NoDecode keeps comma-separated strings from .env / env vars intact so the
    # field_validator below can split them (pydantic-settings would otherwise
    # try to JSON-decode the value and raise).
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"])

    # --- database ---
    DATABASE_URL: str = "sqlite:///./neuroomics.db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "neuroomics"
    POSTGRES_PASSWORD: str = "neuroomics"
    POSTGRES_DB: str = "neuroomics"

    # --- redis / celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    TASK_ALWAYS_EAGER: bool = False

    # --- storage ---
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_ROOT: str = "./media"
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = "neuroomics"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # --- ML ---
    ML_CACHE_DIR: str = "./.mlcache"
    GNN_HIDDEN_DIM: int = 64
    GNN_EPOCHS: int = 50
    RANDOM_SEED: int = 42

    # --- drug repurposing ---
    DRUG_API_TIMEOUT: int = 10
    DRUG_ENABLE_LIVE_API: bool = False
    DRUG_DATABANK_XML_PATH: str = ""
    # Local signature files (relative paths resolve against the backend/ dir).
    LINCS_SIGNATURES_PATH: str = "data/lincs/compound_signatures.csv"
    CMAP_SIGNATURES_PATH: str = "data/cmap/cmap_signatures.csv"
    CLINICALTRIALS_API_KEY: str = ""

    # --- AI research assistant ---
    ASSISTANT_MODE: Literal["local", "llm"] = "local"
    ASSISTANT_API_BASE: str = "https://api.openai.com/v1"
    ASSISTANT_API_KEY: str = ""
    ASSISTANT_MODEL: str = "gpt-4o-mini"
    ASSISTANT_TEMPERATURE: float = 0.4

    # --- default admin (created on first startup) ---
    ADMIN_EMAIL: str = "admin@neuroomics.org"
    ADMIN_PASSWORD: str = "admin12345"

    # --- plugin system ---
    PLUGINS: Annotated[List[str], NoDecode] = Field(default_factory=list)  # dotted paths of plugin modules to load

    # --- rate limiting / security ---
    MAX_UPLOAD_MB: int = 2048
    BCRYPT_ROUNDS: int = 12

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_ROOT)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @field_validator("CORS_ORIGINS", "PLUGINS", mode="before")
    @classmethod
    def _split_list(cls, v: object) -> object:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
