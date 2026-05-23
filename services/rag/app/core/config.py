"""RAG service configuration. Shares the same Postgres as the extraction service."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Fleet Document Intelligence - RAG Service"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+psycopg://fleet:fleet@localhost:5432/fleet"
    )

    # LLM (for answer generation)
    llm_provider: Literal["openai", "anthropic", "bedrock", "ollama"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    aws_region: str = "eu-central-1"
    ollama_base_url: str = "http://ollama:11434"

    # Embeddings
    embedding_provider: Literal["openai", "ollama"] = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # Retrieval
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
