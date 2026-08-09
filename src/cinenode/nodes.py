from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
import asyncio
import json

NodeHandler = Callable[[dict[str, Any], dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class NodeSpec:
    type: str
    category: str
    label: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ("value",)
    cacheable: bool = True
    handler: NodeHandler | None = field(default=None, compare=False, repr=False)


class NodeRegistry:
    def __init__(self) -> None:
        self._items: dict[str, NodeSpec] = {}

    def register(self, spec: NodeSpec) -> None:
        if spec.type in self._items:
            raise ValueError(f"duplicate node type: {spec.type}")
        self._items[spec.type] = spec

    def get(self, node_type: str) -> NodeSpec:
        try:
            return self._items[node_type]
        except KeyError as exc:
            raise ValueError(f"unknown node type: {node_type}") from exc

    def catalog(self) -> list[dict[str, Any]]:
        return [{"type":s.type,"category":s.category,"label":s.label,"inputs":list(s.inputs),"outputs":list(s.outputs),"cacheable":s.cacheable} for s in sorted(self._items.values(), key=lambda x:(x.category,x.label))]


async def _text(params: dict[str, Any], _: dict[str, Any]) -> str:
    return str(params.get("text", ""))

async def _constant(params: dict[str, Any], _: dict[str, Any]) -> Any:
    return params.get("value")

async def _template(params: dict[str, Any], inputs: dict[str, Any]) -> str:
    values = {key:(json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else value) for key,value in inputs.items()}
    return str(params.get("template", "{input}")).format_map(_Safe(values))

async def _merge(_: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for value in inputs.values():
        if isinstance(value, dict):
            result.update(value)
    return result

async def _delay(params: dict[str, Any], inputs: dict[str, Any]) -> Any:
    await asyncio.sleep(max(0.0, min(float(params.get("seconds", 0)), 30.0)))
    return inputs.get("input")

async def _json_path(params: dict[str, Any], inputs: dict[str, Any]) -> Any:
    value = inputs.get("input")
    for part in str(params.get("path", "")).strip(".").split("."):
        if not part:
            continue
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value

class _Safe(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def builtin_registry() -> NodeRegistry:
    registry = NodeRegistry()
    for spec in (
        NodeSpec("input.text","Input","Text",outputs=("text",),handler=_text),
        NodeSpec("data.constant","Data","Constant",handler=_constant),
        NodeSpec("transform.template","Transform","Template",inputs=("input",),handler=_template),
        NodeSpec("transform.json_path","Transform","JSON path",inputs=("input",),handler=_json_path),
        NodeSpec("data.merge","Data","Merge",inputs=("items",),handler=_merge),
        NodeSpec("control.delay","Control","Delay",inputs=("input",),cacheable=False,handler=_delay),
        NodeSpec("inference.chat","Inference","Chat",inputs=("prompt",),cacheable=False),
        NodeSpec("inference.comfyui","Inference","ComfyUI",inputs=("workflow",),cacheable=False),
        NodeSpec("output.text_file","Output","Text file",inputs=("input",),cacheable=False),
    ):
        registry.register(spec)
    return registry
