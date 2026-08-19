"""Unit and integration tests for the REST API interface."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
import pytest
from conftest import FakeChatModel
from fastapi.testclient import TestClient

from generic_agent.agent import RuntimeEngine
from generic_agent.config.schema import AgentConfig
from generic_agent.domain.context import RuntimeContext
from generic_agent.graphs.direct import DirectStrategy
from generic_agent.interfaces.rest import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    return TestClient(app)


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_info_endpoint(client):
    res = client.get("/info")
    assert res.status_code == 200
    data = res.json()
    assert "agent" in data
    assert "model" in data


def test_invoke_endpoint(client):
    fake_model = FakeChatModel(responses=["Test REST answer"])
    rt = RuntimeContext(
        model=fake_model,
        instruction="Assist the user.",
        tools=[],
        description="REST Test Agent",
    )
    graph = DirectStrategy().build(type("Ctx", (), {"runtime": rt, "extra_config": {}})())
    engine = RuntimeEngine(
        config=AgentConfig(use_case="assistant"),
        runtime=rt,
        graph=graph,
        use_case_name="assistant",
    )

    with patch("generic_agent.interfaces.rest.get_root_agent", return_value=engine):
        res = client.post("/invoke", json={"message": "What is 2+2?"})
        assert res.status_code == 200
        data = res.json()
        assert "response" in data
        assert data["response"] == "Test REST answer"
        assert data["use_case"] == "assistant"
