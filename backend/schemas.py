from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NodePosition(BaseModel):
    x: float = 0
    y: float = 0


class WorkflowNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=100)
    position: NodePosition = Field(default_factory=NodePosition)
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=150)
    source: str
    target: str
    source_handle: str | None = None
    target_handle: str | None = None


class WorkflowGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = 1
    nodes: list[WorkflowNode] = Field(default_factory=list, max_length=500)
    edges: list[WorkflowEdge] = Field(default_factory=list, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    graph: WorkflowGraph = Field(default_factory=WorkflowGraph)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name cannot be blank")
        return value


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    graph: WorkflowGraph | None = None


class JobCreate(BaseModel):
    project_id: str | None = None
    graph: WorkflowGraph | None = None


class SettingsPatch(BaseModel):
    values: dict[str, Any]


class EngineTestRequest(BaseModel):
    engine_id: str


class BackupRequest(BaseModel):
    include_assets: bool = True
    include_outputs: bool = True


class RestoreRequest(BaseModel):
    backup_path: str
    replace_existing: bool = False


class GovernanceTaskPatch(BaseModel):
    status: Literal["PENDING", "DONE"]
    evidence: dict[str, Any] | None = None


class AgentMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class AgentChatRequest(BaseModel):
    messages: list[AgentMessage] = Field(min_length=1, max_length=40)
    graph: WorkflowGraph | None = None


class SnapshotCreate(BaseModel):
    label: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=2000)


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["library", "reference", "gallery"] = "library"
    description: str = Field(default="", max_length=2000)


class CollectionItem(BaseModel):
    asset_id: str = Field(min_length=1, max_length=120)
