from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cinenode.engines.base import EngineAdapter
from cinenode.nodes import NodeSpec


@dataclass(frozen=True, slots=True)
class Plugin:
    id: str
    version: str
    nodes: tuple[NodeSpec, ...] = ()
    engines: tuple[EngineAdapter, ...] = ()

PluginFactory = Callable[[], Plugin]
