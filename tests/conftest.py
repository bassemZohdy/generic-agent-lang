"""Shared test fixtures and test doubles for generic-agent-lang."""

from __future__ import annotations

import os
from typing import Any, List, Optional

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage


class FakeChatModel(FakeListChatModel):
    """Configurable fake chat model for testing state graphs deterministically."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeChatModel":
        return self


@pytest.fixture
def fake_llm():
    return FakeChatModel(responses=["Test response from generic-agent-lang."])


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Set default environment variables for test isolation."""
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DEPLOYMENT_ENV", "local")
    monkeypatch.setenv("AGENT_MODEL", "openai/gpt-4o")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
