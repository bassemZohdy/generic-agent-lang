"""Load and validate externalized agent configurations from YAML and environment."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Tuple

import yaml

from ..util import (
    find_unresolved_substitutions,
    process_substitutions,
    split_csv,
)
from .schema import (
    AgentConfig,
    ExecutionCodeExecutionConfig,
    ExecutionConfig,
    InstructionsConfig,
    ModelConfig,
    OutputConfig,
    RoleConfig,
    StateConfig,
    ToolsConfig,
    ToolsMcpConfig,
    ToolsOpenApiConfig,
    ToolsSkillsConfig,
)
from .settings import settings

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = "/app/config/agent.yaml"


def _resolve_use_case_key(raw: str) -> str:
    """Resolve a use-case key to its canonical form."""
    from ..use_cases.registry import get_default_registry

    registry = get_default_registry()
    if registry.has(raw):
        canonical, _ = registry.resolve(raw)
        return canonical
    return raw.strip().lower()


def _env_positive_int(raw: str, name: str) -> int:
    try:
        val = int(raw.strip())
    except ValueError as err:
        raise ValueError(f"{name} must be an integer >= 1; got {raw!r}") from err
    if val < 1:
        raise ValueError(f"{name} must be an integer >= 1; got {val}")
    return val


def load_config_from_yaml(path: str | Path) -> AgentConfig:
    """Load agent configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Parsed and validated AgentConfig.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If YAML is invalid or contains unresolved substitutions.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    logger.info("Loading configuration from %s", path)

    try:
        raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(raw_data, dict):
        raise ValueError(f"Configuration must be a YAML object, not {type(raw_data).__name__}")

    # Apply environment variable substitutions
    raw_data = process_substitutions(raw_data)
    unresolved = find_unresolved_substitutions(raw_data)
    if unresolved:
        raise ValueError(
            "Unresolved environment substitution(s) in YAML: " + ", ".join(unresolved)
        )

    config = _parse_dict_to_config(raw_data)
    config.validate_runtime()
    logger.info("Configuration loaded: use_case=%s", config.use_case)
    return config


def load_config_from_env() -> AgentConfig:
    """Load agent configuration entirely from environment variables.

    Returns:
        AgentConfig populated from environment and settings defaults.
    """
    use_case_raw = (
        os.environ.get("AGENT_USE_CASE")
        or os.environ.get("USE_CASE")
        or "assistant"
    ).strip()
    use_case = _resolve_use_case_key(use_case_raw)

    max_iterations_raw = os.environ.get("AGENT_MAX_ITERATIONS")
    max_iterations = (
        _env_positive_int(max_iterations_raw, "AGENT_MAX_ITERATIONS")
        if max_iterations_raw
        else settings.max_iterations
    )

    specialists_raw = os.environ.get("AGENT_SPECIALISTS")
    specialists = (
        split_csv(specialists_raw)
        if specialists_raw
        else list(settings.specialists)
    )

    model_str = settings.model
    provider = "openai"
    model_name = model_str
    if "/" in model_str:
        provider, model_name = model_str.split("/", 1)

    config = AgentConfig(
        use_case=use_case,
        name=settings.app_name,
        description=settings.agent_description,
        model=ModelConfig(
            provider=provider,
            name=model_name,
        ),
        instructions=InstructionsConfig(value=settings.agent_instruction),
        tools=ToolsConfig(
            enabled=list(settings.enabled_tools),
            mcp=ToolsMcpConfig(
                enabled=settings.enable_mcp,
                tools=list(settings.mcp_tools),
                prefix=settings.mcp_tool_prefix,
            ),
            openapi=ToolsOpenApiConfig(
                enabled=settings.enable_openapi,
                url=settings.openapi_url,
                path=settings.openapi_path,
                title=settings.openapi_title,
                prefix=settings.openapi_tool_prefix,
            ),
            skills=ToolsSkillsConfig(
                enabled=settings.enable_skills,
                dir=settings.skills_dir,
                prefix=settings.skills_tool_prefix,
            ),
        ),
        execution=ExecutionConfig(
            max_iterations=max_iterations,
            specialists=specialists,
            code_execution=ExecutionCodeExecutionConfig(
                strategy=settings.code_execution_strategy,
                docker_host=settings.code_execution_docker_host,
                docker_image=settings.code_execution_docker_image,
                vertex_resource=settings.code_execution_vertex_resource,
                agent_engine_resource=settings.code_execution_agent_engine_resource,
                gke_kubeconfig_path=settings.code_execution_gke_kubeconfig_path,
                gke_kubeconfig_context=settings.code_execution_gke_kubeconfig_context,
            ),
        ),
        output=OutputConfig(
            schema="GenericAgentResponse" if settings.enable_structured_output else None,
            key="last_response",
        ),
        state=StateConfig(enabled=True),
    )

    config.validate_runtime()
    return config


