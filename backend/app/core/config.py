from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TrendSignal API"
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://trendsignal:change-me@localhost:5432/trendsignal"
    )
    naver_api_hub_client_id: str | None = None
    naver_api_hub_client_secret: str | None = None
    naver_api_hub_base_url: str = "https://naverapihub.apigw.ntruss.com"
    collector_request_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

