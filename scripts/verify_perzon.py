"""GATE da Fase E: lê o catálogo real do PERZON e reporta o que ele diz de si mesmo.

O PERZON declara 1697 microitens e afirma, no próprio `00_MASTER_SPEC.md`:

    "O inventário é catálogo-alvo. Esta entrega transforma o catálogo em contratos
     executáveis e navegáveis; não afirma que os algoritmos de produção estejam
     implementados."

Este verificador existe para que essa frase apareça no painel em vez de ficar
enterrada num markdown. Ele não julga o PERZON — ele repete o que o banco diz.

Uso:
    python scripts/verify_perzon.py M-34
    python scripts/verify_perzon.py --resumo
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "source" / "backend"))

# O motor local implementa parte dos contratos. Sem contar isso, o gate repetiria
# para sempre "specified_not_implemented" mesmo depois de o algoritmo existir.
try:
    from cinenode.perzon.registry import POR_FEATURE as IMPLEMENTADOS_LOCAIS
except Exception:   # noqa: BLE001 — o verificador precisa rodar sem o pacote
    IMPLEMENTADOS_LOCAIS = {}

# O PERZON vive fora deste repositório. O caminho é configurável; sem ele, o gate
# devolve BLOCKED com a instrução — nunca PASS por omissão.
PERZON_PADRAO = Path(
    r"D:\AIIA\01-apps-canonicos\11-pezon\PERZON_TOTAL_SPEC_V2\PERZON_TOTAL_SPEC_V2"
)

# Cada módulo da Fase E cobre um conjunto de workspaces do PERZON.
COBERTURA: dict[str, dict[str, object]] = {
    "M-34": {"titulo": "DNA HUMANO", "modulos": ["character", "headshot", "face"]},
    "M-35": {"titulo": "SUPERFÍCIE HUMANA", "modulos": ["material", "mesh", "sculpt"]},
    "M-36": {"titulo": "RIG E FACE", "modulos": ["rig"]},
    "M-37": {"titulo": "MOCAP E MOVIMENTO", "modulos": ["motion"]},
    "M-38": {"titulo": "CABELO E VESTUÁRIO", "modulos": ["hair", "garment"]},
    "M-39": {"titulo": "VOZ DO PERSONAGEM", "modulos": ["voice"]},
    "M-40": {"titulo": "ENTREGA DE PERSONAGEM", "modulos": ["formats", "connectors", "game"]},
}

# O que conta como implementado no vocabulário do PERZON.
STATUS_PRONTO = {"implemented", "verified", "done"}


def raiz_perzon() -> Path | None:
    caminho = Path(os.environ.get("PERZON_ROOT", PERZON_PADRAO))
    return caminho if (caminho / "registry" / "feature_catalog.sqlite").is_file() else None


def ler_catalogo(base: Path) -> dict[str, dict[str, int]]:
    """Devolve, por workspace do PERZON, a contagem por status."""
    conexao = sqlite3.connect(f"file:{base / 'registry' / 'feature_catalog.sqlite'}?mode=ro", uri=True)
    try:
        por_modulo: dict[str, dict[str, int]] = {}
        for modulo, status, total in conexao.execute(
            "SELECT module, status, COUNT(*) FROM features GROUP BY module, status"
        ):
            por_modulo.setdefault(modulo, {})[status] = total
        return por_modulo
    finally:
        conexao.close()


def implementados_por_workspace(base: Path) -> dict[str, list[str]]:
    """Quais `feature_id` do catálogo têm cálculo real no motor local.

    Casa pelo id exato: um id do registro local que não exista no catálogo do
    PERZON seria implementação de algo que ninguém especificou, e isso precisa
    aparecer como erro em vez de inflar a contagem.
    """
    if not IMPLEMENTADOS_LOCAIS:
        return {}
    conexao = sqlite3.connect(
        f"file:{base / 'registry' / 'feature_catalog.sqlite'}?mode=ro", uri=True)
    try:
        por_workspace: dict[str, list[str]] = {}
        for feature_id in IMPLEMENTADOS_LOCAIS:
            linha = conexao.execute(
                "SELECT module FROM features WHERE id = ?", (feature_id,)).fetchone()
            if linha:
                por_workspace.setdefault(linha[0], []).append(feature_id)
        return por_workspace
    finally:
        conexao.close()


def verificar(modulo_id: str) -> dict:
    cobertura = COBERTURA.get(modulo_id)
    if not cobertura:
        return {"status": "FAIL", "summary": f"{modulo_id} não é um módulo da Fase E"}

    base = raiz_perzon()
    if not base:
        return {
            "status": "BLOCKED",
            "summary": "catálogo do PERZON não encontrado",
            "como_corrigir": "Defina PERZON_ROOT apontando para a pasta que contém "
                             "registry/feature_catalog.sqlite",
            "caminho_procurado": str(PERZON_PADRAO),
        }

    catalogo = ler_catalogo(base)
    locais = implementados_por_workspace(base)
    alvos = list(cobertura["modulos"])
    ausentes = [nome for nome in alvos if nome not in catalogo]
    total = 0
    prontos = 0
    detalhe: dict[str, dict[str, int]] = {}
    implementados_aqui = 0
    for nome in alvos:
        contagens = dict(catalogo.get(nome, {}))
        aqui = len(locais.get(nome, []))
        if aqui:
            # Move do balde "não implementado" para o de implementado local. O
            # PERZON continua dizendo que não implementou — e é verdade, lá.
            contagens["implementado_local"] = aqui
            contagens["specified_not_implemented"] = max(
                0, contagens.get("specified_not_implemented", 0) - aqui)
        detalhe[nome] = contagens
        implementados_aqui += aqui
        total += sum(contagens.values())
        prontos += sum(n for st, n in contagens.items()
                       if st in STATUS_PRONTO or st == "implementado_local")

    if not total:
        return {
            "status": "BLOCKED",
            "summary": f"nenhum microitem para {', '.join(alvos)}",
            "workspaces_ausentes": ausentes,
            "como_corrigir": "Confira os nomes de workspace contra o catálogo do PERZON.",
        }

    if prontos == total:
        return {"status": "PASS",
                "summary": f"{total} microitens implementados em {len(alvos)} workspace(s)",
                "total": total, "prontos": prontos, "por_workspace": detalhe}

    return {
        "status": "BLOCKED",
        "summary": f"{prontos}/{total} microitens implementados — o PERZON declara "
                   f"o restante como specified_not_implemented",
        "total": total,
        "prontos": prontos,
        "por_workspace": detalhe,
        "implementado_local": implementados_aqui,
        "operacoes_locais": sorted(
            fid for nome in alvos for fid in locais.get(nome, [])),
        "como_corrigir": "Os contratos existem; falta algoritmo. O que já calcula "
                         "está em cinenode.perzon e aparece em "
                         "/api/perzon/operacoes.",
    }


def resumo() -> dict:
    base = raiz_perzon()
    if not base:
        return {"status": "BLOCKED", "summary": "catálogo do PERZON não encontrado",
                "caminho_procurado": str(PERZON_PADRAO)}
    catalogo = ler_catalogo(base)
    por_status: dict[str, int] = {}
    for contagens in catalogo.values():
        for status, total in contagens.items():
            por_status[status] = por_status.get(status, 0) + total
    total = sum(por_status.values())
    prontos = sum(n for st, n in por_status.items() if st in STATUS_PRONTO)
    return {
        "raiz": str(base),
        "workspaces": len(catalogo),
        "microitens": total,
        "implementados": prontos,
        "por_status": dict(sorted(por_status.items(), key=lambda kv: -kv[1])),
        "cobertura_fase_e": {
            mid: sorted(set(c["modulos"]) & set(catalogo)) for mid, c in COBERTURA.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modulo", nargs="?", help="ID do módulo, ex.: M-34")
    parser.add_argument("--resumo", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.resumo:
        dados = resumo()
        if args.json:
            print(json.dumps(dados, ensure_ascii=False, indent=2))
        else:
            if "erro" in dados or dados.get("status") == "BLOCKED":
                print(f"BLOQUEADO: {dados['summary']}")
                print(f"  procurei em: {dados.get('caminho_procurado')}")
                return 1
            print(f"PERZON em {dados['raiz']}")
            print(f"  {dados['microitens']} microitens em {dados['workspaces']} workspaces")
            print(f"  implementados: {dados['implementados']}")
            for status, total in dados["por_status"].items():
                print(f"    {status:<32} {total}")
            print("  cobertura da Fase E:")
            for mid, mods in dados["cobertura_fase_e"].items():
                titulo = COBERTURA[mid]["titulo"]
                print(f"    {mid} {titulo:<24} {', '.join(mods) or '(sem workspace)'}")
        return 0

    if not args.modulo:
        parser.error("informe o módulo ou use --resumo")
    resultado = verificar(args.modulo)
    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        print(f"{resultado['status']}: {resultado['summary']}")
        if resultado.get("como_corrigir"):
            print(f"  {resultado['como_corrigir']}")
    return 0 if resultado["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
