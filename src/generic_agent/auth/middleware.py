"""FastAPI middleware enforcing user subject binding and session ownership."""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config.settings import settings
from .core import authenticate_request

logger = logging.getLogger(__name__)

_OPEN_PATHS = {"/health", "/healthz", "/version", "/info"}


def _extract_subject(claims: Optional[Dict[str, Any]]) -> str:
    return str(claims.get("sub")) if claims and claims.get("sub") else "anonymous"


class SubjectBindingMiddleware(BaseHTTPMiddleware):
    """Binds request authentication claims and ensures user_id matches token subject."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Any]]):
        if request.url.path in _OPEN_PATHS:
            return await call_next(request)

        try:
            claims = authenticate_request(
                request, required_roles=settings.keycloak_required_roles
            )
        except Exception as error:
            status = getattr(error, "status_code", 503)
            detail = getattr(error, "detail", "Authentication failed")
            return JSONResponse(status_code=status, content={"detail": detail})

        subject = _extract_subject(claims)
        request.state.auth_claims = claims or {}
        request.state.auth_subject = subject

        # If calling /invoke or /stream with a JSON body, ensure user_id in payload matches subject
        if request.url.path in {"/invoke", "/stream", "/run"}:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    payload = json.loads(body_bytes.decode("utf-8"))
                    if isinstance(payload, dict):
                        payload_user = payload.get("user_id")
                        if payload_user and payload_user != subject and not settings.auth_disabled:
                            return JSONResponse(
                                status_code=403,
                                content={"detail": "user_id in payload must match authenticated token subject"},
                            )
                        payload["user_id"] = subject
                        request._body = json.dumps(payload).encode("utf-8")
            except Exception:
                pass

        return await call_next(request)
