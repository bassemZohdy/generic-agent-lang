"""Generic service-status API for OpenAPI toolset integration."""

import logging
from typing import Dict, Optional

from fastapi import FastAPI, Header, Request

from ..auth.core import authenticate_request
from ..config.settings import settings
from ..util import is_production

logger = logging.getLogger(__name__)
_production = is_production(settings.deployment)

app = FastAPI(
    title=settings.openapi_title,
    version=settings.app_version,
    docs_url=None if _production else "/docs",
    redoc_url=None if _production else "/redoc",
)


def get_service_status() -> Dict[str, str]:
    return {
        "service": settings.app_name,
        "environment": settings.deployment,
        "status": "healthy",
        "version": settings.app_version,
    }


@app.get("/status", operation_id="getServiceStatus")
@app.get("/release/status", include_in_schema=False)
def service_status(
    request: Request,
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, str]:
    """Return status after authentication."""
    authenticate_request(
        request, api_key=x_api_key, required_roles=settings.service_api_roles
    )
    return get_service_status()