def log_config_provenance(
    config_path: Optional[str],
    overridden_keys: List[str] | Tuple[str, ...],
    resolved_use_case: str,
) -> None:
    """Log one-line provenance summary."""
    logger.info(
        "config: yaml=%s, use_case=%s, env overrides: %s",
        config_path or "none",
        resolved_use_case,
        ", ".join(overridden_keys) if overridden_keys else "none",
    )


def apply_env_overrides(
    config: AgentConfig, *, config_path: Optional[str] = None
) -> AgentConfig:
    """Apply environment variables onto a YAML-loaded config.

    Explicitly set, non-empty values in the environment override YAML values.
    """
    overridden: list[str] = []
    data = config.model_dump()

    use_case_raw = os.environ.get("AGENT_USE_CASE")
    if use_case_raw and use_case_raw.strip():
        data["use_case"] = _resolve_use_case_key(use_case_raw)
        overridden.append("AGENT_USE_CASE")

    model_name = (
        os.environ.get("AGENT_MODEL")
        or os.environ.get("LANGCHAIN_MODEL")
        or os.environ.get("ADK_MODEL")
    )
    if model_name and model_name.strip():
        m_raw = model_name.strip()
        if "/" in m_raw:
            provider, name = m_raw.split("/", 1)
        else:
            provider = (data.get("model") or {}).get("provider", "openai")
            name = m_raw
        data["model"] = {
            **(data.get("model") or {}),
            "provider": provider,
            "name": name,
        }
        overridden.append("AGENT_MODEL" if os.environ.get("AGENT_MODEL") else "ADK_MODEL")

    instruction = os.environ.get("AGENT_INSTRUCTION")
    if instruction and instruction.strip():
        data["instructions"] = {
            **(data.get("instructions") or {}),
            "value": instruction.strip(),
        }
        overridden.append("AGENT_INSTRUCTION")

    tool_names = os.environ.get("AGENT_TOOLS")
    if tool_names and tool_names.strip():
        data["tools"] = {
            **(data.get("tools") or {}),
            "enabled": split_csv(tool_names),
        }
        overridden.append("AGENT_TOOLS")

    max_iterations_raw = os.environ.get("AGENT_MAX_ITERATIONS")
    if max_iterations_raw and max_iterations_raw.strip():
        data["execution"] = {
            **(data.get("execution") or {}),
            "max_iterations": _env_positive_int(max_iterations_raw, "AGENT_MAX_ITERATIONS"),
        }
        overridden.append("AGENT_MAX_ITERATIONS")

    specialists_raw = os.environ.get("AGENT_SPECIALISTS")
    if specialists_raw and specialists_raw.strip():
        names = split_csv(specialists_raw)
        roles = data.get("roles") or {}
        if roles and not set(names).issubset(roles.keys()):
            unknown = sorted(set(names) - set(roles.keys()))
            raise ValueError(
                f"AGENT_SPECIALISTS contains unknown role(s) {unknown}; "
                f"available roles: {sorted(roles.keys())}"
            )
        data["execution"] = {
            **(data.get("execution") or {}),
            "specialists": names,
        }
        overridden.append("AGENT_SPECIALISTS")

    updated = AgentConfig.model_validate(data)
    updated.validate_runtime()
    log_config_provenance(config_path, overridden, updated.use_case)
    return updated


