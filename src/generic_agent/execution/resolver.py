"""Pluggable code-execution sandbox resolution."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Type

from .base import BaseCodeExecutor

logger = logging.getLogger(__name__)

VERTEX_RESOURCE_ENV = "AGENT_CODE_EXECUTION_VERTEX_RESOURCE"
AGENT_ENGINE_RESOURCE_ENV = "AGENT_CODE_EXECUTION_AGENT_ENGINE_RESOURCE"
GKE_KUBECONFIG_PATH_ENV = "AGENT_CODE_EXECUTION_GKE_KUBECONFIG_PATH"
GKE_KUBECONFIG_CONTEXT_ENV = "AGENT_CODE_EXECUTION_GKE_KUBECONFIG_CONTEXT"
STRATEGY_ENV = "AGENT_CODE_EXECUTION_STRATEGY"
DOCKER_HOST_ENV = "AGENT_CODE_EXECUTION_DOCKER_HOST"
DOCKER_IMAGE_ENV = "AGENT_CODE_EXECUTION_DOCKER_IMAGE"
DEFAULT_SANDBOX_IMAGE = "python:3.13-slim"
UNAVAILABLE = "unavailable"

CE_FIELD_ENV_MAP: tuple[tuple[str, str], ...] = (
    ("strategy", "AGENT_CODE_EXECUTION_STRATEGY"),
    ("docker_host", "AGENT_CODE_EXECUTION_DOCKER_HOST"),
    ("docker_image", "AGENT_CODE_EXECUTION_DOCKER_IMAGE"),
    ("vertex_resource", "AGENT_CODE_EXECUTION_VERTEX_RESOURCE"),
    ("agent_engine_resource", "AGENT_CODE_EXECUTION_AGENT_ENGINE_RESOURCE"),
    ("gke_kubeconfig_path", "AGENT_CODE_EXECUTION_GKE_KUBECONFIG_PATH"),
    ("gke_kubeconfig_context", "AGENT_CODE_EXECUTION_GKE_KUBECONFIG_CONTEXT"),
)


class ProviderConfigurationError(Exception):
    """Raised when an explicitly requested strategy cannot be configured."""
    pass


@dataclass(frozen=True)
class CodeExecutionResolution:
    """Resolved code-execution sandbox outcome."""

    executor: Optional[BaseCodeExecutor]
    strategy: str
    detail: str = ""


class _CodeExecutionProviderSpec:
    strategy: str
    warn_on_select: Optional[str] = None

    @classmethod
    def probe(cls, environment: Mapping[str, str], *, model: Any) -> bool:
        raise NotImplementedError

    @classmethod
    def build(cls, environment: Mapping[str, str]) -> BaseCodeExecutor:
        raise NotImplementedError


class DockerContainerCodeExecutionProvider(_CodeExecutionProviderSpec):
    strategy = "docker_container"

    @classmethod
    def _docker_host(cls, environment: Mapping[str, str]) -> Optional[str]:
        return environment.get(DOCKER_HOST_ENV) or environment.get("DOCKER_HOST") or None

    @classmethod
    def probe(cls, environment: Mapping[str, str], *, model: Any) -> bool:
        try:
            import docker
        except ImportError:
            return False
        try:
            host = cls._docker_host(environment)
            client = (
                docker.DockerClient(base_url=host, timeout=1)
                if host
                else docker.from_env(timeout=1)
            )
            return bool(client.ping())
        except Exception:
            return False

    @classmethod
    def build(cls, environment: Mapping[str, str]) -> BaseCodeExecutor:
        from .sandbox import HardenedContainerCodeExecutor

        return HardenedContainerCodeExecutor(
            base_url=cls._docker_host(environment),
            image=environment.get(DOCKER_IMAGE_ENV) or DEFAULT_SANDBOX_IMAGE,
        )


class UnsafeLocalCodeExecutionProvider(_CodeExecutionProviderSpec):
    strategy = "unsafe_local"
    warn_on_select = (
        "unsafe_local code execution selected: model-generated code runs "
        "IN-PROCESS on the host with NO isolation"
    )

    @classmethod
    def probe(cls, environment: Mapping[str, str], *, model: Any) -> bool:
        return True

    @classmethod
    def build(cls, environment: Mapping[str, str]) -> BaseCodeExecutor:
        from .sandbox import UnsafeLocalCodeExecutor

        return UnsafeLocalCodeExecutor()


_PROVIDERS: Dict[str, Type[_CodeExecutionProviderSpec]] = {}
_AUTO_DETECT_ORDER: list[str] = []


def register(spec: Type[_CodeExecutionProviderSpec], *, auto: bool = False) -> None:
    _PROVIDERS[spec.strategy] = spec
    if auto and spec.strategy not in _AUTO_DETECT_ORDER:
        _AUTO_DETECT_ORDER.append(spec.strategy)


register(DockerContainerCodeExecutionProvider, auto=True)
register(UnsafeLocalCodeExecutionProvider, auto=False)


def resolve_code_executor(
    environment: Mapping[str, str], *, model: Any = None
) -> CodeExecutionResolution:
    """Resolve code execution strategy based on environment and probe checks."""
    explicit = (environment.get(STRATEGY_ENV) or "").strip()
    if explicit:
        spec = _PROVIDERS.get(explicit)
        if spec is None:
            known = ", ".join(sorted(_PROVIDERS.keys()))
            raise ProviderConfigurationError(
                f"Unknown code-execution strategy {explicit!r}; known: {known}"
            )
        if not spec.probe(environment, model=model):
            raise ProviderConfigurationError(
                f"Code-execution strategy {explicit!r} is explicitly configured "
                f"but unavailable (probe failed); fix its configuration or unset {STRATEGY_ENV}"
            )
        if spec.warn_on_select:
            logger.warning("%s", spec.warn_on_select)
        return CodeExecutionResolution(
            spec.build(environment), spec.strategy, "explicit override"
        )

    for name in _AUTO_DETECT_ORDER:
        spec = _PROVIDERS[name]
        if spec.probe(environment, model=model):
            return CodeExecutionResolution(
                spec.build(environment), name, "auto-detected"
            )

    logger.info("No code-execution sandbox available; resolving to '%s'", UNAVAILABLE)
    return CodeExecutionResolution(None, UNAVAILABLE, "no provider probe succeeded")
