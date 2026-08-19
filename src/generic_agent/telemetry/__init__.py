"""Telemetry package for generic-agent-lang."""

from .tracing import invocation_attributes, trace_invocation, tracer

__all__ = ["invocation_attributes", "trace_invocation", "tracer"]
