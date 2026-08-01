from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

# The local docker-compose password. Harmless in development, but a deployment
# that silently falls back to it would be a real problem, so production refuses
# to start with it. Matching on the credential rather than the whole URL is
# deliberate: the same password ships with several hosts (localhost, db,
# 127.0.0.1), and an exact-URL check would wave those through.
DEV_DB_PASSWORD = "pulse_dev_123"
DEV_DATABASE_URL = f"postgresql+asyncpg://pulse:{DEV_DB_PASSWORD}@localhost:5432/job_market_pulse"


class Settings(BaseSettings):
    app_name: str = "Job Market Pulse"
    environment: str = "development"

    database_url: str = DEV_DATABASE_URL
    redis_url: str = "redis://localhost:6379/0"
    scrape_interval_hours: int = 6

    # Comma-separated list of allowed browser origins for the dashboard.
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Shared secret for POST /pipeline/run. A scrape hits 19 external boards,
    # so leaving it open invites both a self-inflicted DoS and an IP ban from
    # Greenhouse/Lever. Required in production (see _guard_production); left
    # unset in development the endpoint stays open, so the documented
    # quick-start curl keeps working against localhost.
    pipeline_token: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("database_url")
    @classmethod
    def _normalise_driver(cls, v: str) -> str:
        # Managed Postgres add-ons hand out `postgresql://` (or `postgres://`),
        # but the async engine needs an async driver or it fails at startup
        # with an unhelpful "dialect does not support async".
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        if self.is_production:
            if DEV_DB_PASSWORD in self.database_url:
                raise ValueError(
                    "DATABASE_URL still contains the development password. "
                    "Set a real DATABASE_URL before running in production."
                )
            if not self.pipeline_token:
                raise ValueError(
                    "PIPELINE_TOKEN must be set in production so "
                    "POST /pipeline/run isn't publicly triggerable."
                )
        return self

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
