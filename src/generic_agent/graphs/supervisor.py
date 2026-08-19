"""SUPERVISOR strategy: Team coordinator StateGraph."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..domain.context import StrategyContext
from ..domain.state import AgentState
from .base import BaseGraphStrategy

logger = logging.getLogger(__name__)


class SupervisorStrategy(BaseGraphStrategy):
    """Team coordinator orchestrating and delegating tasks across specialized team workers."""

    @property
    def agent_type(self) -> str:
        return "SUPERVISOR"

    def build(self, context: StrategyContext) -> CompiledStateGraph:
        rt = context.runtime
        count = self.positive_count(context, "workers", 2)
        worker_names = [f"worker_{i}" for i in range(count)]
        max_iters = rt.max_iterations

        supervisor_llm = self.resolve_llm_for_role(context, "supervisor", bind_tools=False)
        supervisor_inst = (
            f"You are the team supervisor coordinator. Available workers: {', '.join(worker_names)}.\n"
            "Review current progress. If more work is needed, delegate to the appropriate worker.\n"
            "If the task is fully completed, respond with 'FINISH:' followed by your final comprehensive answer."
        )

        workflow = StateGraph(AgentState)

        async def supervisor_node(state: AgentState) -> Dict[str, Any]:
            current_step = state.get("current_step", 0) + 1
            messages = list(state.get("messages", []))
            intermediate = state.get("intermediate_steps", [])

            prompt = [SystemMessage(content=supervisor_inst)]
            if intermediate:
                history_txt = "\n\n".join(
                    f"[{step.get('worker', 'worker')}]: {step.get('output', '')}"
                    for step in intermediate
                )
                prompt.append(HumanMessage(content=f"Worker progress so far:\n{history_txt}"))

            user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
            prompt.extend(user_msgs)

            response = await supervisor_llm.ainvoke(prompt)
            resp_text = response.content if isinstance(response.content, str) else str(response.content)

            target = "FINISH"
            if current_step >= max_iters or resp_text.strip().startswith("FINISH"):
                target = "FINISH"
                final_ans = resp_text.replace("FINISH:", "").strip() if resp_text.startswith("FINISH") else resp_text
            else:
                for w in worker_names:
                    if w in resp_text.lower():
                        target = w
                        break
                if target == "FINISH":
                    target = worker_names[0]
                final_ans = resp_text

            return {
                "current_step": current_step,
                "target_specialist": target,
                "last_response": final_ans,
                "messages": [AIMessage(content=final_ans, name="supervisor")],
            }

        workflow.add_node("supervisor", supervisor_node)

        # Build each worker node
        for i in range(count):
            w_name = f"worker_{i}"
            default_prompt = f"You are worker {i + 1} of {count}. Execute your part of the assignment diligently."
            w_inst = self.build_instruction(context, w_name, default=default_prompt)
            w_llm = self.resolve_llm_for_role(context, w_name, bind_tools=True)

            def make_worker_node(name: str, inst: str, model: Any):
                async def worker_node(state: AgentState) -> Dict[str, Any]:
                    messages = list(state.get("messages", []))
                    user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
                    prompt = [SystemMessage(content=inst)] + user_msgs

                    response = await model.ainvoke(prompt)
                    resp_text = response.content if isinstance(response.content, str) else str(response.content)

                    intermediate = list(state.get("intermediate_steps", []))
                    intermediate.append({"worker": name, "output": resp_text})
                    return {
                        "intermediate_steps": intermediate,
                        "messages": [AIMessage(content=resp_text, name=name)],
                    }

                return worker_node

            workflow.add_node(w_name, make_worker_node(w_name, w_inst, w_llm))
            # Workers report back to supervisor
            workflow.add_edge(w_name, "supervisor")

        def route_supervisor(state: AgentState) -> str:
            target = state.get("target_specialist", "FINISH")
            if target == "FINISH" or state.get("current_step", 0) >= max_iters:
                return "end"
            return target

        workflow.add_edge(START, "supervisor")
        routing_dict = {w: w for w in worker_names}
        routing_dict["end"] = END
        workflow.add_conditional_edges("supervisor", route_supervisor, routing_dict)

        return workflow.compile(checkpointer=rt.checkpointer)
