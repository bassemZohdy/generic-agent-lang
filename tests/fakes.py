"""Shared test doubles and fakes for generic-agent-lang."""

from __future__ import annotations

import sys
import types
from typing import Callable, Optional


class FakeExecResult:
    def __init__(self, exit_code: int = 0, output=(b"", b"")):
        self.exit_code = exit_code
        self.output = output


class FakeContainer:
    def __init__(self, client: "FakeDockerClient"):
        self._client = client
        self.id = f"fake-container-{len(client.run_calls)}"

    def exec_run(self, cmd, demux=False):
        if self._client.exec_handler:
            return self._client.exec_handler(cmd)
        return FakeExecResult(0, (b"container-output\n", b""))

    def stop(self, timeout=None):
        self._client.stop_calls.append(self.id)

    def kill(self):
        self._client.kill_calls.append(self.id)

    def remove(self, force=False):
        self._client.remove_calls.append(self.id)


class FakeDockerClient:
    def __init__(self):
        self.run_calls: list[dict] = []
        self.stop_calls: list[str] = []
        self.kill_calls: list[str] = []
        self.remove_calls: list[str] = []
        self.ping_raises: Optional[Exception] = None
        self.exec_handler: Optional[Callable] = None

    def ping(self) -> bool:
        if self.ping_raises:
            raise self.ping_raises
        return True

    @property
    def containers(self):
        client = self

        class _Containers:
            def run(self, **kwargs):
                client.run_calls.append(kwargs)
                return FakeContainer(client)

        return _Containers()


def install_fake_docker(monkeypatch, client: FakeDockerClient) -> types.ModuleType:
    docker_mod = types.ModuleType("docker")
    client_mod = types.ModuleType("docker.client")

    def _constructor(**kwargs):
        return client

    docker_mod.DockerClient = _constructor
    docker_mod.from_env = _constructor
    client_mod.DockerClient = _constructor

    for name, mod in (("docker", docker_mod), ("docker.client", client_mod)):
        monkeypatch.setitem(sys.modules, name, mod)
    return docker_mod
