"""OpenTelemetry tracing and observability support."""

from __future__ import annotations

import contextlib
import logging
from typing import Any, Dict, Generator, Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from ..config.settings import settings

logger = logging.getLogger(__name__)

# Initialize default TracerProvider if not already configured
if not isinstance(trace.get_tracer_provider(), TracerProvider):
    resource = Resource.create({"service.name": settings.app_name, "service.version": settings.app_version})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

tracer = trace.get_tracer("generic_agent", settings.app_version)


def invocation_attributes(
    invocation_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    use_case: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, str]:
    """Assemble standard span attributes for an agent invocation."""
    attrs = {
        "agent.name": settings.app_name,
        "agent.invocation_id": invocation_id,
        "agent.deployment": settings.deployment,
    }
    if user_id:
        attrs["user.id"] = user_id
    if session_id:
        attrs["session.id"] = session_id
    if use_case:
        attrs["agent.use_case"] = use_case
    if model:
        attrs["agent.model"] = model
    return attrs


@contextlib.contextmanager
def trace_invocation(
    invocation_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    use_case: Optional[str] = None,
) -> Generator[trace.Span, None, None]:
    """Context manager for wrapping an agent invocation in an OpenTelemetry span."""
    attrs = invocation_attributes(
        invocation_id=invocation_id,
        user_id=user_id,
        session_id=session_id,
        use_case=use_case,
        model=settings.model,
    )
    with tracer.start_as_current_span(f"{settings.app_name}.invocation", attributes=attrs) as span:
        yield span
