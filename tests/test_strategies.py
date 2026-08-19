"""Integration and unit tests for LangGraph state graph strategies."""

from __future__ import annotations

import pytest
from conftest import FakeChatModel
from langchain_core.messages import HumanMessage

from generic_agent.domain.context import RuntimeContext, StrategyContext
from generic_agent.domain.state import AgentState
from generic_agent.graphs.direct import DirectStrategy
from generic_agent.graphs.evaluator_optimizer import EvaluatorOptimizerStrategy
from generic_agent.graphs.human_in_loop import HumanInLoopStrategy
from generic_agent.graphs.parallel import ParallelStrategy
from generic_agent.graphs.planner_executor import PlannerExecutorStrategy
from generic_agent.graphs.router import RouterStrategy
from generic_agent.graphs.sequential import SequentialStrategy
from generic_agent.graphs.supervisor import SupervisorStrategy


def make_test_runtime(**kwargs):
    model = FakeChatModel(
        responses=[
            "Test response 1",
            "Test response 2",
            "Test response 3",
            "Test response 4",
            "Test response 5",
            "Test response 6",
            "FINISH: Final report complete.",
        ]
    )
    defaults = {
        "model": model,
        "instruction": "Test instructions",
        "tools": [],
        "description": "Test agent",
        "max_iterations": 3,
        "require_approval": False,
        "specialists": ("billing", "technical"),
    }
    defaults.update(kwargs)
    return RuntimeContext(**defaults)


@pytest.mark.asyncio
async def test_direct_strategy():
    rt = make_test_runtime()
    strat = DirectStrategy()
    context = StrategyContext(strategy_type="DIRECT", runtime=rt)
    graph = strat.build(context)

    res = await graph.ainvoke({"messages": [HumanMessage(content="Hello")]})
    assert "messages" in res
    assert len(res["messages"]) >= 1


@pytest.mark.asyncio
async def test_sequential_strategy():
    rt = make_test_runtime()
    strat = SequentialStrategy()
    context = StrategyContext(strategy_type="SEQUENTIAL", runtime=rt, extra_config={"steps": 2})
    graph = strat.build(context)

    res = await graph.ainvoke({"messages": [HumanMessage(content="Process data")]})
    assert len(res.get("intermediate_steps", [])) == 2
    assert "last_response" in res


@pytest.mark.asyncio
async def test_parallel_strategy():
    rt = make_test_runtime()
    strat = ParallelStrategy()
    context = StrategyContext(strategy_type="PARALLEL", runtime=rt, extra_config={"workers": 2})
    graph = strat.build(context)

    res = await graph.ainvoke({"messages": [HumanMessage(content="Analyze problem")]})
    assert len(res.get("worker_outputs", {})) == 2
    assert "last_response" in res


@pytest.mark.asyncio
async def test_evaluator_optimizer_strategy():
    rt = make_test_runtime(max_iterations=2)
    strat = EvaluatorOptimizerStrategy()
    context = StrategyContext(strategy_type="EVALUATOR_OPTIMIZER", runtime=rt)
    graph = strat.build(context)

    res = await graph.ainvoke({"messages": [HumanMessage(content="Draft proposal")]})
    assert "evaluation" in res
    assert "last_response" in res


@pytest.mark.asyncio
async def test_router_strategy():
    rt = make_test_runtime(specialists=("billing", "technical"))
    strat = RouterStrategy()
    context = StrategyContext(strategy_type="ROUTER", runtime=rt)
    graph = strat.build(context)

    res = await graph.ainvoke({"messages": [HumanMessage(content="billing invoice question")]})
    assert "last_response" in res


@pytest.mark.asyncio
async def test_supervisor_strategy():
    rt = make_test_runtime(max_iterations=2)
    strat = SupervisorStrategy()
    context = StrategyContext(strategy_type="SUPERVISOR", runtime=rt, extra_config={"workers": 2})
    graph = strat.build(context)

    res = await graph.ainvoke({"messages": [HumanMessage(content="Coordinate research and review")]})
    assert "last_response" in res


@pytest.mark.asyncio
async def test_planner_executor_strategy():
    rt = make_test_runtime()
    strat = PlannerExecutorStrategy()
    context = StrategyContext(strategy_type="PLAN_EXECUTE", runtime=rt)
    graph = strat.build(context)

    res = await graph.ainvoke({"messages": [HumanMessage(content="Build website plan")]})
    assert "plan" in res
    assert "last_response" in res


@pytest.mark.asyncio
async def test_human_in_loop_strategy():
    rt = make_test_runtime(require_approval=True)
    strat = HumanInLoopStrategy()
    context = StrategyContext(strategy_type="HUMAN_IN_LOOP", runtime=rt)
    graph = strat.build(context)

    res = await graph.ainvoke({"messages": [HumanMessage(content="Delete data")], "approval_status": "approved"})
    assert "last_response" in res
