"""Command-line interface for running, inspecting, and serving generic-agent-lang."""

from __future__ import annotations

import json
import sys
import click
import uvicorn

from ..agent import build_root_agent, get_root_agent, inspect_runtime
from ..config.loader import resolve_agent_config


@click.group()
def main():
    """Generic Agent Runtime (LangChain & LangGraph)."""
    pass


@main.command()
@click.argument("message", required=True)
@click.option("--thread-id", default=None, help="Thread/Session ID.")
def run(message: str, thread_id: str | None):
    """Run a single prompt through the configured agent."""
    engine = get_root_agent()
    click.echo(f"Running agent with use_case={engine.use_case_name}...")
    result = engine.invoke(message, thread_id=thread_id)
    last_resp = result.get("last_response") or result.get("messages", [""])[-1].content
    click.echo(f"\nResponse:\n{last_resp}")


@main.command()
def inspect():
    """Inspect active agent configuration and capabilities."""
    config = resolve_agent_config()
    info = json.loads(inspect_runtime.invoke({}))
    click.echo("Agent Runtime Info:")
    click.echo(json.dumps(info, indent=2))
    click.echo("\nResolved AgentConfig:")
    click.echo(json.dumps(config.model_dump(), indent=2))


@main.command()
@click.option("--port", default=8002, help="Port to bind.")
@click.option("--host", default="0.0.0.0", help="Host interface.")
def serve(port: int, host: str):
    """Start the REST API server."""
    uvicorn.run("generic_agent.interfaces.rest:app", host=host, port=port, reload=False)


@main.command()
@click.option("--port", default=8003, help="Port to bind.")
@click.option("--host", default="0.0.0.0", help="Host interface.")
def serve_live(port: int, host: str):
    """Start the Live WebSocket server."""
    uvicorn.run("generic_agent.interfaces.live:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
