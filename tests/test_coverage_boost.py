"""Coverage expansion tests for CLI, models, tools, and auth endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest
from click.testing import CliRunner
from conftest import FakeChatModel

from generic_agent.agent import inspect_runtime
from generic_agent.auth.core import (
    authenticate_websocket,
    claim_roles,
    token_from_request,
    websocket_auth_subprotocol,
)
from generic_agent.config.schema import AgentConfig, ExecutionConfig
from generic_agent.interfaces.cli import inspect, main, run
from generic_agent.models.factory import _maybe_warn, resolve_model
from generic_agent.tools.audit import audit_tool_result, is_mutating_tool, protect_and_audit_tool
from generic_agent.tools.openapi import build_openapi_tools
from generic_agent.tools.search import web_search
from generic_agent.tools.skills import parse_skill_md
from generic_agent.util import split_csv


def test_cli_inspect():
    runner = CliRunner()
    result = runner.invoke(inspect)
    assert result.exit_code == 0
    assert "agent" in result.output.lower()


def test_cli_run(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    runner = CliRunner()
    with patch("generic_agent.interfaces.cli.get_root_agent") as mock_root:
        mock_engine = MagicMock()
        mock_engine.use_case_name = "assistant"
        mock_engine.invoke.return_value = {"last_response": "CLI test response"}
        mock_root.return_value = mock_engine

        result = runner.invoke(run, ["What is the status?"])
        assert result.exit_code == 0
        assert "CLI test response" in result.output


def test_models_all_providers(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")

    m_groq = resolve_model("groq/llama-3.3-70b-versatile")
    assert m_groq is not None

    m_mistral = resolve_model("mistral/mistral-large-latest")
    assert m_mistral is not None

    m_ollama = resolve_model("ollama/llama3", base_url="http://localhost:11434")
    assert m_ollama is not None

    m_deepseek = resolve_model("deepseek/deepseek-chat")
    assert m_deepseek is not None


def test_audit_tool_result():
    class DummyTool:
        name = "test_tool"

    audit_tool_result(DummyTool(), {}, {"output": "ok"})
    audit_tool_result(DummyTool(), {}, {"error": "failed"})


def test_openapi_tool_execution(monkeypatch):
    tools = build_openapi_tools(url="http://127.0.0.1:9999", path="/status")
    tool = tools[0]
    res = tool.invoke({})
    assert "Failed to reach service" in res or "Service" in res


def test_skill_parse_plain_text(tmp_path):
    plain_file = tmp_path / "SKILL.md"
    plain_file.write_text("Just plain skill instructions without YAML frontmatter.", encoding="utf-8")
    skill = parse_skill_md(plain_file)
    assert skill.name == tmp_path.name
    assert "plain skill" in skill.instructions


def test_websocket_subprotocol_helper():
    class DummyWS:
        def __init__(self, headers):
            self.headers = headers

    ws_bearer = DummyWS({"sec-websocket-protocol": "bearer.token123"})
    assert websocket_auth_subprotocol(ws_bearer) == "bearer.token123"

    ws_auth_bearer = DummyWS({"sec-websocket-protocol": "authorization.bearer.token456"})
    assert websocket_auth_subprotocol(ws_auth_bearer) == "authorization.bearer.token456"

    ws_none = DummyWS({})
    assert websocket_auth_subprotocol(ws_none) is None


def test_token_from_request_helper():
    class DummyReq:
        def __init__(self, headers):
            self.headers = headers

    req_valid = DummyReq({"authorization": "Bearer valid_jwt_token"})
    assert token_from_request(req_valid) == "valid_jwt_token"

    req_invalid = DummyReq({"authorization": "Basic user:pass"})
    assert token_from_request(req_invalid) is None


def test_config_validation_errors():
    with pytest.raises(ValueError):
        cfg = AgentConfig(use_case="")
        cfg.validate_runtime()

    with pytest.raises(ValueError):
        cfg = AgentConfig(use_case="assistant", execution=ExecutionConfig(max_iterations=0))
        cfg.validate_runtime()
