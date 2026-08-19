"""Unit tests for WebSocket Live API and MCP interface."""

from __future__ import annotations

import json
from unittest.mock import patch
import pytest
from conftest import FakeChatModel
from fastapi.testclient import TestClient

from generic_agent.agent import RuntimeEngine
from generic_agent.config.schema import AgentConfig
from generic_agent.domain.context import RuntimeContext
from generic_agent.graphs.direct import DirectStrategy
from generic_agent.interfaces.live import app as live_app
from generic_agent.interfaces.mcp import get_service_status
from generic_agent.interfaces.service import app as service_app


def test_live_health():
    client = TestClient(live_app)
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_service_api_status(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    client = TestClient(service_app)
    res = client.get("/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_mcp_get_service_status():
    res = get_service_status()
    data = json.loads(res)
    assert data["status"] == "healthy"
    assert data["framework"] == "langchain+langgraph"


def test_websocket_live_chat(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    fake_model = FakeChatModel(responses=["Live streaming reply"])
    rt = RuntimeContext(
        model=fake_model,
        instruction="Assist the user.",
        tools=[],
        description="Live Test Agent",
    )
    graph = DirectStrategy().build(type("Ctx", (), {"runtime": rt, "extra_config": {}})())
    engine = RuntimeEngine(
        config=AgentConfig(use_case="assistant"),
        runtime=rt,
        graph=graph,
        use_case_name="assistant",
    )

    client = TestClient(live_app)
    with patch("generic_agent.interfaces.live.get_root_agent", return_value=engine):
        with client.websocket_connect("/live?session_id=test_sess") as ws:
            init_msg = ws.receive_json()
            assert init_msg["type"] == "session"

            ws.send_json({"close": True})
