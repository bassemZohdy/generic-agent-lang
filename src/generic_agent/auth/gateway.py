"""Forward-auth gateway endpoint for reverse proxies like Traefik."""

from __future__ import annotations

import logging
from typing import Dict

from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse

from ..config.settings import settings
from .core import authenticate_request, claim_roles

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Forward Auth Gateway",
    description="Traefik forward-auth verification endpoint.",
    version=settings.app_version,
)


@app.get("/auth")
@app.post("/auth")
async def verify_auth(
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> Response:
    """Validate request authentication and return forwarded user identity headers."""
    try:
        claims = authenticate_request(
            request,
            api_key=x_api_key,
            required_roles=settings.keycloak_required_roles,
        )
    except Exception as error:
        status = getattr(error, "status_code", 401)
        detail = getattr(error, "detail", "Unauthorized")
        return JSONResponse(status_code=status, content={"detail": detail})

    sub = str(claims.get("sub")) if claims and claims.get("sub") else "anonymous"
    roles = ",".join(sorted(claim_roles(claims))) if claims else ""

    response = Response(status_code=200)
    response.headers["X-Auth-Subject"] = sub
    response.headers["X-Auth-Roles"] = roles
    return response


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "auth-gateway"}
