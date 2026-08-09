from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from .catalog import BY_TYPE
from .config import Settings
from .db import Database
from .engines import EngineError, comfy_workflow, ffmpeg_transcode, ffprobe, image_info, ollama_chat
from .schemas import WorkflowGraph


class WorkflowError(RuntimeError):
    def __init__(self, code: str, message: str, *, node_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.node_id = node_id


class JobCancelled(WorkflowError):
    def __init__(self, message: str = "Job cancelado"):
        super().__init__("JOB_CANCELLED", message)


@dataclass(slots=True)
class ExecutionContext:
    settings: Settings
    db: Database
    job_id: str
    project_id: str
    run_inputs: dict[str, Any]
    cancelled: Callable[[], bool]
    event: Callable[[str, dict[str, Any]], None]

    def ensure_not_cancelled(self) -> None:
        if self.cancelled():
            raise JobCancelled()

    def register_file(self, relative_path: str, media_type: str = "application/octet-stream") -> dict[str, Any]:
        path = (self.settings.home / relative_path).resolve()
        if not path.is_file() or self.settings.home.resolve() not in path.parents:
            raise WorkflowError("ASSET_PATH_INVALID", f"Saída fora do workspace: {relative_path}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return self.db.create_asset(
            project_id=self.project_id,
            job_id=self.job_id,
            name=path.name,
            media_type=media_type,
            relative_path=str(path.relative_to(self.settings.home)),
            bytes_count=path.stat().st_size,
            sha256=digest.hexdigest(),
        )


def validate_graph(graph: WorkflowGraph) -> list[str]:
    errors: list[str] = []
    node_ids = [node.id for node in graph.nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("IDs de nós duplicados")
    nodes = {node.id: node for node in graph.nodes}
    for node in graph.nodes:
        if node.type not in BY_TYPE:
            errors.append(f"Tipo de nó desconhecido: {node.type}")
    edge_ids = [edge.id for edge in graph.edges]
    if len(edge_ids) != len(set(edge_ids)):
        errors.append("IDs de conexões duplicados")
    targets: set[tuple[str, str]] = set()
    adjacency: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    indegree = {node.id: 0 for node in graph.nodes}
    for edge in graph.edges:
        if edge.source not in nodes:
            errors.append(f"Origem inexistente: {edge.source}")
            continue
        if edge.target not in nodes:
            errors.append(f"Destino inexistente: {edge.target}")
            continue
        if edge.source == edge.target:
            errors.append(f"Auto-conexão não permitida: {edge.source}")
            continue
        source_spec = BY_TYPE.get(nodes[edge.source].type)
        target_spec = BY_TYPE.get(nodes[edge.target].type)
        if source_spec and edge.source_port not in source_spec.outputs:
            errors.append(f"Porta de saída inválida: {edge.source}.{edge.source_port}")
        if target_spec and edge.target_port not in target_spec.inputs:
            errors.append(f"Porta de entrada inválida: {edge.target}.{edge.target_port}")
        target_key = (edge.target, edge.target_port)
        if target_key in targets:
            errors.append(f"Mais de uma conexão na entrada: {edge.target}.{edge.target_port}")
        targets.add(target_key)
        adjacency.setdefault(edge.source, []).append(edge.target)
        indegree[edge.target] = indegree.get(edge.target, 0) + 1
    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        current = queue.pop(0)
        visited += 1
        for target in adjacency.get(current, []):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(nodes):
        errors.append("O workflow contém ciclo")
    return errors


def topological_order(graph: WorkflowGraph) -> list[str]:
    errors = validate_graph(graph)
    if errors:
        raise WorkflowError("INVALID_GRAPH", "; ".join(errors))
    adjacency: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    indegree = {node.id: 0 for node in graph.nodes}
    for edge in graph.edges:
        adjacency[edge.source].append(edge.target)
        indegree[edge.target] += 1
    queue = [node.id for node in graph.nodes if indegree[node.id] == 0]
    order: list[str] = []
    while queue:
        current = queue.pop(0)
        order.append(current)
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return order


def _input_value(node_id: str, params: dict[str, Any], context: ExecutionContext, key: str = "value") -> Any:
    override = context.run_inputs.get(node_id)
    if override is not None:
        if isinstance(override, dict) and key in override:
            return override[key]
        return override
    return params.get(key)


def _resolve_inputs(graph: WorkflowGraph, node_id: str, results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for edge in graph.edges:
        if edge.target != node_id:
            continue
        source_result = results.get(edge.source, {})
        if edge.source_port not in source_result:
            raise WorkflowError(
                "SOURCE_PORT_MISSING",
                f"{edge.source} não produziu a porta {edge.source_port}",
                node_id=node_id,
            )
        values[edge.target_port] = source_result[edge.source_port]
    return values


def _as_number(value: Any, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise WorkflowError("NUMBER_REQUIRED", f"{name} precisa ser numérico") from exc


def execute_node(node_type: str, node_id: str, params: dict[str, Any], inputs: dict[str, Any],
                 context: ExecutionContext) -> dict[str, Any]:
    context.ensure_not_cancelled()
    try:
        if node_type == "input.text":
            return {"value": str(_input_value(node_id, params, context) or "")}
        if node_type == "input.number":
            return {"value": _as_number(_input_value(node_id, params, context), "value")}
        if node_type == "input.json":
            value = _input_value(node_id, params, context)
            if isinstance(value, str):
                value = json.loads(value)
            return {"value": value}
        if node_type == "input.file":
            asset_id = str(_input_value(node_id, params, context, "asset_id") or params.get("asset_id") or "")
            asset = context.db.get_asset(asset_id)
            if not asset:
                raise WorkflowError("ASSET_NOT_FOUND", f"Asset não encontrado: {asset_id}", node_id=node_id)
            return {"path": asset["relative_path"]}
        if node_type == "text.template":
            template = str(params.get("template", "{value}"))
            try:
                return {"text": template.format_map(inputs)}
            except KeyError as exc:
                raise WorkflowError("TEMPLATE_VARIABLE_MISSING", f"Variável ausente: {exc.args[0]}", node_id=node_id) from exc
        if node_type == "text.concat":
            return {"text": str(inputs.get("a", "")) + str(params.get("separator", " ")) + str(inputs.get("b", ""))}
        if node_type == "math.add":
            return {"value": _as_number(inputs.get("a"), "a") + _as_number(inputs.get("b"), "b")}
        if node_type == "math.multiply":
            return {"value": _as_number(inputs.get("a"), "a") * _as_number(inputs.get("b"), "b")}
        if node_type == "logic.if":
            return {"value": inputs.get("when_true") if bool(inputs.get("condition")) else inputs.get("when_false")}
        if node_type == "data.merge":
            a = inputs.get("a") or {}
            b = inputs.get("b") or {}
            if not isinstance(a, dict) or not isinstance(b, dict):
                raise WorkflowError("OBJECT_REQUIRED", "data.merge requer dois objetos JSON", node_id=node_id)
            return {"value": {**a, **b}}
        if node_type == "util.delay":
            seconds = min(max(float(params.get("seconds", 1)), 0), 3600)
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                context.ensure_not_cancelled()
                time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
            return {"value": inputs.get("value")}
        if node_type == "media.image.info":
            return {"info": image_info(context.settings, str(inputs.get("path") or ""))}
        if node_type == "media.ffprobe":
            return {"info": ffprobe(context.settings, str(inputs.get("path") or ""))}
        if node_type == "media.ffmpeg.transcode":
            path = ffmpeg_transcode(
                context.settings,
                job_id=context.job_id,
                path_value=str(inputs.get("path") or ""),
                extension=str(params.get("extension") or ".mp4"),
                video_codec=str(params.get("video_codec") or "libx264"),
                audio_codec=str(params.get("audio_codec") or "aac"),
                cancel=context.cancelled,
                event=context.event,
            )
            context.register_file(path, "video/mp4")
            return {"path": path}
        if node_type == "ai.ollama.chat":
            return {"text": ollama_chat(str(inputs.get("prompt") or ""), params)}
        if node_type == "ai.comfy.workflow":
            return {"result": comfy_workflow(
                str(inputs.get("prompt") or ""), params, cancel=context.cancelled, event=context.event
            )}
        if node_type in {"output.text", "output.json"}:
            return {"value": inputs.get("value")}
        raise WorkflowError("UNKNOWN_NODE", f"Tipo de nó desconhecido: {node_type}", node_id=node_id)
    except WorkflowError:
        raise
    except EngineError as exc:
        if exc.code == "JOB_CANCELLED":
            raise JobCancelled(str(exc)) from exc
        raise WorkflowError(exc.code, str(exc), node_id=node_id) from exc
    except Exception as exc:
        raise WorkflowError("NODE_EXECUTION_FAILED", str(exc), node_id=node_id) from exc


def execute_graph(graph: WorkflowGraph, context: ExecutionContext) -> dict[str, Any]:
    order = topological_order(graph)
    nodes = {node.id: node for node in graph.nodes}
    results: dict[str, dict[str, Any]] = {}
    output_values: dict[str, Any] = {}
    context.event("workflow_started", {"nodes": len(order), "order": order})
    for index, node_id in enumerate(order, start=1):
        context.ensure_not_cancelled()
        node = nodes[node_id]
        inputs = _resolve_inputs(graph, node_id, results)
        context.db.set_job_state(context.job_id, "RUNNING", current_node_id=node_id)
        context.event("node_started", {"node_id": node_id, "type": node.type, "index": index, "total": len(order)})
        started = time.perf_counter()
        result = execute_node(node.type, node.id, node.params, inputs, context)
        json.dumps(result, ensure_ascii=False, default=str)
        results[node_id] = result
        if node.type.startswith("output."):
            output_values[node_id] = result.get("value")
        context.event("node_succeeded", {
            "node_id": node_id,
            "type": node.type,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "outputs": list(result),
        })
    payload = {"outputs": output_values, "nodes": results}
    context.event("workflow_succeeded", {"output_nodes": list(output_values)})
    return payload
