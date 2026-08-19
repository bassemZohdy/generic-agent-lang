"""WebSocket live interactive streaming interface for generic-agent-lang."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections import deque
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from ..agent import get_root_agent, inspect_runtime
from ..auth.core import (
    authenticate_websocket,
    authenticate_websocket_token,
    is_auth_disabled,
    websocket_auth_subprotocol,
)
from ..config.settings import settings
from ..util import is_production

logger = logging.getLogger(__name__)
_production = is_production(settings.deployment)

app = FastAPI(
    title=f"{settings.app_name} Live API",
    description="Bidirectional WebSocket streaming interface to generic-agent-lang.",
    version=settings.app_version,
    docs_url=None if _production else "/docs",
    redoc_url=None if _production else "/redoc",
)

_message_windows: Dict[str, deque[float]] = {}


def _is_rate_limited(subject: str) -> bool:
    timestamps = _message_windows.setdefault(subject, deque())
    now = time.monotonic()
    cutoff = now - 60.0
    while timestamps and timestamps[0] <= cutoff:
        timestamps.popleft()
    if len(timestamps) >= settings.live_max_messages_per_minute:
        return True
    timestamps.append(now)
    return False


async def _receive_json_message(websocket: WebSocket) -> Dict[str, Any]:
    raw = await websocket.receive_text()
    if len(raw.encode("utf-8")) > settings.live_max_message_bytes:
        await websocket.close(code=1009, reason="WebSocket message exceeds size limit")
        raise WebSocketDisconnect(code=1009)
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as err:
        await websocket.close(code=1003, reason="Expected valid JSON frame")
        raise WebSocketDisconnect(code=1003) from err
    if not isinstance(msg, dict):
        await websocket.close(code=1003, reason="Expected JSON object")
        raise WebSocketDisconnect(code=1003)
    return msg


@app.get("/healthz")
@app.get("/health")
async def healthz() -> Dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "live_model": settings.live_model}


@app.websocket("/live")
async def live_endpoint(websocket: WebSocket) -> None:
    """Handle interactive WebSocket connections with authentication and streaming."""
    claims: Optional[Dict[str, Any]] = None
    subprotocol = websocket_auth_subprotocol(websocket)
    has_header = bool(websocket.headers.get("authorization"))

    try:
        if is_auth_disabled() or has_header or subprotocol:
            claims = authenticate_websocket(websocket, required_roles=settings.live_api_roles)
            await websocket.accept(subprotocol=subprotocol)
        else:
            await websocket.accept()
            auth_msg = await _receive_json_message(websocket)
            if auth_msg.get("type") != "auth" or not isinstance(auth_msg.get("access_token"), str):
                raise HTTPException(status_code=401, detail="First WebSocket message must authenticate")
            claims = authenticate_websocket_token(auth_msg["access_token"])
    except (HTTPException, WebSocketDisconnect) as err:
        reason = str(getattr(err, "detail", err))[:120]
        logger.warning("WebSocket authentication rejected: %s", reason)
        with contextlib.suppress(Exception):
            await websocket.close(code=4401, reason=reason)
        return
    except Exception:
        logger.exception("Unexpected WebSocket auth error")
        with contextlib.suppress(Exception):
            await websocket.close(code=1011, reason="Authentication failed")
        return

    user_id = str(claims.get("sub")) if claims and claims.get("sub") else "anonymous"
    session_id = websocket.query_params.get("session_id") or "default_session"

    logger.info("WebSocket connected user=%s session=%s", user_id, session_id)
    await websocket.send_json({"type": "session", "session_id": session_id})

    engine = get_root_agent()

    try:
        while True:
            data = await _receive_json_message(websocket)
            if _is_rate_limited(user_id):
                await websocket.close(code=4429, reason="Rate limit exceeded")
                return

            if data.get("close"):
                await websocket.close(code=1000)
                break

            if text := data.get("text"):
                if not isinstance(text, str):
                    await websocket.close(code=1003, reason="text must be a string")
                    return

                try:
                    async for event in engine.astream_events(
                        message=text,
                        thread_id=session_id,
                        user_id=user_id,
                    ):
                        kind = event.get("event", "")
                        ev_data = event.get("data", {})
                        if kind == "on_chat_model_stream":
                            chunk = ev_data.get("chunk")
                            if chunk and hasattr(chunk, "content") and chunk.content:
                                await websocket.send_json({
                                    "type": "content",
                                    "text": chunk.content,
                                })
                        elif kind == "on_chat_model_end":
                            output = ev_data.get("output")
                            if output and hasattr(output, "content") and output.content:
                                await websocket.send_json({
                                    "type": "content",
                                    "text": output.content,
                                })
                        elif kind == "on_tool_start":
                            await websocket.send_json({
                                "type": "tool_call",
                                "tool": event.get("name"),
                            })
                except Exception as err:
                    logger.warning("Streaming event error: %s", err)

                await websocket.send_json({"type": "turn_complete"})
            else:
                await websocket.send_json({"type": "ack"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected user=%s", user_id)
    except Exception:
        logger.exception("Live connection error")
