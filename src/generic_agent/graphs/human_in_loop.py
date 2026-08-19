"""HUMAN_IN_LOOP strategy: Propose, approval gate, and completion StateGraph."""

from __future__ import annotations

import logging
from typing import Any, Dict, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..domain.context import StrategyContext
from ..domain.state import AgentState
from .base import BaseGraphStrategy

logger = logging.getLogger(__name__)


class HumanInLoopStrategy(BaseGraphStrategy):
    """Human-in-the-loop pattern: propose action, await human approval, then execute completion."""

    @property
    def agent_type(self) -> str:
        return "HUMAN_IN_LOOP"

    def validate(self, context: StrategyContext) -> None:
        if not context.runtime.require_approval:
            raise ValueError("HUMAN_IN_LOOP strategy requires require_approval=True")

    def build(self, context: StrategyContext) -> CompiledStateGraph:
        self.validate(context)
        rt = context.runtime

        proposer_llm = self.resolve_llm_for_role(context, "proposer", bind_tools=False)
        completer_llm = self.resolve_llm_for_role(context, "completer", bind_tools=True)

        proposer_inst = self.build_instruction(
            context,
            "proposer",
            default="Propose a clear, actionable solution for the user's request. State any actions requiring confirmation.",
        )
        completer_inst = self.build_instruction(
            context,
            "completer",
            default="Complete and execute the user-approved action thoroughly.",
        )

        workflow = StateGraph(AgentState)

        async def proposer_node(state: AgentState) -> Dict[str, Any]:
            messages = list(state.get("messages", []))
            user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
            prompt = [SystemMessage(content=proposer_inst)] + user_msgs

            response = await proposer_llm.ainvoke(prompt)
            proposal = response.content if isinstance(response.content, str) else str(response.content)

            status = state.get("approval_status", "approved")
            return {
                "approval_status": status,
                "last_response": proposal,
                "messages": [AIMessage(content=proposal, name="proposer")],
            }

        async def completer_node(state: AgentState) -> Dict[str, Any]:
            proposal = state.get("last_response", "")
            messages = list(state.get("messages", []))
            user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

            prompt = [
                SystemMessage(content=completer_inst),
                HumanMessage(content=f"Approved Proposal to complete:\n{proposal}"),
            ]
            prompt.extend(user_msgs)

            response = await completer_llm.ainvoke(prompt)
            resp_text = response.content if isinstance(response.content, str) else str(response.content)

            return {
                "last_response": resp_text,
                "messages": [AIMessage(content=resp_text, name="completer")],
            }

        def route_approval(state: AgentState) -> Literal["complete", "end"]:
            status = state.get("approval_status", "approved").lower()
            if status in {"rejected", "denied"}:
                return "end"
            return "complete"

        workflow.add_node("proposer", proposer_node)
        workflow.add_node("completer", completer_node)

        workflow.add_edge(START, "proposer")
        workflow.add_conditional_edges("proposer", route_approval, {"complete": "completer", "end": END})
        workflow.add_edge("completer", END)

        return workflow.compile(checkpointer=rt.checkpointer)
