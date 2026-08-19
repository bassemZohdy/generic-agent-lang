"""Base interfaces and data structures for code execution sandboxes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CodeExecutionResult:
    """Outcome of running code in a sandbox."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and not bool(self.stderr.strip())

    @property
    def output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(f"STDERR:\n{self.stderr}")
        if self.timed_out:
            parts.append("Execution timed out.")
        return "\n".join(parts) if parts else "No output."


class BaseCodeExecutor(ABC):
    """Abstract base class for sandbox code execution engines."""

    @abstractmethod
    def execute_code(self, code: str, timeout: Optional[int] = None) -> CodeExecutionResult:
        """Run code snippet inside the sandbox and return the result."""
        pass
