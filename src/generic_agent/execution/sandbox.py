"""Hardened Docker container and local code executors."""

from __future__ import annotations

import atexit
import contextlib
import io
import logging
import os
import sys
import threading
from typing import Any, Dict, Optional

from .base import BaseCodeExecutor, CodeExecutionResult

logger = logging.getLogger(__name__)

DEFAULT_SANDBOX_IMAGE = "python:3.13-slim"


class HardenedContainerCodeExecutor(BaseCodeExecutor):
    """Secure, resource-limited Docker container code execution engine."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        image: Optional[str] = None,
        timeout_seconds: int = 30,
        mem_limit: str = "512m",
        nano_cpus: int = 1_000_000_000,
        pids_limit: int = 128,
        tmpfs_size: str = "64m",
    ) -> None:
        import docker

        self.image = image or DEFAULT_SANDBOX_IMAGE
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self._client = (
            docker.DockerClient(base_url=base_url)
            if base_url
            else docker.from_env()
        )
        self._hardening: Dict[str, Any] = {
            "mem_limit": mem_limit,
            "nano_cpus": nano_cpus,
            "pids_limit": pids_limit,
            "read_only": True,
            "tmpfs": {"/tmp": f"size={tmpfs_size},rw"},
            "network_disabled": True,
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges"],
        }
        self._container = None
        self._lock = threading.Lock()
        self._start_container()
        atexit.register(self._cleanup_container)

    def _start_container(self) -> None:
        self._container = self._client.containers.run(
            image=self.image,
            command=["tail", "-f", "/dev/null"],
            detach=True,
            tty=True,
            **self._hardening,
        )

    def _cleanup_container(self) -> None:
        if self._container:
            with contextlib.suppress(Exception):
                self._container.stop(timeout=1)
                self._container.remove(force=True)

    def _recover_container(self) -> None:
        """Kill and restart container after a hung execution."""
        if self._container:
            with contextlib.suppress(Exception):
                self._container.kill()
                self._container.remove(force=True)
        self._start_container()

    def execute_code(self, code: str, timeout: Optional[int] = None) -> CodeExecutionResult:
        """Execute code in the container under a strict wall-clock timeout."""
        effective_timeout = timeout or self.timeout_seconds
        result_box: Dict[str, Any] = {}

        def _run():
            try:
                result_box["exec"] = self._container.exec_run(
                    ["python3", "-c", code],
                    demux=True,
                )
            except Exception as err:
                result_box["error"] = err

        with self._lock:
            worker = threading.Thread(target=_run, daemon=True)
            worker.start()
            worker.join(effective_timeout)

            if worker.is_alive():
                logger.warning("Code execution exceeded %ds timeout; restarting sandbox", effective_timeout)
                self._recover_container()
                return CodeExecutionResult(
                    stderr=f"Execution timed out after {effective_timeout}s.",
                    timed_out=True,
                    exit_code=124,
                )

            if "error" in result_box:
                return CodeExecutionResult(
                    stderr=f"Execution failed: {result_box['error']}",
                    exit_code=1,
                )

            exec_res = result_box.get("exec")
            exit_code = getattr(exec_res, "exit_code", 0)
            out = getattr(exec_res, "output", None) or (None, None)
            stdout = out[0].decode("utf-8", "replace") if out[0] else ""
            stderr = out[1].decode("utf-8", "replace") if len(out) > 1 and out[1] else ""
            return CodeExecutionResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


class UnsafeLocalCodeExecutor(BaseCodeExecutor):
    """In-process local Python code executor with redirected stdout/stderr.

    DANGEROUS: Executes untrusted code directly in the host process without isolation.
    Must only be used when explicitly requested.
    """

    def execute_code(self, code: str, timeout: Optional[int] = None) -> CodeExecutionResult:
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        local_scope: Dict[str, Any] = {}
        exit_code = 0
        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            exec(code, {"__builtins__": __builtins__}, local_scope)
        except Exception as e:
            stderr_capture.write(f"Traceback: {type(e).__name__}: {e}\n")
            exit_code = 1
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return CodeExecutionResult(
            stdout=stdout_capture.getvalue(),
            stderr=stderr_capture.getvalue(),
            exit_code=exit_code,
        )
