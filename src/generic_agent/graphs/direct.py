"""DIRECT strategy: Single agent ReAct / tool-calling StateGraph."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from ..domain.context import StrategyContext
from ..domain.schemas import GenericAgentResponse
from ..domain.state import AgentState
from ..tools.audit import audit_tool_result, protect_and_audit_tool
from .base import BaseGraphStrategy

logger = logging.getLogger(__name__)


class DirectStrategy(BaseGraphStrategy):
    """Single agent with optional ReAct tool-calling loop."""

    @property
    def agent_type(self) -> str:
        return "DIRECT"

    def build(self, context: StrategyContext) -> CompiledStateGraph:
        rt = context.runtime
        tools = rt.tools or []
        llm = self.resolve_llm_for_role(context, bind_tools=bool(tools))
        instruction = self.build_instruction(context)

        workflow = StateGraph(AgentState)

        async def agent_node(state: AgentState) -> Dict[str, Any]:
            messages = list(state.get("messages", []))
            # Insert system instruction if not already the first message
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=instruction)] + messages

            response = await llm.ainvoke(messages)
            last_resp = response.content if isinstance(response.content, str) else str(response.content)

            # If structured output schema is requested, parse or format envelope
            if rt.output_schema == GenericAgentResponse:
                structured = GenericAgentResponse(
                    answer=last_resp,
                    confidence=1.0,
                    evidence=[],
                    risks=[],
                    next_steps=[],
                )
                return {"messages": [response], "last_response": structured.model_dump()}

            return {"messages": [response], "last_response": last_resp}

        workflow.add_node("agent", agent_node)

        if tools:
            # Wrap tool node with security audit callbacks
            tool_node = ToolNode(tools)

            async def audited_tool_node(state: AgentState) -> Dict[str, Any]:
                messages = state.get("messages", [])
                last_msg = messages[-1] if messages else None
                if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
                    for tc in last_msg.tool_calls:
                        t_name = tc.get("name", "")
                        t_args = tc.get("args", {})
                        matched_tool = next((t for t in tools if getattr(t, "name", "") == t_name), None)
                        if matched_tool:
                            veto = protect_and_audit_tool(matched_tool, t_args)
                            if veto and "error" in veto:
                                return {
                                    "messages": [
                                        ToolMessage(
                                            tool_call_id=tc.get("id", "veto"),
                                            content=veto["error"],
                                            name=t_name,
                                        )
                                    ]
                                }

                res = await tool_node.ainvoke(state)
                return res

            workflow.add_node("tools", audited_tool_node)

            def should_continue(state: AgentState) -> Literal["tools", "end"]:
                messages = state.get("messages", [])
                last_msg = messages[-1] if messages else None
                if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
                    return "tools"
                return "end"

            workflow.add_edge(START, "agent")
            workflow.add_conditional_edges(
                "agent",
                should_continue,
                {"tools": "tools", "end": END},
            )
            workflow.add_edge("tools", "agent")
        else:
            workflow.add_edge(START, "agent")
            workflow.add_edge("agent", END)

        return workflow.compile(checkpointer=rt.checkpointer)
