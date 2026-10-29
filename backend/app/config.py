from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_url: str = "mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
    mongodb_database: str = "transaction_ledger"
    app_env: str = "development"
    max_page_size: int = 100
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    currency: str = "INR"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
