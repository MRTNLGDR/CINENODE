"""Indexador: o modelo pequeno que mantém a biblioteca organizada sozinho.

Ele olha o asset, decide o que ele é, dá um nome legível, escolhe categoria e
etiquetas, e grava tudo no `metadata` — sem mover nem renomear o arquivo no disco,
porque o caminho já está referenciado por jobs e grafos.

Roda em três situações: quando o usuário pede, quando um job termina, e no ocioso.
Nunca compete com uma geração: se houver job ativo, ele espera.
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .gateway import AIGateway, GatewayError
from .store import Store
from .util import utc_now

# Categorias fixas. Modelo pequeno inventa taxonomia se você deixar; aqui ele escolhe.
CATEGORIAS: dict[str, list[str]] = {
    "pessoa": ["retrato", "corpo inteiro", "grupo", "rosto"],
    "personagem": ["conceito", "turnaround", "expressão", "figurino"],
    "ambiente": ["interior", "exterior", "paisagem", "urbano", "natureza"],
    "arquitetura": ["fachada", "interior", "planta", "maquete", "detalhe"],
    "objeto": ["produto", "veículo", "mobiliário", "prop", "material"],
    "textura": ["basecolor", "normal", "roughness", "referência"],
    "cena": ["still", "storyboard", "key visual", "plano"],
    "abstrato": ["padrão", "gradiente", "ruído", "estudo"],
    "documento": ["planta baixa", "diagrama", "texto", "tabela"],
    "malha3d": ["objeto", "personagem", "ambiente", "peça"],
    "audio": ["voz", "música", "efeito", "ambiente"],
    "outro": ["não classificado"],
}

PROMPT_VISAO = """Você classifica um arquivo de mídia para a biblioteca de um estúdio.

Responda SOMENTE com JSON, nesta forma exata:
{"titulo": "...", "categoria": "...", "subcategoria": "...", "etiquetas": ["...", "..."], "descricao": "..."}

Regras:
- "titulo": 3 a 6 palavras em português, descrevendo o conteúdo. Sem extensão de arquivo,
  sem data, sem "imagem de".
