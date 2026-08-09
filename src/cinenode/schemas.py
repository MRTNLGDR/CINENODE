from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=128)
    x: float = 0
    y: float = 0
    params: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    source: str
    source_port: str = "value"
    target: str
    target_port: str = "value"


class WorkflowGraph(BaseModel):
    version: int = 1
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)


class WorkflowCreate(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=160)
    graph: WorkflowGraph


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    graph: WorkflowGraph | None = None


class RunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
