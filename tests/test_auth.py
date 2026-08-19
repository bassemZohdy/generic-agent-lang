"""Unit tests for authentication, JWT verification, and forward-auth gateway."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from generic_agent.auth.core import (
    authenticate_websocket_token,
    claim_roles,
    decode_token,
    require_roles,
    service_key_claims,
)
from generic_agent.auth.gateway import app as gateway_app


def test_claim_roles_extraction():
    claims = {
        "realm_access": {
            "roles": ["agent-user", "admin"]
        }
    }
    roles = claim_roles(claims)
    assert roles == {"agent-user", "admin"}


def test_require_roles_success():
    claims = {"realm_access": {"roles": ["agent-user"]}}
    require_roles(claims, ("agent-user", "admin"))


def test_require_roles_failure():
    claims = {"realm_access": {"roles": ["guest"]}}
    with pytest.raises(Exception):
        require_roles(claims, ("agent-user",))


def test_service_key_claims():
    claims = service_key_claims()
    assert claims["sub"] == "internal-service"
    assert "realm_access" in claims


def test_gateway_health():
    client = TestClient(gateway_app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_gateway_auth_disabled():
    client = TestClient(gateway_app)
    res = client.get("/auth")
    assert res.status_code == 200
