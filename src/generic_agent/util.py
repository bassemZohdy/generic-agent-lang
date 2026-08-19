"""Zero-dependency utility helpers for generic-agent-lang."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_PROD_ENV_PREFIXES = ("prod", "production", "staging", "stage")


def is_production(deployment: str) -> bool:
    """Return True if the deployment environment name denotes production/staging."""
    normalized = deployment.strip().lower()
    return any(normalized.startswith(prefix) for prefix in _PROD_ENV_PREFIXES)


def split_csv(raw: str) -> list[str]:
    """Split a comma-separated string into stripped, non-empty tokens."""
    if not raw:
        return []
    return [token.strip() for token in raw.split(",") if token.strip()]


def substitute_env_vars(value: str) -> str:
    """Substitute environment variables in a string.

    Supports ${VAR_NAME} and ${VAR_NAME:default} syntax.
    """
    if not isinstance(value, str) or "${" not in value:
        return value

    def replace_var(match: re.Match) -> str:
        var_ref = match.group(1)
        if ":" in var_ref:
            var_name, default = var_ref.split(":", 1)
        else:
            var_name, default = var_ref, None

        result = os.getenv(var_name.strip())
        if result is None:
            if default is None:
                logger.warning("Environment variable %s not found and has no default", var_name)
                return match.group(0)
            return default
        return result

    return re.sub(r"\$\{([^}]+)\}", replace_var, value)


def process_substitutions(obj: Any) -> Any:
    """Recursively process environment variable substitutions in nested structures."""
    if isinstance(obj, dict):
        return {k: process_substitutions(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [process_substitutions(item) for item in obj]
    elif isinstance(obj, str):
        return substitute_env_vars(obj)
    return obj


def find_unresolved_substitutions(obj: Any, path: str = "") -> list[str]:
    """Return list of dot-notation paths that still contain unresolved placeholders."""
    if isinstance(obj, dict):
        paths: list[str] = []
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else str(key)
            paths.extend(find_unresolved_substitutions(value, child_path))
        return paths
    if isinstance(obj, list):
        paths = []
        for idx, value in enumerate(obj):
            paths.extend(find_unresolved_substitutions(value, f"{path}[{idx}]"))
        return paths
    if isinstance(obj, str) and "${" in obj:
        return [path]
    return []
