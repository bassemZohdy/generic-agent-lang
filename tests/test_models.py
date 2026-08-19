"""Unit tests for multi-provider model factory and resolution."""

from __future__ import annotations

import pytest
from langchain_core.language_models import BaseChatModel

from generic_agent.models.factory import resolve_model


def test_resolve_openai_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    model = resolve_model("gpt-4o", provider="openai")
    assert isinstance(model, BaseChatModel)


def test_resolve_prefixed_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    model = resolve_model("openai/gpt-4o")
    assert isinstance(model, BaseChatModel)


def test_resolve_anthropic_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test-key")
    model = resolve_model("claude-3-5-sonnet-latest", provider="anthropic")
    assert isinstance(model, BaseChatModel)


def test_resolve_google_model(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "goog-test-key")
    model = resolve_model("gemini-2.0-flash", provider="google")
    assert isinstance(model, BaseChatModel)


def test_resolve_existing_model_instance():
    from conftest import FakeChatModel

    fake = FakeChatModel(responses=["test"])
    resolved = resolve_model(fake)
    assert resolved is fake
