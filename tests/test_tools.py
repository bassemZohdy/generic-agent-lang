"""Unit tests for built-in tools, audit callbacks, and tool registry."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from generic_agent.tools.approval import request_approval
from generic_agent.tools.audit import (
    audit_tool_result,
    is_mutating_tool,
    protect_and_audit_tool,
    tool_name,
)
from generic_agent.tools.knowledge import retrieve_knowledge
from generic_agent.tools.mcp_client import build_mcp_tools
from generic_agent.tools.openapi import build_openapi_tools
from generic_agent.tools.registry import build_tool, inspect_runtime
from generic_agent.tools.search import web_search
from generic_agent.tools.skills import load_skills_from_dir, parse_skill_md


def test_audit_mutating_tool():
    class DummyTool:
        name = "create_database_record"

    assert is_mutating_tool(DummyTool()) is True
    assert is_mutating_tool(retrieve_knowledge) is False
    assert is_mutating_tool(request_approval) is False

    veto = protect_and_audit_tool(DummyTool(), {"table": "users"})
    assert veto is not None
    assert "error" in veto


def test_knowledge_retrieval(tmp_path: Path, monkeypatch):
    knowledge_file = tmp_path / "data.json"
    knowledge_file.write_text(
        json.dumps([
            {"title": "Q3 Financials", "content": "Revenue grew by 25% year-over-year."},
            {"title": "Security Policy", "content": "All credentials must use vault rotation."},
        ]),
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_KNOWLEDGE_FILE", str(knowledge_file))

    result = retrieve_knowledge.invoke("What was the Q3 revenue growth?")
    assert "Revenue grew by 25%" in result
    assert "<untrusted_external_knowledge>" in result


def test_web_search_fallback():
    res = web_search.invoke("What is LangGraph?")
    assert "<untrusted_web_search_results>" in res


def test_request_approval():
    res = request_approval.invoke({"action": "drop table"})
    assert "Approval requested" in res


def test_openapi_tool_builder():
    tools = build_openapi_tools(url="http://localhost:8001", path="/status")
    assert len(tools) == 1
    assert tools[0].name == "api_get_status"


def test_mcp_tool_builder():
    tools = build_mcp_tools()
    assert len(tools) == 1
    assert tools[0].name == "mcp_get_service_status"


def test_skills_loader(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "status_check"
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: status-check
description: Check infrastructure status
---
Instructions: Read node health and report metrics.
""",
        encoding="utf-8",
    )

    tools = load_skills_from_dir(tmp_path / "skills")
    assert len(tools) == 1
    assert "status_check" in tools[0].name
    res = tools[0].invoke({"query": "node-1"})
    assert "<skill_context" in res


def test_inspect_runtime():
    res = inspect_runtime.invoke({})
    parsed = json.loads(res)
    assert "agent" in parsed
    assert "model" in parsed
    assert "enabled_tools" in parsed


def test_build_tool():
    assert build_tool("knowledge") is not None
    assert build_tool("search") is not None
    assert build_tool("approval") is not None
    assert build_tool("code_execution") is None  # silent tool
    assert build_tool("nonexistent_tool") is None
