"""Unit tests for configuration loaders, schemas, and environment variable overlays."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from generic_agent.config.loader import (
    apply_env_overrides,
    load_config_from_env,
    load_config_from_yaml,
    resolve_agent_config,
)
from generic_agent.config.schema import AgentConfig, ModelConfig
from generic_agent.config.settings import load_settings, settings
from generic_agent.util import (
    find_unresolved_substitutions,
    is_production,
    process_substitutions,
    split_csv,
    substitute_env_vars,
)


def test_util_helpers():
    assert is_production("production") is True
    assert is_production("prod-us-east") is True
    assert is_production("staging") is True
    assert is_production("local") is False
    assert is_production("docker-compose") is False

    assert split_csv("a, b, c") == ["a", "b", "c"]
    assert split_csv("") == []
    assert split_csv("single") == ["single"]


def test_substitute_env_vars(monkeypatch):
    monkeypatch.setenv("TEST_VAR", "hello_world")
    assert substitute_env_vars("value is ${TEST_VAR}") == "value is hello_world"
    assert substitute_env_vars("value is ${MISSING_VAR:default_val}") == "value is default_val"

    nested = {"a": "${TEST_VAR}", "b": ["${MISSING_VAR:fallback}"]}
    res = process_substitutions(nested)
    assert res == {"a": "hello_world", "b": ["fallback"]}

    unresolved = find_unresolved_substitutions({"a": "${UNRESOLVED_VAR}"})
    assert unresolved == ["a"]


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("AGENT_USE_CASE", "pipeline")
    monkeypatch.setenv("AGENT_MAX_ITERATIONS", "5")
    monkeypatch.setenv("AGENT_SPECIALISTS", "billing,technical")

    config = load_config_from_env()
    assert config.use_case == "pipeline"
    assert config.execution.max_iterations == 5
    assert config.execution.specialists == ["billing", "technical"]


def test_load_config_from_yaml(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MODEL_KEY", "secret-key-123")

    yaml_content = """
agent:
  use_case: expert_dispatch
  name: "support-agent"
  description: "Customer support dispatcher"

model:
  provider: openai
  name: gpt-4o
  api_key: "${MODEL_KEY}"

execution:
  max_iterations: 4
  specialists: [billing, technical]

roles:
  billing:
    instruction: "Handle billing"
  technical:
    instruction: "Handle tech"

tools:
  enabled: [knowledge, search]
"""
    config_file = tmp_path / "agent.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    config = load_config_from_yaml(config_file)
    assert config.use_case == "expert_dispatch"
    assert config.model.api_key == "secret-key-123"
    assert config.execution.max_iterations == 4
    assert config.execution.specialists == ["billing", "technical"]
    assert "billing" in config.roles
    assert "technical" in config.roles


def test_apply_env_overrides(tmp_path: Path, monkeypatch):
    yaml_content = """
agent:
  use_case: assistant
model:
  name: gpt-4o
"""
    config_file = tmp_path / "agent.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")
    loaded = load_config_from_yaml(config_file)

    monkeypatch.setenv("AGENT_USE_CASE", "pipeline")
    monkeypatch.setenv("AGENT_MAX_ITERATIONS", "6")

    overridden = apply_env_overrides(loaded, config_path=str(config_file))
    assert overridden.use_case == "pipeline"
    assert overridden.execution.max_iterations == 6


def test_yaml_unresolved_error(tmp_path: Path):
    yaml_content = """
agent:
  use_case: assistant
model:
  api_key: "${UNRESOLVED_SECRET_KEY}"
"""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError, match="Unresolved environment substitution"):
        load_config_from_yaml(config_file)


def test_settings_validation(monkeypatch):
    monkeypatch.setenv("DEPLOYMENT_ENV", "production")
    monkeypatch.setenv("KEYCLOAK_ISSUER", "")
    monkeypatch.setenv("AUTH_DISABLED", "false")

    with pytest.raises(ValueError, match="KEYCLOAK_ISSUER is required"):
        load_settings()
