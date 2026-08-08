"""Avalia os módulos, grava a evidência de cada gate e imprime o painel.

Uso:
    python scripts/governance_report.py                 # lê evidência existente
    python scripts/governance_report.py --executar      # roda os comandos e grava evidência
    python scripts/governance_report.py --json          # saída para máquina
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "source" / "backend"))

from cinenode.modules import MODULOS, ModuleRegistry  # noqa: E402
from cinenode.workflow import NODE_CATALOG  # noqa: E402

BARRA = 34
SIMBOLO = {"CONCLUIDO": "OK ", "EM_PROGRESSO": "...", "BLOQUEADO": "BLQ",
           "REGREDIU": "REG", "PARCIAL": "   "}


def executar_gates(registro: ModuleRegistry) -> int:
    """Roda o comando de cada gate distinto uma vez e grava a evidência de todos.

    Comandos se repetem entre módulos; executar N vezes o mesmo `pytest -q` só
    gastaria tempo. O resultado é reaproveitado por comando.
    """
    cache: dict[str, tuple[str, str]] = {}
    gravados = 0
    for modulo in MODULOS:
        for gate in modulo.gates:
            if gate.command not in cache:
                processo = subprocess.run(gate.command, shell=True, cwd=RAIZ,
                                          capture_output=True, text=True, timeout=900)
                saida = ((processo.stdout or "") + (processo.stderr or "")).strip()
                linhas = [linha for linha in saida.splitlines() if linha.strip()]
                cache[gate.command] = (
                    "PASS" if processo.returncode == 0 else "FAIL",
                    (linhas[-1] if linhas else "sem saída")[:160],
                )
                print(f"  {gate.command:<45} {cache[gate.command][0]}")
            status, resumo = cache[gate.command]
            registro.gravar_evidencia(modulo.id, gate.id, status, resumo)
            gravados += 1
    return gravados


def imprimir(relatorio: dict) -> None:
    print()
    print(f"GOVERNANÇA — {relatorio['total']} módulos · "
          f"{relatorio['concluidos']} concluídos · {relatorio['progresso_geral']}%")
    print()
    fase_atual = None
    for modulo in relatorio["modulos"]:
        if modulo["fase"] != fase_atual:
            fase_atual = modulo["fase"]
            info = relatorio["fases"][fase_atual]
            marca = " [FASE COMPLETA]" if info["completa"] else ""
            print(f"\nFASE {fase_atual} — {info['titulo']}  "
                  f"({info['concluidos']}/{info['modulos']}){marca}")
        cheio = int(modulo["progresso"] / 100 * BARRA)
        barra = "#" * cheio + "." * (BARRA - cheio)
        print(f"  {SIMBOLO.get(modulo['estado'], '?')} {modulo['id']:<6} "
              f"{modulo['titulo'][:26]:<27} {barra} {modulo['progresso']:>3}%  "
              f"{modulo['gates_ok']}/{modulo['gates_total']} gates")
        if modulo["nos_faltando"]:
            print(f"          nós ainda não entregues: {', '.join(modulo['nos_faltando'])}")
        if modulo["bloqueio"]:
            print(f"          bloqueio: {modulo['bloqueio']}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executar", action="store_true",
                        help="roda os comandos dos gates e grava a evidência")
    parser.add_argument("--json", action="store_true", help="saída em JSON")
    args = parser.parse_args()

    registro = ModuleRegistry(RAIZ, NODE_CATALOG)
    if args.executar:
        print("Executando os gates e gravando evidência...")
        total = executar_gates(registro)
        print(f"  {total} arquivos de evidência gravados em docs/evidence/")

    relatorio = registro.relatorio()
    if args.json:
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    else:
        imprimir(relatorio)
    # Sair com erro quando houver módulo regredido: o CI precisa notar.
    return 1 if any(m["estado"] == "REGREDIU" for m in relatorio["modulos"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
