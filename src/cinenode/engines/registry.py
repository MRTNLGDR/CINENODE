from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any

from .base import EngineAdapter
from .http_adapters import ComfyUIEngine, MockEngine, OllamaEngine, OpenAICompatibleEngine


class EngineRegistry:
    def __init__(self) -> None:
        self._items: dict[str, EngineAdapter] = {}

    def register(self, engine: EngineAdapter) -> None:
        if engine.info.id in self._items:
            raise ValueError(f"duplicate engine: {engine.info.id}")
        self._items[engine.info.id]=engine

    def get(self, engine_id: str) -> EngineAdapter:
        try: return self._items[engine_id]
        except KeyError as exc: raise ValueError(f"unknown engine: {engine_id}") from exc

    def list(self) -> list[dict[str,Any]]:
        return [{"id":e.info.id,"label":e.info.label,"capabilities":list(e.info.capabilities),"local":e.info.local} for e in self._items.values()]

    def load_entry_points(self) -> list[str]:
        loaded=[]
        for point in entry_points(group="cinenode.engines"):
            engine=point.load()()
            if not isinstance(engine,EngineAdapter):
                raise TypeError(f"entry point {point.name} is not an EngineAdapter")
            self.register(engine); loaded.append(engine.info.id)
        return loaded


def builtin_engines(*, test_mode: bool=False, allow_private: bool=False) -> EngineRegistry:
    registry=EngineRegistry()
    registry.register(OllamaEngine(allow_private=allow_private))
    registry.register(OpenAICompatibleEngine(allow_private=allow_private))
    registry.register(ComfyUIEngine(allow_private=allow_private))
    if test_mode: registry.register(MockEngine())
    try: registry.load_entry_points()
    except Exception: pass
    return registry
