from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
    def _normalise_dsn(cls, v: str) -> str:
        """
        Make a managed provider's connection string usable by asyncpg.

        Providers hand out libpq-style DSNs that the async stack rejects in two
        different ways, both of which fail at startup with opaque errors:

        1. `postgres://` / `postgresql://` — the sync driver. Produces
           "dialect does not support async".
        2. `?sslmode=require` — Render's External Database URL includes this,
           and SQLAlchemy passes it straight through to asyncpg, which doesn't
           take that keyword: "connect() got an unexpected keyword argument
           'sslmode'". The asyncpg dialect spells it `ssl`, and accepts the
           same libpq values, so the parameter is renamed rather than dropped —
           dropping it would silently downgrade a connection meant to be
           encrypted.
        """
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        parts = urlsplit(v)
        if not parts.query:
            return v

        params = parse_qsl(parts.query, keep_blank_values=True)
        if not any(key == "sslmode" for key, _ in params):
            return v

        renamed = [("ssl" if key == "sslmode" else key, val) for key, val in params]
        return urlunsplit(parts._replace(query=urlencode(renamed)))

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
