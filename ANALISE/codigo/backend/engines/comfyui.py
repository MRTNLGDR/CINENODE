from __future__ import annotations

import asyncio
import copy
import json
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from .common import EngineExecutionError


def _replace_tokens(value: Any, tokens: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_tokens(item, tokens) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_tokens(item, tokens) for item in value]
    if isinstance(value, str):
        if value in tokens:
            return tokens[value]
        result = value
        for token, replacement in tokens.items():
            result = result.replace(token, str(replacement))
        return result
    return value


class ComfyUIEngine:
    engine_id = "comfyui"

    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        self.base_url = str(settings.get("base_url", "http://127.0.0.1:8188")).rstrip("/")

    async def status(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/system_stats")
                response.raise_for_status()
                data = response.json()
            return {"engine_id": self.engine_id, "available": True, "version": str(data.get("system", {}).get("comfyui_version", "unknown")), "detail": self.base_url}
        except Exception as exc:
            return {"engine_id": self.engine_id, "available": False, "version": None, "detail": str(exc)}


    async def upload_image(self, path: Path, *, subfolder: str = "cinenode") -> str:
        """Envia um arquivo local para o ComfyUI e devolve o nome que o LoadImage espera."""
        if not path.is_file():
            raise EngineExecutionError("ASSET_FILE_MISSING", "Arquivo não encontrado para upload", str(path))
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    f"{self.base_url}/upload/image",
                    files={"image": (path.name, path.read_bytes())},
                    data={"overwrite": "true", "subfolder": subfolder},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise EngineExecutionError("COMFYUI_UPLOAD_FAILED", "Falha ao enviar imagem ao ComfyUI", str(exc)) from exc
        name = data.get("name") or path.name
        folder = data.get("subfolder") or ""
        return f"{folder}/{name}" if folder else name

    async def execute_workflow(
        self,
        workflow: dict[str, Any],
        output_dir: Path,
        tokens: dict[str, Any],
        *,
        cancel_check=None,
        progress_callback=None,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        client_id = uuid.uuid4().hex
        prompt = _replace_tokens(copy.deepcopy(workflow), tokens)
        timeout = float(self.settings.get("timeout_seconds", 14400))
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(f"{self.base_url}/prompt", json={"prompt": prompt, "client_id": client_id})
                response.raise_for_status()
                prompt_id = response.json().get("prompt_id")
            if not prompt_id:
                raise EngineExecutionError("COMFYUI_INVALID_RESPONSE", "ComfyUI não retornou prompt_id")
            started = asyncio.get_running_loop().time()
            while True:
                if cancel_check and cancel_check():
                    async with httpx.AsyncClient(timeout=10) as client:
                        await client.post(f"{self.base_url}/interrupt")
                    raise EngineExecutionError("JOB_CANCELLED", "Execução cancelada pelo usuário")
                if asyncio.get_running_loop().time() - started > timeout:
                    raise EngineExecutionError("ENGINE_TIMEOUT", "ComfyUI excedeu o limite de tempo")
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.get(f"{self.base_url}/history/{prompt_id}")
                    response.raise_for_status()
                    history = response.json()
                entry = history.get(prompt_id)
                if entry:
                    outputs = entry.get("outputs") or {}
                    downloaded: list[Path] = []
                    for node_output in outputs.values():
                        # Coleta genérica: cada nó do ComfyUI nomeia sua saída de um jeito
                        # ("images", "gifs", "audio", "3d" no SaveGLB…). O que importa é a
                        # lista de itens com "filename", não a chave.
                        for items in node_output.values():
                            if not isinstance(items, list):
                                continue
                            for item in items:
                                if not isinstance(item, dict):
                                    continue
                                filename = item.get("filename")
                                if not filename:
                                    continue
                                query = urlencode({
                                    "filename": filename,
                                    "subfolder": item.get("subfolder", ""),
                                    "type": item.get("type", "output"),
                                })
                                async with httpx.AsyncClient(timeout=300) as client:
                                    media = await client.get(f"{self.base_url}/view?{query}")
                                    media.raise_for_status()
                                target = output_dir / Path(filename).name
                                target.write_bytes(media.content)
                                downloaded.append(target)
                    if not downloaded:
                        raise EngineExecutionError("COMFYUI_OUTPUT_MISSING", "ComfyUI concluiu sem arquivos de saída", json.dumps(entry)[:2000])
                    return downloaded
                if progress_callback:
                    await progress_callback(None)
                await asyncio.sleep(1)
        except httpx.HTTPError as exc:
            raise EngineExecutionError("COMFYUI_REQUEST_FAILED", "Falha ao comunicar com ComfyUI", str(exc)) from exc
