"""PARALLEL strategy: Concurrent multi-worker StateGraph with aggregation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..domain.context import StrategyContext
from ..domain.state import AgentState
from .base import BaseGraphStrategy

logger = logging.getLogger(__name__)


class ParallelStrategy(BaseGraphStrategy):
    """Concurrent execution of multiple independent worker perspectives aggregated into a final synthesis."""

    @property
    def agent_type(self) -> str:
        return "PARALLEL"

    def build(self, context: StrategyContext) -> CompiledStateGraph:
        rt = context.runtime
        count = self.positive_count(context, "workers", 2)
        workflow = StateGraph(AgentState)

        worker_nodes = []
        for i in range(count):
            node_name = f"worker_{i}"
            role_name = f"worker_{i}"
            default_prompt = (
                f"You are worker {i + 1} of {count} analyzing this request concurrently. "
                "Provide your unique perspective, analysis, and solution."
            )
            worker_instruction = self.build_instruction(context, role_name, default=default_prompt)
            llm = self.resolve_llm_for_role(context, role_name, bind_tools=False)

            def make_worker_node(idx: int, inst: str, model: Any):
                async def worker_node(state: AgentState) -> Dict[str, Any]:
                    messages = list(state.get("messages", []))
                    user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
                    prompt = [SystemMessage(content=inst)] + user_msgs

                    response = await model.ainvoke(prompt)
                    resp_text = response.content if isinstance(response.content, str) else str(response.content)

                    # Return dictionary delta; merge_dicts reducer aggregates all workers
                    return {
                        "worker_outputs": {f"worker_{idx}": resp_text},
                    }

                return worker_node

            workflow.add_node(node_name, make_worker_node(i, worker_instruction, llm))
            worker_nodes.append(node_name)

        # Aggregator node synthesizes outputs from all parallel workers
        aggregator_llm = self.resolve_llm_for_role(context, "aggregator", bind_tools=False)

        async def aggregate_node(state: AgentState) -> Dict[str, Any]:
            worker_outputs = state.get("worker_outputs", {})
            perspectives = "\n\n".join(
                f"### Perspective ({w_name}):\n{out}"
                for w_name, out in worker_outputs.items()
            )
            prompt = [
                SystemMessage(
                    content=(
                        "You are an expert synthesizer. Combine the following distinct "
                        "perspectives from multiple workers into a single, cohesive, well-reasoned response."
                    )
                ),
                HumanMessage(
                    content=f"Worker Perspectives:\n{perspectives}\n\nProvide the consolidated final answer:"
                ),
            ]
            response = await aggregator_llm.ainvoke(prompt)
            resp_text = response.content if isinstance(response.content, str) else str(response.content)
            return {
                "messages": [AIMessage(content=resp_text, name="aggregator")],
                "last_response": resp_text,
            }

        workflow.add_node("aggregator", aggregate_node)

        # Wire fan-out: START -> each worker -> aggregator -> END
        for w_node in worker_nodes:
            workflow.add_edge(START, w_node)
            workflow.add_edge(w_node, "aggregator")

        workflow.add_edge("aggregator", END)

        return workflow.compile(checkpointer=rt.checkpointer)
