"""Fase E executável: os contratos do PERZON com algoritmo de verdade por trás.

O PERZON declara 1697 microitens e entrega 1697 stubs em Rust que devolvem
`specified_not_implemented`. O contrato está exato; o cálculo nunca existiu.

Decisão registrada (ADR-008): a implementação vive aqui, em Python, e não no
repositório Rust. Três razões medidas, não estéticas:

1. O gargalo desta máquina é VRAM — 16.376 MiB, com pico medido de 15.752 MiB no
   job de vídeo. Esse teto não muda com a linguagem. Reescrever em Rust otimizaria
   o que não é o gargalo.
2. O CineNode já tem fila de jobs, registro de assets, banco com migração, UI e
   telemetria. A Fase E precisa disso tudo; duplicar em outro processo criaria
   dois donos para o mesmo estado.
3. `trimesh`, `scipy`, `numpy` e `open3d` cobrem a geometria com código já testado
   por terceiros. Reimplementar decimação e suavização laplaciana em Rust seria
   escrever de novo, pior, o que já funciona.

O contrato do PERZON continua sendo a fonte: cada operação aqui casa com o
`feature_id` dele, e o verificador confronta os dois. Onde o cálculo real não
existir, a operação recusa com código — nunca devolve resultado inventado.
"""
from __future__ import annotations

from .engine import PerzonEngine, PerzonOperationError
from .registry import OPERACOES, OperacaoPerzon, operacoes_por_modulo

__all__ = [
    "OPERACOES",
    "OperacaoPerzon",
    "PerzonEngine",
    "PerzonOperationError",
    "operacoes_por_modulo",
]
