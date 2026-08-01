from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Job Market Pulse"
    database_url: str = "postgresql+asyncpg://pulse:pulse_dev_123@localhost:5432/job_market_pulse"
    redis_url: str = "redis://localhost:6379/0"
    scrape_interval_hours: int = 6

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
