"""Integration tests for RuntimeEngine execution and streaming."""

from __future__ import annotations

import pytest
from conftest import FakeChatModel

from generic_agent.agent import RuntimeEngine, build_root_agent, get_root_agent
from generic_agent.config.schema import AgentConfig, ExecutionConfig, ModelConfig
from generic_agent.domain.context import RuntimeContext
from generic_agent.graphs.direct import DirectStrategy


@pytest.mark.asyncio
async def test_runtime_engine_ainvoke():
    model = FakeChatModel(responses=["Hello from LangGraph engine!"])
    rt = RuntimeContext(
        model=model,
        instruction="Help the user.",
        tools=[],
        description="Test runtime",
    )
    strat = DirectStrategy()
    graph = strat.build(type("Ctx", (), {"runtime": rt, "extra_config": {}})())

    config = AgentConfig(use_case="assistant")
    engine = RuntimeEngine(config=config, runtime=rt, graph=graph, use_case_name="assistant")

    res = await engine.ainvoke("What is your status?")
    assert "last_response" in res
    assert res["last_response"] == "Hello from LangGraph engine!"


@pytest.mark.asyncio
async def test_runtime_engine_astream():
    model = FakeChatModel(responses=["Streamed reply."])
    rt = RuntimeContext(
        model=model,
        instruction="Help the user.",
        tools=[],
        description="Test runtime",
    )
    graph = DirectStrategy().build(type("Ctx", (), {"runtime": rt, "extra_config": {}})())
    config = AgentConfig(use_case="assistant")
    engine = RuntimeEngine(config=config, runtime=rt, graph=graph, use_case_name="assistant")

    chunks = []
    async for chunk in engine.astream("Hello stream"):
        chunks.append(chunk)

    assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_runtime_engine_astream_events():
    model = FakeChatModel(responses=["Event stream."])
    rt = RuntimeContext(
        model=model,
        instruction="Help the user.",
        tools=[],
        description="Test runtime",
    )
    graph = DirectStrategy().build(type("Ctx", (), {"runtime": rt, "extra_config": {}})())
    config = AgentConfig(use_case="assistant")
    engine = RuntimeEngine(config=config, runtime=rt, graph=graph, use_case_name="assistant")

    events = []
    async for ev in engine.astream_events("Hello events"):
        events.append(ev)

    assert len(events) >= 1


def test_build_root_agent():
    engine = build_root_agent()
    assert engine is not None
    assert engine.use_case_name == "assistant"
