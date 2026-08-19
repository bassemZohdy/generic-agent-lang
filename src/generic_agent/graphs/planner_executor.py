"""PLAN_EXECUTE strategy: Plan then execute StateGraph."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..domain.context import StrategyContext
from ..domain.state import AgentState
from .base import BaseGraphStrategy

logger = logging.getLogger(__name__)


class PlannerExecutorStrategy(BaseGraphStrategy):
    """Plan-then-execute pattern: creates an explicit plan, executes steps, and synthesizes the final output."""

    @property
    def agent_type(self) -> str:
        return "PLAN_EXECUTE"

    def build(self, context: StrategyContext) -> CompiledStateGraph:
        rt = context.runtime
        planner_llm = self.resolve_llm_for_role(context, "planner", bind_tools=False)
        executor_llm = self.resolve_llm_for_role(context, "executor", bind_tools=True)

        planner_inst = self.build_instruction(
            context,
            "planner",
            default=(
                "Create a clear, step-by-step plan to thoroughly solve the user's request. "
                "List each step concisely."
            ),
        )
        executor_inst = self.build_instruction(
            context,
            "executor",
            default="Execute the provided step-by-step plan. Complete every step thoroughly and provide the final solution.",
        )

        workflow = StateGraph(AgentState)

        async def planner_node(state: AgentState) -> Dict[str, Any]:
            messages = list(state.get("messages", []))
            user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
            prompt = [SystemMessage(content=planner_inst)] + user_msgs

            response = await planner_llm.ainvoke(prompt)
            plan_text = response.content if isinstance(response.content, str) else str(response.content)

            steps = [line.strip() for line in plan_text.splitlines() if line.strip()]
            return {
                "plan": steps,
                "messages": [AIMessage(content=plan_text, name="planner")],
            }

        async def executor_node(state: AgentState) -> Dict[str, Any]:
            plan = state.get("plan", [])
            messages = list(state.get("messages", []))
            user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

            plan_str = "\n".join(plan)
            prompt = [
                SystemMessage(content=executor_inst),
                HumanMessage(content=f"Plan to execute:\n{plan_str}\n\nExecute the plan and deliver the complete solution:"),
            ]
            prompt.extend(user_msgs)

            response = await executor_llm.ainvoke(prompt)
            resp_text = response.content if isinstance(response.content, str) else str(response.content)

            return {
                "last_response": resp_text,
                "messages": [AIMessage(content=resp_text, name="executor")],
            }

        workflow.add_node("planner", planner_node)
        workflow.add_node("executor", executor_node)

        workflow.add_edge(START, "planner")
        workflow.add_edge("planner", "executor")
        workflow.add_edge("executor", END)

        return workflow.compile(checkpointer=rt.checkpointer)
