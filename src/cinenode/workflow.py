from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json

from .nodes import NodeRegistry
from .util import stable_hash


@dataclass(frozen=True, slots=True)
class CompiledWorkflow:
    nodes: dict[str, dict[str, Any]]
    order: tuple[str, ...]


def compile_workflow(definition: dict[str, Any], registry: NodeRegistry) -> CompiledWorkflow:
    raw_nodes = definition.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("workflow requires a non-empty nodes list")
    nodes: dict[str, dict[str, Any]] = {}
    for raw in raw_nodes:
        if not isinstance(raw, dict) or not raw.get("id") or not raw.get("type"):
            raise ValueError("each node requires id and type")
        node_id=str(raw["id"])
        if node_id in nodes:
            raise ValueError(f"duplicate node id: {node_id}")
        registry.get(str(raw["type"]))
        nodes[node_id]=raw
    indegree={node_id:0 for node_id in nodes}; outgoing={node_id:[] for node_id in nodes}
    for target,node in nodes.items():
        bindings=node.get("inputs",{}) or {}
        if not isinstance(bindings,dict):
            raise ValueError(f"inputs for {target} must be an object")
        dependencies=set()
        for binding in bindings.values():
            if isinstance(binding,dict) and "node" in binding:
                source=str(binding["node"])
                if source not in nodes:
                    raise ValueError(f"node {target} references missing node {source}")
                dependencies.add(source)
        for source in dependencies:
            outgoing[source].append(target); indegree[target]+=1
    queue=sorted(node_id for node_id,degree in indegree.items() if degree==0); order=[]
    while queue:
        current=queue.pop(0); order.append(current)
        for target in sorted(outgoing[current]):
            indegree[target]-=1
            if indegree[target]==0:
                queue.append(target); queue.sort()
    if len(order)!=len(nodes):
        raise ValueError("workflow contains a cycle")
    return CompiledWorkflow(nodes,tuple(order))


def resolve_inputs(node: dict[str, Any], outputs: dict[str, Any], job_input: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any]={}
    for name,binding in (node.get("inputs",{}) or {}).items():
        if isinstance(binding,dict) and "node" in binding:
            value=outputs[str(binding["node"])]
            path=binding.get("path")
            if path:
                for part in str(path).strip(".").split("."):
                    value=value[int(part)] if isinstance(value,list) else value[part]
            result[name]=value
        elif isinstance(binding,dict) and "job" in binding:
            result[name]=job_input.get(str(binding["job"]))
        else:
            result[name]=binding
    return result


def node_cache_key(node: dict[str, Any], inputs: dict[str, Any]) -> str:
    return stable_hash({"type":node["type"],"params":node.get("params",{}),"inputs":inputs,"revision":1})
