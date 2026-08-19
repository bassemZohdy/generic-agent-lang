"""End-to-end integration tests for multi-use-case agent execution."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from conftest import FakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

from generic_agent.agent import build_root_agent
from generic_agent.config.loader import load_config_from_yaml
from generic_agent.config.schema import AgentConfig, ExecutionConfig, ModelConfig, ToolsConfig


@pytest.mark.asyncio
async def test_end_to_end_pipeline_use_case(monkeypatch, tmp_path: Path):
    yaml_config = """
agent:
  use_case: pipeline
  name: "e2e-pipeline"
model:
  name: gpt-4o
execution:
  steps: 3
"""
    cfg_file = tmp_path / "agent.yaml"
    cfg_file.write_text(yaml_config, encoding="utf-8")
    monkeypatch.setenv("AGENT_CONFIG_FILE", str(cfg_file))
    monkeypatch.setenv("AUTH_DISABLED", "true")

    engine = build_root_agent()
    assert engine.use_case_name == "pipeline"


@pytest.mark.asyncio
async def test_end_to_end_expert_dispatch(monkeypatch, tmp_path: Path):
    yaml_config = """
agent:
  use_case: expert_dispatch
  name: "e2e-dispatcher"
model:
  name: gpt-4o
execution:
  specialists: [billing, technical]
roles:
  billing:
    instruction: "Billing specialist"
  technical:
    instruction: "Technical specialist"
"""
    cfg_file = tmp_path / "agent.yaml"
    cfg_file.write_text(yaml_config, encoding="utf-8")
    monkeypatch.setenv("AGENT_CONFIG_FILE", str(cfg_file))
    monkeypatch.setenv("AUTH_DISABLED", "true")

    engine = build_root_agent()
    assert engine.use_case_name == "expert_dispatch"


@pytest.mark.asyncio
async def test_end_to_end_approval_gate(monkeypatch, tmp_path: Path):
    yaml_config = """
agent:
  use_case: approval_gate
  name: "e2e-gate"
model:
  name: gpt-4o
execution:
  require_approval: true
"""
    cfg_file = tmp_path / "agent.yaml"
    cfg_file.write_text(yaml_config, encoding="utf-8")
    monkeypatch.setenv("AGENT_CONFIG_FILE", str(cfg_file))
    monkeypatch.setenv("AUTH_DISABLED", "true")

    engine = build_root_agent()
    assert engine.use_case_name == "approval_gate"
