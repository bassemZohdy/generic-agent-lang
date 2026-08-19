"""EVALUATOR_OPTIMIZER strategy: Generate-evaluate-refine feedback loop StateGraph."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..domain.context import StrategyContext
from ..domain.schemas import EvaluationResult
from ..domain.state import AgentState
from .base import BaseGraphStrategy

logger = logging.getLogger(__name__)


class EvaluatorOptimizerStrategy(BaseGraphStrategy):
    """Generate-evaluate-refine iterative loop with explicit criteria assessment."""

    @property
    def agent_type(self) -> str:
        return "EVALUATOR_OPTIMIZER"

    def validate(self, context: StrategyContext) -> None:
        self.require_min_iterations(context, minimum=1)

    def build(self, context: StrategyContext) -> CompiledStateGraph:
        self.validate(context)
        rt = context.runtime
        max_iters = rt.max_iterations

        generator_llm = self.resolve_llm_for_role(context, "generator", bind_tools=False)
        evaluator_llm = self.resolve_llm_for_role(context, "evaluator", bind_tools=False)

        generator_inst = self.build_instruction(
            context,
            "generator",
            default="Generate a high-quality, comprehensive solution for the user request. Incorporate any feedback provided.",
        )
        evaluator_inst = self.build_instruction(
            context,
            "evaluator",
            default=(
                "You are a rigorous quality evaluator. Critically assess the candidate solution. "
                "Output your evaluation strictly in JSON format with fields: "
                "score (float 0.0-1.0), is_acceptable (bool), feedback (string), improvements (list of strings)."
            ),
        )

        workflow = StateGraph(AgentState)

        async def generator_node(state: AgentState) -> Dict[str, Any]:
            current_step = state.get("current_step", 0) + 1
            messages = list(state.get("messages", []))
            user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
            evaluation = state.get("evaluation")

            prompt = [SystemMessage(content=generator_inst)]
            if evaluation and evaluation.get("feedback"):
                feedback_prompt = (
                    f"Previous attempt was evaluated with score {evaluation.get('score', 0.0)}:\n"
                    f"Critique: {evaluation.get('feedback')}\n"
                    f"Recommended Improvements: {', '.join(evaluation.get('improvements', []))}\n"
                    "Please refine and improve the solution addressing all feedback."
                )
                prompt.append(HumanMessage(content=feedback_prompt))

            prompt.extend(user_msgs)
            response = await generator_llm.ainvoke(prompt)
            resp_text = response.content if isinstance(response.content, str) else str(response.content)

            return {
                "current_step": current_step,
                "max_iterations": max_iters,
                "last_response": resp_text,
                "messages": [AIMessage(content=resp_text, name="generator")],
            }

        async def evaluator_node(state: AgentState) -> Dict[str, Any]:
            last_resp = state.get("last_response", "")
            messages = list(state.get("messages", []))
            user_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

            eval_prompt = [
                SystemMessage(content=evaluator_inst),
                HumanMessage(
                    content=(
                        f"Candidate Solution:\n{last_resp}\n\n"
                        "Evaluate this candidate against the user request. Return valid JSON only."
                    )
                ),
            ]
            eval_resp = await evaluator_llm.ainvoke(eval_prompt)
            eval_text = eval_resp.content if isinstance(eval_resp.content, str) else str(eval_resp.content)

            # Parse evaluation result
            eval_data: Dict[str, Any] = {
                "score": 0.85,
                "is_acceptable": True,
                "feedback": "Acceptable output.",
                "improvements": [],
            }
            try:
                cleaned = eval_text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    eval_data.update(parsed)
            except Exception:
                # If LLM didn't return pure JSON, estimate acceptability based on keywords or iteration count
                if "not acceptable" in eval_text.lower() or "needs improvement" in eval_text.lower():
                    eval_data["is_acceptable"] = False
                    eval_data["score"] = 0.5
                eval_data["feedback"] = eval_text

            return {"evaluation": eval_data}

        def route_eval(state: AgentState) -> Literal["generate", "end"]:
            current_step = state.get("current_step", 1)
            evaluation = state.get("evaluation", {})
            is_acceptable = evaluation.get("is_acceptable", False)
            score = evaluation.get("score", 0.0)

            if is_acceptable or score >= 0.85 or current_step >= max_iters:
                return "end"
            return "generate"

        workflow.add_node("generator", generator_node)
        workflow.add_node("evaluator", evaluator_node)

        workflow.add_edge(START, "generator")
        workflow.add_edge("generator", "evaluator")
        workflow.add_conditional_edges(
            "evaluator",
            route_eval,
            {"generate": "generator", "end": END},
        )

        return workflow.compile(checkpointer=rt.checkpointer)
