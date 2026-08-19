"""Tests for REST SSE streaming and structured output formatting."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest
from conftest import FakeChatModel
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from generic_agent.agent import RuntimeEngine
from generic_agent.config.schema import AgentConfig
from generic_agent.domain.context import RuntimeContext
from generic_agent.domain.schemas import GenericAgentResponse
from generic_agent.graphs.direct import DirectStrategy
from generic_agent.interfaces.rest import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    return TestClient(app)


def test_rest_stream_endpoint(client):
    async def fake_events(*args, **kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Hello ")}}
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="world!")}}
        yield {"event": "on_tool_start", "name": "search", "data": {"input": "test query"}}
        yield {"event": "on_tool_end", "data": {"output": "search results"}}
        yield {"event": "on_chain_end", "name": "agent", "data": {}}

    mock_engine = MagicMock()
    mock_engine.use_case_name = "assistant"
    mock_engine.astream_events = fake_events

    with patch("generic_agent.interfaces.rest.get_root_agent", return_value=mock_engine):
        res = client.post("/stream", json={"message": "Stream this"})
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        assert "Hello" in res.text


@pytest.mark.asyncio
async def test_direct_strategy_structured_output():
    fake_model = FakeChatModel(responses=["Structured answer text"])
    rt = RuntimeContext(
        model=fake_model,
        instruction="Assist the user.",
        tools=[],
        description="Structured Agent",
        output_schema=GenericAgentResponse,
    )
    graph = DirectStrategy().build(type("Ctx", (), {"runtime": rt, "extra_config": {}})())
    res = await graph.ainvoke({"messages": [HumanMessage(content="Query")]})
    assert "last_response" in res
    assert isinstance(res["last_response"], dict)
    assert res["last_response"]["answer"] == "Structured answer text"
