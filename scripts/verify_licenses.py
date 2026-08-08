"""Confronta o registro de modelos com o que a máquina realmente consegue carregar.

Roda sem o servidor de pé: consulta o Ollama por HTTP se ele estiver no ar e lê os
perfis de modelo do disco. O que estiver carregável e não declarado sai como falha,
com nome — porque a lacuna que ninguém consegue nomear é a que nunca é fechada.

Uso:  python scripts/verify_licenses.py [--evidencia]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "source" / "backend"))

from cinenode.registry_models import ModelRegistry  # noqa: E402


def modelos_do_ollama() -> list[str]:
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        return [m.get("name", "") for m in dados.get("models", []) if m.get("name")]
    except Exception:
        return []


def modelos_dos_perfis() -> list[str]:
    """Dois nomes para a mesma coisa, e ambos precisam estar cobertos.

    O peso aparece no disco como arquivo (`flux1-schnell-Q4_K_S.gguf`) e no app como
    perfil (`flux-fast-quantized`). Checar só um dos dois deixa metade da superfície
    fora — foi o que a rota ao vivo pegou e este script, na primeira versão, não.
    """
    encontrados: list[str] = []
    for arquivo in (RAIZ / "data" / "models").rglob("*"):
        if arquivo.suffix.lower() in {".gguf", ".safetensors", ".ckpt", ".pth", ".task", ".bin"}:
            encontrados.append(arquivo.stem)

    import os

    from cinenode.config import AppConfig
    from cinenode.store import _default_model_profiles

    os.environ.setdefault("CINENODE_HOME", str(RAIZ / "data"))
    encontrados += list(_default_model_profiles(AppConfig.from_env()).keys())
    return encontrados


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidencia", action="store_true",
                        help="grava docs/evidence/licencas/modelos.json")
    parser.add_argument("--slots", default="",
                        help="prefixos de slot separados por virgula; vazio olha tudo")
    parser.add_argument("--modulo", default="",
                        help="nome do modulo, usado so para nomear o arquivo de evidencia")
    args = parser.parse_args()

    slots = [s for s in args.slots.split(",") if s.strip()]
    em_uso = modelos_do_ollama() + modelos_dos_perfis()
    registro = ModelRegistry(RAIZ / "data" / "models", slots)
    relatorio = registro.relatorio(em_uso)

    print(f"escopo: {', '.join(relatorio['escopo'])}")
    print(f"registrados: {relatorio['total_registrado']}  "
          f"autorizados: {relatorio['autorizados']}")

    if relatorio["pendentes"]:
        print(f"\nPENDENTES ({len(relatorio['pendentes'])}) — declarados, sem licença resolvida:")
        for item in relatorio["pendentes"]:
            print(f"  - {item['id']}: {item['o_que_falta']}")
            print(f"    origem: {item['origem']}")

    if relatorio["nao_registrados"]:
        print(f"\nNAO REGISTRADOS ({len(relatorio['nao_registrados'])}) — carregáveis, "
              f"ninguém declarou:")
        for nome in relatorio["nao_registrados"]:
            print(f"  - {nome}")

    if args.evidencia:
        nome = f"{args.modulo or 'global'}.json"
        destino = RAIZ / "docs" / "evidence" / "licencas" / nome
        registro.gravar_evidencia(destino, em_uso)
        print(f"\nevidencia: {destino.relative_to(RAIZ)}")

    faltando = len(relatorio["pendentes"]) + len(relatorio["nao_registrados"])
    if faltando:
        print(f"\nFAIL: {faltando} modelos sem licença declarada.")
        return 1
    print("\nPASS: todo modelo carregável tem origem e licença declaradas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
