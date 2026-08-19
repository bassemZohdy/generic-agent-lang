"""State definitions for LangGraph agent workflows."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, Sequence, Union
from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.graph.message import add_messages


def merge_dicts(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reducer that merges concurrent dictionary updates into one state dictionary."""
    res = dict(a or {})
    if b:
        res.update(b)
    return res


class AgentState(TypedDict, total=False):
    """Unified state schema for all generic-agent-lang state graphs.

    Compatible with LangGraph's message reducers and adds rich workflow tracking.
    """

    # Core message history with standard LangGraph append/update reducer
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Shared execution context and variables
    context: Dict[str, Any]

    # Current step or iteration index
    current_step: int

    # Maximum iterations allowed for loop/evaluator graphs
    max_iterations: int

    # Intermediate steps/results from tools or sub-agents (reducer appends)
    intermediate_steps: List[Dict[str, Any]]

    # Step-by-step plan for planner-executor graphs
    plan: List[str]

    # Evaluation output and score for evaluator-optimizer graphs
    evaluation: Dict[str, Any]

    # Human-in-the-loop approval status ("pending", "approved", "rejected")
    approval_status: str

    # Specialist routing decision
    target_specialist: str

    # Output from individual worker subgraphs (supports concurrent fan-out merge)
    worker_outputs: Annotated[Dict[str, Any], merge_dicts]

    # Final response or structured output
    last_response: Union[str, Dict[str, Any], None]


class AgentInput(TypedDict, total=False):
    """Input payload accepted by the agent graph."""

    messages: Sequence[BaseMessage]
    context: Optional[Dict[str, Any]]


class AgentOutput(TypedDict, total=False):
    """Output payload produced by the agent graph."""

    messages: Sequence[BaseMessage]
    last_response: Union[str, Dict[str, Any], None]
    intermediate_steps: Optional[List[Dict[str, Any]]]
