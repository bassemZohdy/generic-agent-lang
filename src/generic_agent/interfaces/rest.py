"""REST API interface providing HTTP and Server-Sent Events (SSE) streaming endpoints."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from ..agent import get_root_agent, inspect_runtime
from ..auth.middleware import SubjectBindingMiddleware
from ..config.settings import settings
from ..domain.schemas import GenericAgentResponse
from ..util import is_production

logger = logging.getLogger(__name__)

_production = is_production(settings.deployment)

app = FastAPI(
    title=f"{settings.app_name} API",
    description="Generic configuration-driven LangChain and LangGraph Agent API",
    version=settings.app_version,
    docs_url=None if _production else "/docs",
    redoc_url=None if _production else "/redoc",
    openapi_url=None if _production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SubjectBindingMiddleware)


class InvokeRequest(BaseModel):
    """Request body for agent invocation."""

    message: str = Field(description="The user input query or instruction.")
    thread_id: Optional[str] = Field(default=None, description="Optional thread/session ID for conversational continuity.")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional extra execution context.")
    user_id: Optional[str] = Field(default=None, description="Optional user ID (must match token subject if authenticated).")


class InvokeResponse(BaseModel):
    """Standardized response from agent invocation."""

    response: Union[str, Dict[str, Any]] = Field(description="The agent's answer or structured response.")
    thread_id: Optional[str] = Field(default=None, description="Thread ID.")
    use_case: str = Field(description="The active use case.")


@app.get("/health")
@app.get("/healthz")
async def health() -> Dict[str, str]:
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/info")
async def info() -> Dict[str, Any]:
    """Agent runtime metadata and capabilities."""
    return json.loads(inspect_runtime.invoke({}))


@app.post("/invoke", response_model=InvokeResponse)
@app.post("/run", response_model=InvokeResponse)
async def invoke_agent(req: InvokeRequest, request: Request) -> InvokeResponse:
    """Synchronously invoke the agent graph and return the final output."""
    engine = get_root_agent()
    user_id = getattr(request.state, "auth_subject", req.user_id) or "anonymous"

    try:
        result = await engine.ainvoke(
            message=req.message,
            context=req.context,
            thread_id=req.thread_id,
            user_id=user_id,
        )
        last_resp = result.get("last_response", "")
        if not last_resp and result.get("messages"):
            last_resp = result["messages"][-1].content

        return InvokeResponse(
            response=last_resp,
            thread_id=req.thread_id,
            use_case=engine.use_case_name,
        )
    except Exception as err:
        logger.exception("Invocation failed")
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {err}") from err


@app.post("/stream")
@app.post("/run_sse")
async def stream_agent(req: InvokeRequest, request: Request) -> EventSourceResponse:
    """Stream LangGraph events (node state changes, tokens) using Server-Sent Events (SSE)."""
    engine = get_root_agent()
    user_id = getattr(request.state, "auth_subject", req.user_id) or "anonymous"

    async def event_generator():
        try:
            async for event in engine.astream_events(
                message=req.message,
                context=req.context,
                thread_id=req.thread_id,
                user_id=user_id,
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

                # Stream model tokens
                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield {
                            "event": "token",
                            "data": json.dumps({"token": chunk.content}),
                        }
                # Stream tool events
                elif kind == "on_tool_start":
                    yield {
                        "event": "tool_start",
                        "data": json.dumps({"name": event.get("name"), "input": data.get("input")}),
                    }
                elif kind == "on_tool_end":
                    yield {
                        "event": "tool_end",
                        "data": json.dumps({"output": str(data.get("output", ""))[:500]}),
                    }
                # Stream graph node completion
                elif kind == "on_chain_end" and event.get("name") in {"agent", "step_node", "aggregator", "generator"}:
                    yield {
                        "event": "node_complete",
                        "data": json.dumps({"node": event.get("name")}),
                    }

            yield {"event": "done", "data": json.dumps({"status": "completed"})}
        except Exception as err:
            logger.exception("Streaming failed")
            yield {"event": "error", "data": json.dumps({"error": str(err)})}

    return EventSourceResponse(event_generator())
