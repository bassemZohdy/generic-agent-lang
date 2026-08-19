"""Multi-provider chat model resolution using LangChain model connectors."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Union

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

#: Environment-variable hints per provider for warnings
PROVIDER_ENV_HINTS: Dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "ollama": "OLLAMA_API_BASE",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "mistralai": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "together_ai": "TOGETHERAI_API_KEY",
    "azure": "AZURE_OPENAI_API_KEY",
}

_warned: set[str] = set()


def _maybe_warn(provider: str, api_key: Optional[str]) -> None:
    """Log a one-time warning if a provider's recommended env var is missing."""
    env_var = PROVIDER_ENV_HINTS.get(provider.lower())
    if (
        env_var
        and api_key is None
        and os.environ.get(env_var) is None
        and provider not in _warned
    ):
        _warned.add(provider)
        logger.warning("Provider %r usually requires %s; it is not set", provider, env_var)


def resolve_model(
    name: str,
    *,
    provider: str = "openai",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    streaming: bool = True,
    model_kwargs: Optional[Dict[str, Any]] = None,
) -> BaseChatModel:
    """Resolve a model name to a configured LangChain BaseChatModel instance.

    Rules:
    - If ``name`` contains "/", the prefix is parsed as the provider (e.g. "openai/gpt-4o", "anthropic/claude-3-5-sonnet").
    - Supports OpenAI, Anthropic, Google (Gemini), Groq, Mistral, Ollama, DeepSeek, and generic OpenAI-compatible gateways.
    - If an explicit BaseChatModel instance is passed, it is returned directly.

    Args:
        name: Model name, e.g. "gpt-4o" or "openai/gpt-4o".
        provider: Provider name if not prefixed in ``name``.
        api_key: Optional API key override.
        base_url: Optional base URL override (e.g. for vLLM, Ollama, local proxy).
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in response.
        streaming: Whether to enable token streaming.
        model_kwargs: Extra provider-specific keyword arguments.

    Returns:
        Configured BaseChatModel instance.
    """
    if isinstance(name, BaseChatModel):
        return name

    name_str = str(name).strip()
    resolved_provider = provider.lower()
    model_name = name_str

    if "/" in name_str:
        resolved_provider, model_name = name_str.split("/", 1)
        resolved_provider = resolved_provider.lower()

    _maybe_warn(resolved_provider, api_key)

    common_kwargs: Dict[str, Any] = {
        "model": model_name,
        "streaming": streaming,
    }
    if temperature is not None:
        common_kwargs["temperature"] = temperature
    if max_tokens is not None:
        common_kwargs["max_tokens"] = max_tokens
    if model_kwargs:
        common_kwargs.update(model_kwargs)

    # 1. OpenAI / OpenAI Compatible
    if resolved_provider in {"openai", "azure_openai", "deepseek"}:
        try:
            from langchain_openai import ChatOpenAI

            kwargs = {**common_kwargs}
            if api_key:
                kwargs["api_key"] = api_key
            elif resolved_provider == "deepseek" and os.environ.get("DEEPSEEK_API_KEY"):
                kwargs["api_key"] = os.environ.get("DEEPSEEK_API_KEY")
                if not base_url:
                    base_url = "https://api.deepseek.com"

            if base_url:
                kwargs["base_url"] = base_url

            return ChatOpenAI(**kwargs)
        except ImportError:
            logger.warning("langchain-openai not installed; falling back")

    # 2. Anthropic
    if resolved_provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic

            kwargs = {**common_kwargs}
            kwargs["model_name"] = model_name
            kwargs.pop("model", None)
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["anthropic_api_url"] = base_url
            return ChatAnthropic(**kwargs)
        except ImportError:
            logger.warning("langchain-anthropic not installed; falling back")

    # 3. Google GenAI / Gemini
    if resolved_provider in {"google", "gemini", "google_genai"}:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            kwargs = {**common_kwargs}
            kwargs["model"] = model_name
            if api_key:
                kwargs["google_api_key"] = api_key
            return ChatGoogleGenerativeAI(**kwargs)
        except ImportError:
            logger.warning("langchain-google-genai not installed; falling back")

    # 4. Ollama
    if resolved_provider == "ollama":
        try:
            from langchain_ollama import ChatOllama

            kwargs = {**common_kwargs}
            if base_url:
                kwargs["base_url"] = base_url
            elif os.environ.get("OLLAMA_API_BASE"):
                kwargs["base_url"] = os.environ.get("OLLAMA_API_BASE")
            return ChatOllama(**kwargs)
        except ImportError:
            logger.warning("langchain-ollama not installed; falling back")

    # 5. Groq
    if resolved_provider == "groq":
        try:
            from langchain_groq import ChatGroq

            kwargs = {**common_kwargs}
            if api_key:
                kwargs["api_key"] = api_key
            return ChatGroq(**kwargs)
        except ImportError:
            logger.warning("langchain-groq not installed; falling back")

    # 6. Mistral AI
    if resolved_provider in {"mistral", "mistralai"}:
        try:
            from langchain_mistralai import ChatMistralAI

            kwargs = {**common_kwargs}
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["endpoint"] = base_url
            return ChatMistralAI(**kwargs)
        except ImportError:
            logger.warning("langchain-mistralai not installed; falling back")

    # 7. Unified fallback via init_chat_model or ChatOpenAI
    try:
        from langchain.chat_models import init_chat_model

        kwargs = {**common_kwargs}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        return init_chat_model(model_name, model_provider=resolved_provider, **kwargs)
    except Exception as err:
        logger.warning(
            "init_chat_model could not initialize %s/%s: %s; falling back to ChatOpenAI",
            resolved_provider,
            model_name,
            err,
        )

    # Generic OpenAI fallback for gateways
    try:
        from langchain_openai import ChatOpenAI

        kwargs = {**common_kwargs}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)
    except Exception:
        # Ultimate fallback: FakeListChatModel (useful in test environments)
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        logger.warning("Using FakeListChatModel fallback for %s/%s", resolved_provider, model_name)
        return FakeListChatModel(responses=["Hello! I am generic-agent-lang."])
