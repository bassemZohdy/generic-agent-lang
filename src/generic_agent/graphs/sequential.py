"""SEQUENTIAL strategy: Ordered pipeline StateGraph."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..domain.context import StrategyContext
from ..domain.state import AgentState
from .base import BaseGraphStrategy

logger = logging.getLogger(__name__)


class SequentialStrategy(BaseGraphStrategy):
    """Sequential pipeline executing an ordered chain of specialized agent steps."""

    @property
    def agent_type(self) -> str:
        return "SEQUENTIAL"

    def build(self, context: StrategyContext) -> CompiledStateGraph:
        rt = context.runtime
        count = self.positive_count(context, "steps", 2)
        workflow = StateGraph(AgentState)

        step_nodes = []
        for i in range(count):
            node_name = f"step_{i}"
            role_name = f"step_{i}"
            default_prompt = (
                f"You are step {i + 1} of {count} in this execution pipeline. "
                "Perform your designated stage of the task, building directly on prior results, "
                "then deliver your clear output."
            )
            step_instruction = self.build_instruction(context, role_name, default=default_prompt)
            llm = self.resolve_llm_for_role(context, role_name, bind_tools=False)

            def make_step_node(idx: int, inst: str, model: Any):
                async def step_node(state: AgentState) -> Dict[str, Any]:
                    messages = list(state.get("messages", []))
                    intermediate = list(state.get("intermediate_steps", []))

                    prompt_messages = [
                        SystemMessage(content=inst),
                    ]
                    # Include prior step summaries if available
                    if intermediate:
                        prior_text = "\n\n".join(
                            f"Step {s.get('step', i)} Output: {s.get('output', '')}"
                            for i, s in enumerate(intermediate)
                        )
                        prompt_messages.append(
                            HumanMessage(content=f"Previous pipeline stages:\n{prior_text}")
                        )

                    prompt_messages.extend([m for m in messages if not isinstance(m, SystemMessage)])
                    response = await model.ainvoke(prompt_messages)
                    resp_text = response.content if isinstance(response.content, str) else str(response.content)

                    updated_intermediate = intermediate + [{"step": idx, "output": resp_text}]
                    return {
                        "messages": [AIMessage(content=resp_text, name=f"step_{idx}")],
                        "intermediate_steps": updated_intermediate,
                        "last_response": resp_text,
                    }

                return step_node

            workflow.add_node(node_name, make_step_node(i, step_instruction, llm))
            step_nodes.append(node_name)

        # Wire linear pipeline: START -> step_0 -> step_1 -> ... -> END
        workflow.add_edge(START, step_nodes[0])
        for i in range(len(step_nodes) - 1):
            workflow.add_edge(step_nodes[i], step_nodes[i + 1])
        workflow.add_edge(step_nodes[-1], END)

        return workflow.compile(checkpointer=rt.checkpointer)
