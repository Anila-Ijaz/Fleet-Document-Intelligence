"""Provider-agnostic chat model for the agent service."""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import get_settings


def get_chat_model() -> BaseChatModel:
    s = get_settings()
    if s.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=s.llm_model, api_key=s.openai_api_key, temperature=s.llm_temperature)
    if s.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=s.llm_model, api_key=s.anthropic_api_key, temperature=s.llm_temperature)
    if s.llm_provider == "bedrock":
        from langchain_aws import ChatBedrock

        return ChatBedrock(model_id=s.llm_model, region_name=s.aws_region,
                           model_kwargs={"temperature": s.llm_temperature})
    if s.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=s.llm_model, base_url=s.ollama_base_url, temperature=s.llm_temperature)
    raise ValueError(f"Unsupported LLM provider: {s.llm_provider}")