def _parse_dict_to_config(data: dict) -> AgentConfig:
    """Map raw YAML dictionary structure into AgentConfig."""
    agent_data = data.get("agent", {})
    if not isinstance(agent_data, dict):
        raise ValueError("agent must be a mapping")

    use_case_raw = str(agent_data.get("use_case") or "").strip()
    if not use_case_raw:
        raise ValueError("agent.use_case is required")
    use_case = _resolve_use_case_key(use_case_raw)

    model_data = data.get("model", {})
    model_config = None
    if model_data:
        provider = model_data.get("provider", "openai")
        name = model_data.get("name", "")
        if "/" in name and provider in {"openai", "google", "default"}:
            provider, name = name.split("/", 1)
        model_config = ModelConfig(
            provider=provider,
            name=name,
            api_key=model_data.get("api_key"),
            base_url=model_data.get("base_url"),
            temperature=model_data.get("temperature"),
            max_tokens=model_data.get("max_tokens"),
            streaming=model_data.get("streaming", True),
            model_kwargs=model_data.get("model_kwargs", {}),
        )

    instructions_data = data.get("instructions", {})
    instructions_config = None
    if instructions_data:
        instructions_config = InstructionsConfig(
            value=instructions_data.get("value", ""),
            file=instructions_data.get("file"),
        )

    tools_data = data.get("tools", {})
    tools_config = None
    if tools_data:
        mcp_data = tools_data.get("mcp")
        mcp_config = None
        if mcp_data:
            mcp_config = ToolsMcpConfig(
                enabled=mcp_data.get("enabled", False),
                tools=mcp_data.get("tools", []),
                prefix=mcp_data.get("prefix", "mcp_"),
                server_path=mcp_data.get("server_path"),
            )

        openapi_data = tools_data.get("openapi")
        openapi_config = None
        if openapi_data:
            openapi_config = ToolsOpenApiConfig(
                enabled=openapi_data.get("enabled", False),
                url=openapi_data.get("url", ""),
                path=openapi_data.get("path", "/status"),
                title=openapi_data.get("title", "Service API"),
                prefix=openapi_data.get("prefix", "api_"),
            )

        skills_data = tools_data.get("skills")
        skills_config = None
        if skills_data:
            skills_config = ToolsSkillsConfig(
                enabled=skills_data.get("enabled", False),
                dir=skills_data.get("dir", ""),
                prefix=skills_data.get("prefix", ""),
            )

        tools_config = ToolsConfig(
            enabled=tools_data.get("enabled", []),
            mcp=mcp_config,
            openapi=openapi_config,
            skills=skills_config,
        )

    execution_data = data.get("execution", {})
    execution_config = None
    if execution_data:
        ce_data = execution_data.get("code_execution")
        ce_config = None
        if ce_data:
            ce_config = ExecutionCodeExecutionConfig(
                strategy=ce_data.get("strategy", ""),
                docker_host=ce_data.get("docker_host", ""),
                docker_image=ce_data.get("docker_image", ""),
                vertex_resource=ce_data.get("vertex_resource", ""),
                agent_engine_resource=ce_data.get("agent_engine_resource", ""),
                gke_kubeconfig_path=ce_data.get("gke_kubeconfig_path", ""),
                gke_kubeconfig_context=ce_data.get("gke_kubeconfig_context", ""),
            )

        execution_config = ExecutionConfig(
            max_iterations=execution_data.get("max_iterations", 3),
            require_approval=execution_data.get("require_approval", False),
            steps=execution_data.get("steps"),
            workers=execution_data.get("workers"),
            specialists=execution_data.get("specialists", []),
            code_execution=ce_config,
        )

    output_data = data.get("output", {})
    output_config = None
    if output_data:
        output_config = OutputConfig(
            schema=output_data.get("schema"),
            key=output_data.get("key", "last_response"),
        )

    state_data = data.get("state", {})
    state_config = None
    if state_data:
        state_config = StateConfig(
            enabled=state_data.get("enabled", True),
            checkpointer=state_data.get("checkpointer", "memory"),
        )

    roles_data = data.get("roles") or {}
    roles = {
        str(name): RoleConfig(
            instruction=role.get("instruction"),
            model=role.get("model"),
            tools=role.get("tools"),
        )
        for name, role in roles_data.items()
        if isinstance(role, dict)
    }

    return AgentConfig(
        use_case=use_case,
        name=agent_data.get("name", ""),
        description=agent_data.get("description", ""),
        model=model_config,
        instructions=instructions_config,
        tools=tools_config,
        execution=execution_config,
        output=output_config,
        state=state_config,
        roles=roles,
    )


def active_config_path() -> Optional[str]:
    """Return configured YAML config path, or None for env mode."""
    path = os.environ.get("AGENT_CONFIG_FILE")
    if path:
        return path
    return DEFAULT_CONFIG_FILE if os.path.exists(DEFAULT_CONFIG_FILE) else None


def resolve_agent_config() -> AgentConfig:
    """Resolve runtime config: YAML file when available, else env only."""
    path = active_config_path()
    if path is not None:
        return apply_env_overrides(load_config_from_yaml(path), config_path=path)
    config = load_config_from_env()
    log_config_provenance(None, (), config.use_case)
    return config
