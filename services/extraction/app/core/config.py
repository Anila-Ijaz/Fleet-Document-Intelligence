"""Application configuration.

All settings are loaded from environment variables (or a .env file in local dev).
This keeps secrets out of code and makes the same image deployable to docker-compose,
kind, and AWS EKS without changes.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Service ---
    app_name: str = "Fleet Document Intelligence - Extraction Service"
    environment: Literal["local", "staging", "production"] = "local"
    log_level: str = "INFO"

    # --- Database ---
    # Example: postgresql+psycopg://fleet:fleet@db:5432/fleet
    database_url: str = Field(
        default="postgresql+psycopg://fleet:fleet@localhost:5432/fleet"
    )

    # --- LLM provider abstraction ---
    # Switch the whole system between providers with one variable.
    llm_provider: Literal["ollama", "openai", "anthropic", "bedrock"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0  # deterministic extraction

    # Ollama
    ollama_base_url: str = "http://ollama:11434"

    # OpenAI
    openai_api_key: str | None = None

    # Anthropic
    anthropic_api_key: str | None = None

    # AWS Bedrock
    aws_region: str = "eu-central-1"  # Frankfurt - relevant for a German employer

    # --- Embeddings (used in Phase 2 RAG) ---
    embedding_provider: Literal["ollama", "openai"] = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536  # text-embedding-3-small dimension


@lru_cache
def get_settings() -> Settings:
    return Settings()
