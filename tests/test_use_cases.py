"""Unit tests for public use-case catalog and registry resolution."""

from __future__ import annotations

import pytest

from generic_agent.use_cases.registry import get_default_registry


def test_registry_catalog():
    registry = get_default_registry()
    catalog = registry.get_catalog()
    assert len(catalog) >= 8

    use_case_names = {entry["use_case"] for entry in catalog}
    expected = {
        "assistant",
        "pipeline",
        "multi_perspective",
        "refine_until_good",
        "expert_dispatch",
        "team_coordinator",
        "plan_and_execute",
        "approval_gate",
    }
    assert expected.issubset(use_case_names)


def test_alias_resolution():
    registry = get_default_registry()
    canonical, agent = registry.resolve("direct")
    assert canonical == "assistant"

    canonical, agent = registry.resolve("workflow")
    assert canonical == "pipeline"

    canonical, agent = registry.resolve("supervisor")
    assert canonical == "team_coordinator"

    canonical, agent = registry.resolve("gate")
    assert canonical == "approval_gate"


def test_unknown_use_case():
    registry = get_default_registry()
    with pytest.raises(ValueError, match="Unknown use case"):
        registry.resolve("nonexistent_unknown_use_case")
