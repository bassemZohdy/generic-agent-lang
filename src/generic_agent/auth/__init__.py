"""Authentication package for generic-agent-lang."""

from .core import (
    authenticate_request,
    authenticate_websocket,
    authenticate_websocket_token,
    claim_roles,
    decode_token,
    keycloak_enabled,
    require_roles,
    token_from_request,
    websocket_auth_subprotocol,
)
from .middleware import SubjectBindingMiddleware

__all__ = [
    "SubjectBindingMiddleware",
    "authenticate_request",
    "authenticate_websocket",
    "authenticate_websocket_token",
    "claim_roles",
    "decode_token",
    "keycloak_enabled",
    "require_roles",
    "token_from_request",
    "websocket_auth_subprotocol",
]
