"""Unit tests for code execution sandbox resolution and executors."""

from __future__ import annotations

import pytest

from generic_agent.execution.base import CodeExecutionResult
from generic_agent.execution.resolver import (
    ProviderConfigurationError,
    resolve_code_executor,
)
from generic_agent.execution.sandbox import UnsafeLocalCodeExecutor


def test_code_execution_result():
    res = CodeExecutionResult(stdout="hello\n", stderr="", exit_code=0)
    assert res.is_success is True
    assert "hello" in res.output

    failed = CodeExecutionResult(stdout="", stderr="SyntaxError\n", exit_code=1)
    assert failed.is_success is False
    assert "STDERR:" in failed.output


def test_unsafe_local_code_executor():
    executor = UnsafeLocalCodeExecutor()
    res = executor.execute_code("print(1 + 1)")
    assert res.is_success is True
    assert res.stdout.strip() == "2"

    err_res = executor.execute_code("raise ValueError('boom')")
    assert err_res.is_success is False
    assert "ValueError" in err_res.stderr


def test_resolver_explicit_unsafe_local():
    resolution = resolve_code_executor({"AGENT_CODE_EXECUTION_STRATEGY": "unsafe_local"})
    assert resolution.strategy == "unsafe_local"
    assert isinstance(resolution.executor, UnsafeLocalCodeExecutor)


def test_resolver_unknown_strategy():
    with pytest.raises(ProviderConfigurationError, match="Unknown code-execution strategy"):
        resolve_code_executor({"AGENT_CODE_EXECUTION_STRATEGY": "quantum_computer"})


def test_resolver_fallback_unavailable():
    # In test environment where docker daemon might not be pinged, fallback to unavailable or docker
    resolution = resolve_code_executor({})
    assert resolution.strategy in {"docker_container", "unavailable"}
