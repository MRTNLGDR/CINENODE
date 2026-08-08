from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .common import EngineExecutionError, LogCallback, CancelCheck, find_executable, require_executable, run_command


class LocalLLMEngine:
    def __init__(self, ollama: dict[str, Any], opencode: dict[str, Any], openrouter: dict[str, Any] | None = None):
        self.ollama = ollama
        self.opencode = opencode
        # Provider remoto, desligado por padrão. Só é usado se o nó pedir explicitamente
        # e a chave estiver configurada; nenhum outro caminho do runtime sai da máquina.
        self.openrouter = openrouter or {}

    def _openrouter_key(self) -> str:
        return str(self.openrouter.get("api_key") or os.getenv("OPENROUTER_API_KEY") or "").strip()

    async def status(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        base = str(self.ollama.get("base_url", "http://127.0.0.1:11434")).rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{base}/api/version")
                response.raise_for_status()
                version = response.json().get("version", "unknown")
            result.append({"engine_id": "ollama", "available": True, "version": version, "detail": base})
        except Exception as exc:
            result.append({"engine_id": "ollama", "available": False, "version": None, "detail": str(exc)})
        executable = find_executable(self.opencode.get("binary_path", "opencode"))
        result.append({
            "engine_id": "opencode",
            "available": bool(executable),
            "version": "installed" if executable else None,
            "detail": executable or "opencode não encontrado",
        })
        enabled = bool(self.openrouter.get("enabled"))
        has_key = bool(self._openrouter_key())
        result.append({
            "engine_id": "openrouter",
            "available": enabled and has_key,
            "version": str(self.openrouter.get("model") or "") or None,
            "detail": (
                "provider remoto ativo" if enabled and has_key
                else "desativado" if not enabled
                else "sem OPENROUTER_API_KEY"
            ),
        })
        return result

    async def _openrouter_chat(self, instruction: str, prompt: str, model: str | None) -> str:
        if not self.openrouter.get("enabled"):
            raise EngineExecutionError(
                "OPENROUTER_DISABLED",
                "O provider OpenRouter está desligado.",
                "Ative em Configurações > engines > openrouter.enabled e informe a chave.",
            )
        key = self._openrouter_key()
        if not key:
            raise EngineExecutionError(
                "OPENROUTER_KEY_MISSING",
                "OpenRouter exige uma chave de API.",
                "Defina engines.openrouter.api_key ou a variável de ambiente OPENROUTER_API_KEY.",
            )
        selected = model or self.openrouter.get("model")
        if not selected:
            raise EngineExecutionError("LLM_MODEL_MISSING", "Nenhum modelo OpenRouter foi configurado")
        base = str(self.openrouter.get("base_url", "https://openrouter.ai/api/v1")).rstrip("/")
        payload = {
            "model": str(selected),
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": float(self.openrouter.get("temperature", 0.45)),
        }
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=float(self.openrouter.get("timeout_seconds", 300))) as client:
                response = await client.post(f"{base}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise EngineExecutionError(
                "OPENROUTER_REQUEST_FAILED",
                f"OpenRouter respondeu {exc.response.status_code}",
                exc.response.text[:600],
            ) from exc
        except httpx.HTTPError as exc:
            raise EngineExecutionError("OPENROUTER_REQUEST_FAILED", "Falha ao consultar o OpenRouter", str(exc)) from exc
        try:
            output = str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise EngineExecutionError("LLM_EMPTY_RESPONSE", "Resposta do OpenRouter em formato inesperado", json.dumps(data)[:800]) from exc
        if not output:
            raise EngineExecutionError("LLM_EMPTY_RESPONSE", "OpenRouter não retornou texto")
        return output

    async def enhance(
        self,
        prompt: str,
        *,
        provider: str = "ollama",
        model: str | None = None,
        instruction: str | None = None,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> str:
        instruction = instruction or (
            "Aprimore o prompt para geração audiovisual local. Preserve intenção, personagens, "
            "continuidade e restrições. Retorne somente o prompt final, sem introdução."
        )
        if provider == "openrouter":
            return await self._openrouter_chat(instruction, prompt, model)

        if provider == "opencode":
            executable = require_executable(self.opencode.get("binary_path", "opencode"), "opencode")
            selected = model or self.opencode.get("model")
            args = [executable, "run"]
            if selected:
                args.extend(["--model", str(selected)])
            args.append(f"{instruction}\n\nPROMPT ORIGINAL:\n{prompt}")
            result = await run_command(
                args,
                timeout=int(self.opencode.get("timeout_seconds", 900)),
                cancel_check=cancel_check,
                log=log,
            )
            output = result.stdout.strip()
            if not output:
                raise EngineExecutionError("LLM_EMPTY_RESPONSE", "OpenCode não retornou texto")
            return output

        base = str(self.ollama.get("base_url", "http://127.0.0.1:11434")).rstrip("/")
        selected = model or self.ollama.get("model")
        if not selected:
            raise EngineExecutionError("LLM_MODEL_MISSING", "Nenhum modelo Ollama foi configurado")
        payload = {
            "model": selected,
            "stream": False,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0.45, "num_ctx": 8192},
        }
        try:
            async with httpx.AsyncClient(timeout=float(self.ollama.get("timeout_seconds", 600))) as client:
                response = await client.post(f"{base}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise EngineExecutionError("OLLAMA_REQUEST_FAILED", "Falha ao consultar o Ollama local", str(exc)) from exc
        output = str((data.get("message") or {}).get("content") or "").strip()
        if not output:
            raise EngineExecutionError("LLM_EMPTY_RESPONSE", "Ollama não retornou texto", json.dumps(data)[:1000])
        return output
