"""Domain response schemas and data transfer objects."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GenericAgentResponse(BaseModel):
    """Stable response envelope shared by all configured agent use cases."""

    answer: str = Field(description="The direct answer to the user's request.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence from 0.0 to 1.0.")
    evidence: List[str] = Field(default_factory=list, description="Citations, documents, or data evidence used.")
    risks: List[str] = Field(default_factory=list, description="Identified risks, caveats, or assumptions.")
    next_steps: List[str] = Field(default_factory=list, description="Recommended follow-up actions.")


class PlanStep(BaseModel):
    """One step in a multi-step plan."""

    step_number: int
    description: str
    assigned_worker: Optional[str] = None
    completed: bool = False
    result: Optional[str] = None


class PlanExecutionOutput(BaseModel):
    """Output from a planner-executor agent."""

    plan: List[PlanStep]
    final_summary: str


class EvaluationResult(BaseModel):
    """Output from an evaluator agent."""

    score: float = Field(ge=0.0, le=1.0, description="Quality score from 0.0 to 1.0.")
    is_acceptable: bool = Field(description="Whether the response meets acceptance criteria.")
    feedback: str = Field(description="Detailed critique and suggestions for improvement.")
    improvements: List[str] = Field(default_factory=list, description="Specific action items for refinement.")


class HumanApprovalPayload(BaseModel):
    """Payload presented to a human reviewer for approval."""

    action: str = Field(description="The proposed action requiring approval.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Parameters or details of the action.")
    requires_explicit_confirmation: bool = True
