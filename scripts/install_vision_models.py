"""Baixa e verifica os pesos de visão usados pelos nós de controle visual.

Regra do projeto: peso sem hash conferido não entra em produção. O download grava
num arquivo temporário, calcula o sha256, e só então promove para o destino final —
um download interrompido nunca vira um peso corrompido em uso.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Peso:
    id: str
    arquivo: str
    url: str
    bytes_esperados: int
    licenca: str
    origem: str
    descricao: str
    # sha256 fica vazio na primeira execução: o script imprime o valor observado
    # para ser fixado aqui depois da conferência manual.
    sha256: str = ""


CATALOGO: dict[str, Peso] = {
    "depth-anything-v2-small": Peso(
        id="depth-anything-v2-small",
        arquivo="depth_anything_v2_vits.onnx",
        url="https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx",
        bytes_esperados=99_000_000,     # tolerância verificada abaixo
        licenca="Apache-2.0 (código) — conferir termos do peso no card do modelo",
        origem="onnx-community/depth-anything-v2-small",
        descricao="Depth Anything V2 Small exportado para ONNX. Roda em CPU.",
        sha256="afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c",
    ),
}


def sha256_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as handle:
        for bloco in iter(lambda: handle.read(1 << 20), b""):
            digest.update(bloco)
    return digest.hexdigest()


def baixar(peso: Peso, destino: Path, *, forcar: bool = False) -> dict:
    destino.parent.mkdir(parents=True, exist_ok=True)
    final = destino
    if final.exists() and not forcar:
        atual = sha256_arquivo(final)
        if peso.sha256 and atual != peso.sha256:
            return {"estado": "HASH_DIVERGENTE", "arquivo": str(final),
                    "esperado": peso.sha256, "encontrado": atual}
        return {"estado": "JA_INSTALADO", "arquivo": str(final),
                "bytes": final.stat().st_size, "sha256": atual}

    temporario = final.with_suffix(final.suffix + ".parcial")
    print(f"  baixando {peso.id} de {peso.origem}...")
    try:
        requisicao = urllib.request.Request(
            peso.url, headers={"User-Agent": "CineNode/0.4 (local install script)"})
        with urllib.request.urlopen(requisicao, timeout=120) as resposta, temporario.open("wb") as saida:
            total = int(resposta.headers.get("Content-Length") or 0)
            baixado = 0
            while bloco := resposta.read(1 << 20):
                saida.write(bloco)
                baixado += len(bloco)
                if total:
                    print(f"\r    {baixado / 1e6:7.1f} / {total / 1e6:.1f} MB", end="", flush=True)
            print()
    except urllib.error.HTTPError as exc:
        temporario.unlink(missing_ok=True)
        return {"estado": "HTTP_ERRO", "codigo": exc.code, "url": peso.url,
                "como_corrigir": "Confira a URL no card do modelo; ela pode ter mudado de caminho."}
    except Exception as exc:  # noqa: BLE001 - rede falha de muitas formas
        temporario.unlink(missing_ok=True)
        return {"estado": "REDE_ERRO", "detalhe": str(exc)[:200],
                "como_corrigir": "Verifique a conexão e rode de novo; o download recomeça do zero."}

    tamanho = temporario.stat().st_size
    if tamanho < 1_000_000:
        conteudo = temporario.read_bytes()[:200]
        temporario.unlink(missing_ok=True)
        return {"estado": "ARQUIVO_SUSPEITO", "bytes": tamanho,
                "inicio": conteudo.decode("utf-8", "replace"),
                "como_corrigir": "O servidor devolveu uma página em vez do peso."}

    observado = sha256_arquivo(temporario)
    if peso.sha256 and observado != peso.sha256:
        temporario.unlink(missing_ok=True)
        return {"estado": "HASH_DIVERGENTE", "esperado": peso.sha256, "encontrado": observado,
                "como_corrigir": "O arquivo baixado não é o esperado. Não foi instalado."}

    temporario.replace(final)
    return {"estado": "INSTALADO", "arquivo": str(final), "bytes": tamanho,
            "sha256": observado, "licenca": peso.licenca, "origem": peso.origem}


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala pesos de visão do CineNode.")
    parser.add_argument("--model", action="append", help="ID do peso; repita para vários.")
    parser.add_argument("--all", action="store_true", help="Instala todos os pesos do catálogo.")
    parser.add_argument("--force", action="store_true", help="Rebaixa mesmo se já existir.")
    parser.add_argument("--list", action="store_true", help="Só lista o catálogo.")
    parser.add_argument("--models-dir", default=os.getenv("CINENODE_MODELS_DIR", str(RAIZ / "data" / "models")))
    args = parser.parse_args()

    if args.list or (not args.model and not args.all):
        print("Pesos de visão disponíveis:\n")
        for peso in CATALOGO.values():
            print(f"  {peso.id}")
            print(f"    {peso.descricao}")
            print(f"    origem  : {peso.origem}")
            print(f"    licença : {peso.licenca}")
            print(f"    arquivo : vision/{peso.arquivo}\n")
        print("Instale com: python scripts/install_vision_models.py --model depth-anything-v2-small")
        return 0

    alvos = list(CATALOGO) if args.all else (args.model or [])
    destino_base = Path(args.models_dir) / "vision"
    relatorio = []
    falhou = False
    for identificador in alvos:
        peso = CATALOGO.get(identificador)
        if not peso:
            print(f"  peso desconhecido: {identificador}")
            falhou = True
            continue
        resultado = baixar(peso, destino_base / peso.arquivo, forcar=args.force)
        resultado["id"] = identificador
        relatorio.append(resultado)
        marca = "ok" if resultado["estado"] in {"INSTALADO", "JA_INSTALADO"} else "FALHOU"
        print(f"  [{marca}] {identificador}: {resultado['estado']}")
        if resultado["estado"] == "INSTALADO":
            print(f"          sha256 {resultado['sha256']}")
            print(f"          {resultado['bytes'] / 1e6:.1f} MB em {resultado['arquivo']}")
        if marca == "FALHOU":
            falhou = True
            for chave in ("como_corrigir", "detalhe", "codigo", "encontrado"):
                if chave in resultado:
                    print(f"          {chave}: {resultado[chave]}")

    destino_base.mkdir(parents=True, exist_ok=True)
    (destino_base / "install-report.json").write_text(
        json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
