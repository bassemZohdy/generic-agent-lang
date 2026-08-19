"""Comprehensive unit tests for Keycloak token decoding and authentication flows."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

from generic_agent.auth.core import (
    authenticate_request,
    authenticate_websocket,
    authenticate_websocket_token,
    decode_token,
    keycloak_enabled,
    require_roles,
    service_key_claims,
)


def test_keycloak_enabled_flag(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/basic-agent")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    assert keycloak_enabled() is True

    monkeypatch.setenv("AUTH_DISABLED", "true")
    assert keycloak_enabled() is False


def test_authenticate_request_with_service_key(monkeypatch):
    monkeypatch.setenv("AGENT_SERVICE_API_KEY", "secret-svc-key-999")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/basic-agent")

    class DummyReq:
        headers = {}

    claims = authenticate_request(DummyReq(), api_key="secret-svc-key-999")
    assert claims is not None
    assert claims["sub"] == "internal-service"


def test_authenticate_request_missing_auth(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/basic-agent")

    class DummyReq:
        headers = {}

    with pytest.raises(HTTPException) as exc_info:
        authenticate_request(DummyReq())
    assert exc_info.value.status_code == 401


def test_decode_token_mock_jwks(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/basic-agent")
    monkeypatch.setenv("KEYCLOAK_JWKS_URL", "http://localhost:8080/realms/basic-agent/certs")

    mock_signing_key = MagicMock()
    mock_signing_key.key = "public-key"

    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key

    with patch("generic_agent.auth.core._jwks_client", return_value=mock_jwks):
        with patch("jwt.decode", return_value={"sub": "user-123", "realm_access": {"roles": ["agent-user"]}}):
            claims = decode_token("fake.jwt.token")
            assert claims["sub"] == "user-123"


def test_websocket_auth_token_string(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/basic-agent")

    with patch("generic_agent.auth.core.decode_token", return_value={"sub": "ws-user", "realm_access": {"roles": ["agent-user"]}}):
        claims = authenticate_websocket_token("valid-ws-token")
        assert claims["sub"] == "ws-user"
