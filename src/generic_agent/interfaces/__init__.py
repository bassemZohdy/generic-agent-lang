"""Interfaces package for generic-agent-lang."""

from .cli import main
from .live import app as live_app
from .rest import app as rest_app
from .service import app as service_app

__all__ = ["live_app", "main", "rest_app", "service_app"]
