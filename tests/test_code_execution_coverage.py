"""Tests for HardenedContainerCodeExecutor using fake docker client."""

from __future__ import annotations

import pytest
from fakes import FakeDockerClient, FakeExecResult, install_fake_docker

from generic_agent.execution.sandbox import HardenedContainerCodeExecutor


def test_hardened_container_code_executor_lifecycle(monkeypatch):
    fake_docker = FakeDockerClient()
    fake_docker.exec_handler = lambda cmd: FakeExecResult(0, (b"hello sandbox\n", b""))
    install_fake_docker(monkeypatch, fake_docker)

    executor = HardenedContainerCodeExecutor(image="python:3.13-slim", timeout_seconds=5)
    res = executor.execute_code("print('hello sandbox')")

    assert res.is_success is True
    assert "hello sandbox" in res.stdout
    assert len(fake_docker.run_calls) >= 1
