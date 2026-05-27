"""Agent service configuration. Shares the same Postgres as the other services."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Fleet Document Intelligence - Agent Service"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+psycopg://fleet:fleet@localhost:5432/fleet"
    )

    llm_provider: Literal["openai", "anthropic", "bedrock", "ollama"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    aws_region: str = "eu-central-1"
    ollama_base_url: str = "http://ollama:11434"

    # Business rules for anomaly detection
    high_value_threshold_eur: float = 5000.0
    confidence_review_threshold: float = 0.6


@lru_cache
def get_settings() -> Settings:
    return Settings()
