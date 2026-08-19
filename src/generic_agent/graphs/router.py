"""ROUTER strategy: Dynamic specialist dispatch StateGraph."""

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


class RouterStrategy(BaseGraphStrategy):
    """Dynamic router analyzing user intent and dispatching to configured domain specialists."""

    @property
    def agent_type(self) -> str:
        return "ROUTER"

    def validate(self, context: StrategyContext) -> None:
        if not context.runtime.specialists:
            raise ValueError("ROUTER strategy requires at least one specialist in config")

    def build(self, context: StrategyContext) -> CompiledStateGraph:
        self.validate(context)
        rt = context.runtime
        specialists = list(rt.specialists)

        router_llm = self.resolve_llm_for_role(context, "router", bind_tools=False)
        router_inst = (
            f"You are a triage router. Available specialists: {', '.join(specialists)}.\n"
            "Analyze the request and choose the single best specialist. "
            "Reply strictly with only the name of the chosen specialist."
        )

        workflow = StateGraph(AgentState)

        async def router_node(state: AgentState) -> Dict[str, Any]:
            messages = list(state.get("messages", []))
            user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
            prompt = [SystemMessage(content=router_inst)] + user_msgs

            response = await router_llm.ainvoke(prompt)
            choice = str(response.content).strip().lower()

            # Match chosen specialist or fallback to first
            matched = next((s for s in specialists if s.lower() in choice), specialists[0])
            logger.info("Router dispatched to specialist: %s", matched)
            return {"target_specialist": matched}

        workflow.add_node("router", router_node)

        # Build each specialist node
        for name in specialists:
            node_name = f"specialist_{name}"
            default_prompt = f"You are the {name} specialist. Provide domain-expert assistance for this request."
            specialist_inst = self.build_instruction(context, name, default=default_prompt)
            spec_llm = self.resolve_llm_for_role(context, name, bind_tools=True)

            def make_specialist_node(s_name: str, inst: str, model: Any):
                async def specialist_node(state: AgentState) -> Dict[str, Any]:
                    messages = list(state.get("messages", []))
                    user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
                    prompt = [SystemMessage(content=inst)] + user_msgs

                    response = await model.ainvoke(prompt)
                    resp_text = response.content if isinstance(response.content, str) else str(response.content)

                    return {
                        "messages": [AIMessage(content=resp_text, name=f"specialist_{s_name}")],
                        "last_response": resp_text,
                    }

                return specialist_node

            workflow.add_node(node_name, make_specialist_node(name, specialist_inst, spec_llm))
            workflow.add_edge(node_name, END)

        def route_specialist(state: AgentState) -> str:
            target = state.get("target_specialist", specialists[0])
            return f"specialist_{target}"

        routing_map = {f"specialist_{s}": f"specialist_{s}" for s in specialists}
        workflow.add_edge(START, "router")
        workflow.add_conditional_edges("router", route_specialist, routing_map)

        return workflow.compile(checkpointer=rt.checkpointer)
