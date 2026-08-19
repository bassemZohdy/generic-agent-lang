"""Pydantic V2 configuration schemas for generic-agent-lang."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class RoleConfig(BaseModel):
    """Per-role configuration override."""

    instruction: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[str]] = None


class ModelConfig(BaseModel):
    """Model provider and endpoint configuration."""

    provider: str = "openai"
    name: str = "gpt-4o"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    streaming: bool = True
    model_kwargs: Dict[str, Any] = Field(default_factory=dict)


class InstructionsConfig(BaseModel):
    """Agent instructions configuration."""

    value: str = ""
    file: Optional[str] = None


class ToolsMcpConfig(BaseModel):
    """MCP tools configuration."""

    enabled: bool = False
    tools: List[str] = Field(default_factory=list)
    prefix: str = "mcp_"
    server_path: Optional[str] = None


class ToolsOpenApiConfig(BaseModel):
    """OpenAPI toolset configuration."""

    enabled: bool = False
    url: str = ""
    path: str = "/status"
    title: str = "Service API"
    prefix: str = "api_"


class ToolsSkillsConfig(BaseModel):
    """Skills tools configuration."""

    enabled: bool = False
    dir: str = ""
    prefix: str = ""


class ToolsConfig(BaseModel):
    """Enabled tools and toolset configuration."""

    enabled: List[str] = Field(default_factory=list)
    mcp: Optional[ToolsMcpConfig] = None
    openapi: Optional[ToolsOpenApiConfig] = None
    skills: Optional[ToolsSkillsConfig] = None


class ExecutionCodeExecutionConfig(BaseModel):
    """Code execution sandbox configuration."""

    strategy: str = ""
    docker_host: str = ""
    docker_image: str = ""
    vertex_resource: str = ""
    agent_engine_resource: str = ""
    gke_kubeconfig_path: str = ""
    gke_kubeconfig_context: str = ""


class ExecutionConfig(BaseModel):
    """Execution runtime parameters."""

    max_iterations: int = Field(default=3, ge=1)
    require_approval: bool = False
    steps: Optional[int] = Field(default=None, ge=1)
    workers: Optional[int] = Field(default=None, ge=1)
    specialists: List[str] = Field(default_factory=list)
    code_execution: Optional[ExecutionCodeExecutionConfig] = None


class OutputConfig(BaseModel):
    """Agent output schema configuration."""

    schema_name: Optional[str] = Field(default=None, alias="schema")
    key: Optional[str] = "last_response"

    class Config:
        populate_by_name = True


class StateConfig(BaseModel):
    """Agent state persistence configuration."""

    enabled: bool = True
    checkpointer: Optional[str] = "memory"  # memory, sqlite, postgres


class AgentConfig(BaseModel):
    """Complete agent configuration parsed from YAML or environment."""

    use_case: str = "assistant"
    name: str = ""
    description: str = ""
    model: Optional[ModelConfig] = None
    instructions: Optional[InstructionsConfig] = None
    tools: Optional[ToolsConfig] = None
    execution: Optional[ExecutionConfig] = None
    output: Optional[OutputConfig] = None
    state: Optional[StateConfig] = None
    roles: Dict[str, RoleConfig] = Field(default_factory=dict)

    @field_validator("use_case")
    @classmethod
    def validate_use_case(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("agent.use_case is required")
        return v.strip().lower()

    def validate_runtime(self) -> None:
        """Validate structural configuration."""
        if not self.use_case:
            raise ValueError("agent.use_case is required")
        if self.execution:
            if self.execution.max_iterations < 1:
                raise ValueError("execution.max_iterations must be >= 1")
            if self.execution.steps is not None and self.execution.steps < 1:
                raise ValueError("execution.steps must be >= 1")
            if self.execution.workers is not None and self.execution.workers < 1:
                raise ValueError("execution.workers must be >= 1")