- "categoria": exatamente uma destas: {categorias}
- "subcategoria": uma das opções da categoria escolhida.
- "etiquetas": 3 a 8 palavras-chave em português, minúsculas, sem repetir o título.
- "descricao": uma frase objetiva sobre o que está no arquivo.
Não invente o que não está visível."""


def _slug(texto: str) -> str:
    """Nome de arquivo previsível a partir do título: sem acento, sem espaço, minúsculo."""
    dobrado = "".join(
        ch for ch in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(ch) != "Mn"
    )
    limpo = re.sub(r"[^a-z0-9]+", "-", dobrado).strip("-")
    return limpo[:60] or "sem-titulo"


def _tokens(texto: str) -> list[str]:
    dobrado = "".join(
        ch for ch in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(ch) != "Mn"
    )
    return [t for t in re.findall(r"[a-z0-9]{3,}", dobrado)]


@dataclass
class IndexerStatus:
    running: bool = False
    mode: str = "parado"          # parado | ocioso | sob demanda
    processed: int = 0
    failed: int = 0
    total: int = 0
    current: str = ""
    last_error: dict[str, Any] | None = None
    last_run_at: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rodando": self.running,
            "modo": self.mode,
            "processados": self.processed,
            "falhas": self.failed,
            "total": self.total,
            "atual": self.current,
            "ultimo_erro": self.last_error,
            "ultima_execucao": self.last_run_at,
            "historico": self.history[-20:],
        }


class AssetIndexer:
    """Mantém a biblioteca organizada. Idempotente: reprocessar não duplica nada."""

    VISUAL_KINDS = {"image", "video"}
    IDLE_SECONDS = 45.0

    def __init__(self, store: Store, gateway: AIGateway, jobs: Any = None):
        self.store = store
        self.gateway = gateway
        self.jobs = jobs
        self.status = IndexerStatus()
        self._task: asyncio.Task | None = None
        self._idle_task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    # ---- fila ---------------------------------------------------------------

    def pending(self, limit: int = 500) -> list[dict[str, Any]]:
        """Assets ainda sem ficha de indexação, ou com ficha de versão antiga."""
        pendentes = []
        for asset in self.store.list_assets(limit=limit):
            ficha = (asset.get("metadata") or {}).get("index")
            if not ficha or ficha.get("versao") != 1:
                pendentes.append(asset)
        return pendentes

    def summary(self) -> dict[str, Any]:
        """O que a biblioteca mostra no topo: quanto está organizado, e como está dividido."""
        assets = self.store.list_assets(limit=2000)
        indexados = [a for a in assets if (a.get("metadata") or {}).get("index")]
        por_categoria: dict[str, int] = {}
        por_origem = {"saida": 0, "upload": 0}
        for asset in assets:
            ficha = (asset.get("metadata") or {}).get("index") or {}
            categoria = ficha.get("categoria") or "nao classificado"
            por_categoria[categoria] = por_categoria.get(categoria, 0) + 1
            por_origem["saida" if asset.get("job_id") else "upload"] += 1
        return {
            "total": len(assets),
            "indexados": len(indexados),
            "pendentes": len(assets) - len(indexados),
            "por_categoria": dict(sorted(por_categoria.items(), key=lambda kv: -kv[1])),
            "por_origem": por_origem,
            "categorias_validas": CATEGORIAS,
        }

    # ---- indexação de um asset ---------------------------------------------

    async def index_asset(self, asset_id: str, *, force: bool = False) -> dict[str, Any]:
        asset = self.store.get_asset(asset_id)
        metadata = dict(asset.get("metadata") or {})
        if metadata.get("index") and not force:
            return {"asset_id": asset_id, "estado": "ja_indexado", "index": metadata["index"]}

        path = Path(asset["path"])
        if not path.is_file():
            raise GatewayError("ARQUIVO_AUSENTE", f"O arquivo do asset {asset_id} não está no disco.",
                               "Restaure o backup ou remova o asset da biblioteca.")

        if asset["kind"] in self.VISUAL_KINDS:
            ficha = await self._index_visual(asset, path)
        else:
            ficha = self._index_deterministic(asset, path)

        ficha["versao"] = 1
        ficha["indexado_em"] = utc_now()
        ficha["nome_sugerido"] = f"{_slug(ficha['titulo'])}{path.suffix.lower()}"
        ficha["busca"] = sorted(set(
            _tokens(ficha["titulo"]) + _tokens(ficha.get("descricao", ""))
            + [t for etiqueta in ficha.get("etiquetas", []) for t in _tokens(etiqueta)]
            + _tokens(asset.get("original_name") or "")
        ))
        metadata["index"] = ficha
        self._save_metadata(asset_id, metadata)
        self.store.audit("indexer", "asset.indexed", "asset", asset_id,
                         {"categoria": ficha["categoria"], "titulo": ficha["titulo"]})
        return {"asset_id": asset_id, "estado": "indexado", "index": ficha}

    async def _index_visual(self, asset: dict[str, Any], path: Path) -> dict[str, Any]:
        """Imagem e vídeo passam pelo modelo de visão. Vídeo usa o primeiro frame."""
        alvo = path
        temporario: Path | None = None
        if asset["kind"] == "video":
            temporario = await self._first_frame(path)
            if temporario:
                alvo = temporario
        try:
            if alvo.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                # Formato que o modelo de visão não lê: cai para o determinístico.
                return self._index_deterministic(asset, path)
            categorias = ", ".join(CATEGORIAS)
            resposta = await self.gateway.chat_json(
                "visao",
                [
                    {"role": "system", "content": PROMPT_VISAO.replace("{categorias}", categorias)},
                    {"role": "user", "content": f"Arquivo: {asset.get('original_name') or path.name}. Classifique."},
                ],
                images=[alvo],
                temperature=0.1,
            )
            dados = resposta.get("dados")
            if not isinstance(dados, dict):
                ficha = self._index_deterministic(asset, path)
                ficha["motivo_fallback"] = "o modelo de visão não devolveu JSON válido"
                return ficha
            return self._normalize(dados, asset, path, modelo=resposta["modelo"], provedor=resposta["provedor"])
        finally:
            if temporario and temporario.exists():
                temporario.unlink(missing_ok=True)

    async def _first_frame(self, video: Path) -> Path | None:
        """Um frame basta para classificar. FFmpeg já é dependência do projeto."""
        destino = video.parent / f".idx-{video.stem}.jpg"
        comando = ["ffmpeg", "-y", "-v", "error", "-ss", "0.5", "-i", str(video),
                   "-frames:v", "1", "-vf", "scale=768:-2", str(destino)]
        try:
            processo = await asyncio.create_subprocess_exec(
                *comando, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
            await processo.communicate()
        except FileNotFoundError:
            return None
        return destino if destino.exists() else None

    def _index_deterministic(self, asset: dict[str, Any], path: Path) -> dict[str, Any]:
        """Sem modelo disponível, ainda assim a biblioteca fica utilizável.

        Nome do arquivo, tipo e tamanho já dizem bastante; é honesto marcar a origem
        como determinística para o usuário saber que ninguém olhou o conteúdo."""
        base = (asset.get("original_name") or path.stem).rsplit(".", 1)[0]
        legivel = re.sub(r"[_\-]+", " ", base).strip() or path.stem
        mapa_kind = {"image": "abstrato", "video": "cena", "audio": "audio", "model3d": "malha3d"}
        categoria = mapa_kind.get(asset["kind"], "outro")
        return {
            "titulo": legivel[:80],
            "categoria": categoria,
            "subcategoria": CATEGORIAS[categoria][0],
            "etiquetas": sorted(set(_tokens(legivel)))[:8],
            "descricao": f"{asset['kind']} de {path.suffix.lstrip('.').upper() or 'formato desconhecido'}.",
            "origem": "deterministico",
            "modelo": None,
            "provedor": None,
        }

    def _normalize(self, dados: dict[str, Any], asset: dict[str, Any], path: Path,
                   *, modelo: str, provedor: str) -> dict[str, Any]:
        """O modelo pode devolver categoria fora da lista. Aqui ela é forçada de volta."""
        categoria = str(dados.get("categoria", "")).strip().lower()
        if categoria not in CATEGORIAS:
            categoria = {"image": "abstrato", "video": "cena", "audio": "audio",
                         "model3d": "malha3d"}.get(asset["kind"], "outro")
        subcategoria = str(dados.get("subcategoria", "")).strip().lower()
        if subcategoria not in CATEGORIAS[categoria]:
            subcategoria = CATEGORIAS[categoria][0]
        etiquetas = [str(e).strip().lower() for e in (dados.get("etiquetas") or []) if str(e).strip()]
        titulo = str(dados.get("titulo") or "").strip() or path.stem
        return {
            "titulo": titulo[:80],
            "categoria": categoria,
            "subcategoria": subcategoria,
            "etiquetas": etiquetas[:8],
            "descricao": str(dados.get("descricao") or "").strip()[:300],
            "origem": "visao",
            "modelo": modelo,
            "provedor": provedor,
        }

    def _save_metadata(self, asset_id: str, metadata: dict[str, Any]) -> None:
        self.store.db.execute(
            "UPDATE assets SET metadata_json = ? WHERE id = ?",
            (self.store.db.dump_json(metadata), asset_id),
        )

    # ---- renomear (opcional e reversível) -----------------------------------

    def rename_to_suggestion(self, asset_id: str) -> dict[str, Any]:
        """Renomeia o arquivo no disco para o nome sugerido, guardando o anterior.

        Só age quando o usuário pede: o caminho está referenciado por jobs, e trocar
        sem aviso quebraria histórico."""
        asset = self.store.get_asset(asset_id)
        metadata = dict(asset.get("metadata") or {})
        ficha = metadata.get("index") or {}
        sugerido = ficha.get("nome_sugerido")
        if not sugerido:
            raise GatewayError("SEM_FICHA", "Este asset ainda não foi indexado.",
                               "Rode a organização da biblioteca antes de renomear.")
        origem = Path(asset["path"])
        destino = origem.with_name(sugerido)
        contador = 2
        while destino.exists() and destino != origem:
            destino = origem.with_name(f"{Path(sugerido).stem}-{contador}{Path(sugerido).suffix}")
            contador += 1
        if destino == origem:
            return {"asset_id": asset_id, "estado": "ja_no_nome", "path": str(origem)}
        origem.rename(destino)
        ficha["renomeado_de"] = origem.name
        metadata["index"] = ficha
        self.store.db.execute(
            "UPDATE assets SET path = ?, metadata_json = ? WHERE id = ?",
            (str(destino), self.store.db.dump_json(metadata), asset_id),
        )
        self.store.audit("indexer", "asset.renamed", "asset", asset_id,
                         {"de": origem.name, "para": destino.name})
        return {"asset_id": asset_id, "estado": "renomeado", "path": str(destino)}

    # ---- busca semântica leve ------------------------------------------------

    def search(self, consulta: str, limit: int = 50) -> list[dict[str, Any]]:
        """Busca por tokens com peso, sobre as fichas geradas.

        Não é um índice vetorial; é honesto sobre isso. Resolve o caso real de achar
        "aquela imagem da fachada à noite" sem carregar modelo de embedding."""
        alvos = _tokens(consulta)
        if not alvos:
            return []
        resultados = []
        for asset in self.store.list_assets(limit=2000):
            ficha = (asset.get("metadata") or {}).get("index") or {}
            corpus = set(ficha.get("busca") or []) or set(_tokens(asset.get("original_name") or ""))
            if not corpus:
                continue
            acertos = sum(1 for token in alvos if token in corpus)
            if not acertos:
                parciais = sum(1 for token in alvos for palavra in corpus if palavra.startswith(token))
                if not parciais:
                    continue
                acertos = parciais * 0.5
            score = acertos / len(alvos)
            resultados.append({**asset, "score": round(score, 3)})
        resultados.sort(key=lambda item: (-item["score"], item["created_at"]))
        return resultados[:limit]

    # ---- execução em lote ----------------------------------------------------

    async def run_once(self, *, limit: int = 200, force: bool = False, mode: str = "sob demanda") -> dict[str, Any]:
        if self.status.running:
            return {"estado": "ja_rodando", **self.status.as_dict()}
        fila = self.store.list_assets(limit=limit) if force else self.pending(limit)
        self.status = IndexerStatus(running=True, mode=mode, total=len(fila))
        try:
            for asset in fila:
                if self._stop.is_set():
                    break
                self.status.current = asset.get("original_name") or asset["id"]
                try:
                    resultado = await self.index_asset(asset["id"], force=force)
                    self.status.processed += 1
                    self.status.history.append({
                        "asset_id": asset["id"],
                        "titulo": resultado.get("index", {}).get("titulo", ""),
                        "categoria": resultado.get("index", {}).get("categoria", ""),
                    })
                except GatewayError as exc:
                    self.status.failed += 1
                    self.status.last_error = exc.as_dict()
                    # Sem modelo, insistir nos 200 restantes só gera 200 erros iguais.
                    if exc.code in {"SEM_MODELO", "OLLAMA_OFFLINE", "SEM_CHAVE"}:
                        break
                except Exception as exc:  # noqa: BLE001 - um asset ruim não pode parar a fila
                    self.status.failed += 1
                    self.status.last_error = {"erro": "FALHA_ASSET", "mensagem": str(exc)[:200],
                                              "como_corrigir": "Veja o log; o restante da fila continuou."}
        finally:
            self.status.running = False
            self.status.current = ""
            self.status.last_run_at = utc_now()
        return self.status.as_dict()

    def start_background(self, api_loop_owner: Any = None) -> None:
        """Laço ocioso: só trabalha quando não há job de geração ativo."""
        if self._idle_task and not self._idle_task.done():
            return
        self._stop.clear()
        self._idle_task = asyncio.create_task(self._idle_loop(), name="indexer-idle")

    async def _idle_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.IDLE_SECONDS)
                return
            except asyncio.TimeoutError:
                pass
            if self.status.running or self._gpu_busy():
                continue
            if not self.pending(limit=20):
                continue
            try:
                await self.run_once(limit=20, mode="ocioso")
            except Exception:  # noqa: BLE001 - o laço ocioso nunca pode derrubar o servidor
                continue

    def _gpu_busy(self) -> bool:
        """Indexar durante uma geração roubaria a VRAM que o gerador precisa."""
        if not self.jobs:
            return False
        try:
            ativos = [job for job in self.store.list_jobs(limit=20)
                      if job.get("status") in {"running", "queued"}]
            return bool(ativos)
        except Exception:  # noqa: BLE001
            return False

    async def stop(self) -> None:
        self._stop.set()
        if self._idle_task:
            self._idle_task.cancel()
            try:
                await self._idle_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
