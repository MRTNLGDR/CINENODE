from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EngineInfo:
    id: str
    label: str
    capabilities: tuple[str, ...]
    local: bool = True


class EngineAdapter(ABC):
    info: EngineInfo

    @abstractmethod
    async def probe(self) -> dict[str, Any]: ...

    async def chat(self, prompt: str, params: dict[str, Any]) -> Any:
        raise NotImplementedError(f"{self.info.id} does not implement chat")

    async def run_workflow(self, workflow: dict[str, Any], params: dict[str, Any]) -> Any:
        raise NotImplementedError(f"{self.info.id} does not implement workflow execution")
