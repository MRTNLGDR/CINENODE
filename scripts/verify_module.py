"""GATE-FUNC: verifica que os nós prometidos por um módulo existem de verdade.

"Existe" aqui não é aparecer numa lista. É: estar no catálogo, ter rótulo e
descrição, declarar portas, ter todos os campos com controle visual, e ter um
executor registrado no motor. Um nó sem executor é um botão que não faz nada.

Uso:
    python scripts/verify_module.py M-14
    python scripts/verify_module.py --todos
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "source" / "backend"))

from cinenode.modules import MODULOS  # noqa: E402
from cinenode.workflow import CATALOG_BY_TYPE  # noqa: E402


def tipos_com_executor() -> set[str]:
    """Lê o despacho real de `_execute_node`.

    O executor não vive num registry: é uma cadeia de `if node.type == "..."`.
    Ler o código é a única forma honesta de saber quem tem implementação — uma
    lista escrita à mão divergiria na primeira adição de nó.
    """
    fonte = (RAIZ / "source/backend/cinenode/workflow.py").read_text(encoding="utf-8")
    return set(re.findall(r'node\.type\s*==\s*"([^"]+)"', fonte))

UI_VISUAIS = {"chips", "ratio", "seed", "picker", "slider"}
TIPOS_VISUAIS_POR_NATUREZA = {"textarea", "asset", "model_profile"}
TIPOS_TEXTO_LIVRE = {"text", "path", "json"}


def verificar_no(tipo: str) -> list[str]:
    """Devolve a lista de problemas. Lista vazia significa nó realmente entregue."""
    problemas: list[str] = []
    item = CATALOG_BY_TYPE.get(tipo)
    if not item:
        return [f"{tipo}: não está no catálogo"]

    if not item.get("label"):
        problemas.append(f"{tipo}: sem rótulo")
    if not item.get("description"):
        problemas.append(f"{tipo}: sem descrição")
    if not item.get("category"):
        problemas.append(f"{tipo}: sem categoria")
    if item.get("inputs") is None or item.get("outputs") is None:
        problemas.append(f"{tipo}: não declara portas")

    for campo in item.get("fields", []):
        if campo.get("ui") in UI_VISUAIS:
            continue
        if campo["type"] in TIPOS_VISUAIS_POR_NATUREZA | TIPOS_TEXTO_LIVRE:
            continue
        if campo["type"] == "number":
            continue
        problemas.append(f"{tipo}.{campo['key']}: campo tipo {campo['type']} sem controle visual")

    if tipo not in tipos_com_executor():
        problemas.append(f"{tipo}: sem executor registrado — é um botão que não faz nada")

    return problemas


def verificar_modulo(modulo_id: str) -> dict:
    modulo = next((m for m in MODULOS if m.id == modulo_id), None)
    if not modulo:
        return {"status": "FAIL", "summary": f"módulo desconhecido: {modulo_id}", "problemas": []}

    if not modulo.nos:
        # Módulo de infraestrutura não entrega nó; o gate dele é a suíte.
        return {"status": "PASS", "summary": "módulo sem nós declarados (infraestrutura)",
                "nos_verificados": 0, "problemas": []}

    problemas: list[str] = []
    for tipo in modulo.nos:
        problemas.extend(verificar_no(tipo))

    if problemas:
        return {"status": "FAIL",
                "summary": f"{len(problemas)} problema(s) em {len(modulo.nos)} nó(s)",
                "nos_verificados": len(modulo.nos), "problemas": problemas}
    return {"status": "PASS",
            "summary": f"{len(modulo.nos)} nó(s) com rótulo, portas, campos visuais e executor",
            "nos_verificados": len(modulo.nos), "problemas": []}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modulo", nargs="?", help="ID do módulo, ex.: M-14")
    parser.add_argument("--todos", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.todos:
        resultados = {m.id: verificar_modulo(m.id) for m in MODULOS}
        falhas = {k: v for k, v in resultados.items() if v["status"] != "PASS"}
        if args.json:
            print(json.dumps(resultados, ensure_ascii=False, indent=2))
        else:
            for mid, r in resultados.items():
                print(f"  {mid:<6} {r['status']:<5} {r['summary']}")
                for p in r["problemas"][:5]:
                    print(f"           {p}")
        return 1 if falhas else 0

    if not args.modulo:
        parser.error("informe o módulo ou use --todos")
    resultado = verificar_modulo(args.modulo)
    print(json.dumps(resultado, ensure_ascii=False, indent=2) if args.json
          else f"{resultado['status']}: {resultado['summary']}")
    for p in resultado["problemas"]:
        print(f"  {p}")
    return 0 if resultado["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
