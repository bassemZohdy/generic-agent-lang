"""Keycloak OIDC bearer-token validation and authorization helpers."""

from __future__ import annotations

import logging
import os
import secrets
from typing import Any, Dict, Optional, Set, Tuple

import jwt
from fastapi import HTTPException, Request, WebSocket
from jwt import PyJWKClient

from ..config.settings import settings

logger = logging.getLogger(__name__)

_jwks_clients: Dict[str, PyJWKClient] = {}


def is_auth_disabled() -> bool:
    """Check if authentication is disabled (respecting dynamic environment override)."""
    env_val = os.environ.get("AUTH_DISABLED", "").strip().lower()
    if env_val in {"true", "1", "yes"}:
        return True
    if env_val in {"false", "0", "no"}:
        return False
    return settings.auth_disabled


def keycloak_enabled() -> bool:
    """Return whether Keycloak OIDC bearer-token validation is active."""
    issuer = os.environ.get("KEYCLOAK_ISSUER", settings.keycloak_issuer).strip()
    return bool(issuer and not is_auth_disabled())


def _authentication_required() -> None:
    if is_auth_disabled():
        return
    issuer = os.environ.get("KEYCLOAK_ISSUER", settings.keycloak_issuer).strip()
    if not issuer:
        raise HTTPException(
            status_code=503,
            detail=(
                "Keycloak authentication is not configured; set KEYCLOAK_ISSUER "
                "or explicitly set AUTH_DISABLED=true"
            ),
        )


def _jwks_client(url: str) -> PyJWKClient:
    """Return cached JWKS client with configured timeout."""
    client = _jwks_clients.get(url)
    if client is None:
        client = PyJWKClient(
            url,
            cache_keys=True,
            cache_jwk_set=True,
            lifespan=300,
            timeout=settings.keycloak_jwks_timeout,
        )
        _jwks_clients[url] = client
    return client


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a Keycloak JWT bearer token."""
    issuer = os.environ.get("KEYCLOAK_ISSUER", settings.keycloak_issuer).strip()
    if not issuer:
        raise HTTPException(status_code=503, detail="Keycloak authentication is not configured")
    jwks_url = os.environ.get("KEYCLOAK_JWKS_URL", settings.keycloak_jwks_url).strip()
    if not jwks_url:
        jwks_url = f"{issuer.rstrip('/')}/protocol/openid-connect/certs"

    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=settings.keycloak_audience,
            options={"verify_aud": bool(settings.keycloak_audience)},
        )
        if not claims.get("sub"):
            raise jwt.InvalidTokenError("Token subject is required")
        return claims
    except (jwt.PyJWTError, ValueError, OSError) as err:
        raise HTTPException(status_code=401, detail="Invalid Keycloak access token") from err


def token_from_request(request: Request) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    return token.strip() if scheme.lower() == "bearer" and token.strip() else None


def claim_roles(claims: Dict[str, Any]) -> Set[str]:
    """Extract role set from configured JWT role claim path."""
    value: Any = claims
    for part in settings.keycloak_role_claim.split("."):
        value = value.get(part, {}) if isinstance(value, dict) else {}
    return set(value) if isinstance(value, list) else set()


def require_roles(claims: Dict[str, Any], required_roles: Tuple[str, ...]) -> None:
    """Verify that claims contain at least one of the required roles."""
    if required_roles and not set(required_roles).intersection(claim_roles(claims)):
        raise HTTPException(status_code=403, detail="Required Keycloak role is missing")


def service_key_claims() -> Dict[str, Any]:
    """Generate claims structure for internal service-key authentication."""
    claims: Dict[str, Any] = {
        "sub": "internal-service",
        "auth_method": "api_key",
    }
    value: Dict[str, Any] = claims
    parts = settings.keycloak_role_claim.split(".")
    for part in parts[:-1]:
        child: Dict[str, Any] = {}
        value[part] = child
        value = child
    value[parts[-1]] = list(settings.service_api_roles)
    return claims


def authenticate_request(
    request: Request,
    *,
    api_key: Optional[str] = None,
    required_roles: Tuple[str, ...] = (),
) -> Optional[Dict[str, Any]]:
    """Authenticate incoming HTTP request via Bearer token or service API key."""
    _authentication_required()
    if is_auth_disabled():
        return None

    token = token_from_request(request)
    if token:
        claims = decode_token(token)
        require_roles(claims, required_roles)
        return claims

    svc_key = os.environ.get("AGENT_SERVICE_API_KEY", settings.service_api_key)
    if (
        svc_key
        and api_key
        and secrets.compare_digest(api_key, svc_key)
    ):
        claims = service_key_claims()
        require_roles(claims, required_roles)
        return claims

    raise HTTPException(status_code=401, detail="Bearer token or valid service API key required")


def websocket_auth_subprotocol(websocket: WebSocket) -> Optional[str]:
    """Extract offered auth subprotocol (e.g. bearer.<token> or authorization.bearer.<token>)."""
    for protocol in websocket.headers.get("sec-websocket-protocol", "").split(","):
        val = protocol.strip()
        lowered = val.lower()
        for prefix in ("bearer.", "authorization.bearer."):
            if lowered.startswith(prefix) and val[len(prefix):].strip():
                return val
    return None


def authenticate_websocket_token(token: str) -> Dict[str, Any]:
    """Validate token received in first WebSocket frame."""
    _authentication_required()
    if is_auth_disabled():
        return {}
    if not token.strip():
        raise HTTPException(status_code=401, detail="Bearer token required")
    claims = decode_token(token.strip())
    require_roles(claims, settings.live_api_roles)
    return claims


def authenticate_websocket(
    websocket: WebSocket,
    *,
    required_roles: Tuple[str, ...] = (),
) -> Optional[Dict[str, Any]]:
    """Authenticate WebSocket connection via header or subprotocol."""
    _authentication_required()
    if is_auth_disabled():
        return None

    header = websocket.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        claims = decode_token(token.strip())
        require_roles(claims, required_roles)
        return claims

    if subprotocol := websocket_auth_subprotocol(websocket):
        lowered = subprotocol.lower()
        prefix = "authorization.bearer." if lowered.startswith("authorization.bearer.") else "bearer."
        token_str = subprotocol[len(prefix):].strip()
        claims = decode_token(token_str)
        require_roles(claims, required_roles)
        return claims

    raise HTTPException(
        status_code=401,
        detail="Bearer token required in Authorization header, subprotocol, or first message",
    )
