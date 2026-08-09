"""Gateway de IA: um endereço, muitos provedores, nenhum nó acoplado a fornecedor.

O nó pede uma capacidade (`slot`). O gateway resolve para um provedor concreto —
Ollama local por padrão, OpenRouter quando houver chave — e devolve sempre a mesma
forma de resposta. Trocar de modelo não muda o grafo salvo.

A chave do OpenRouter fica no store, nunca no grafo, nunca no prompt, nunca no log.
"""
from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .store import Store

OLLAMA_URL = "http://127.0.0.1:11434"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
TIMEOUT_SECONDS = 180.0

# Capacidades que qualquer nó pode pedir. O nome é estável; o modelo por trás não é.
CAPABILITY_SLOTS: dict[str, dict[str, Any]] = {
    "texto.rapido": {
        "label": "Texto rápido",
        "description": "Classificar, renomear, escolher ferramenta, validar JSON.",
        "prefer_local": True,
        "local_hints": ["qwen3:1.7b", "qwen3:4b", "llama3.2:3b", "gemma3:4b"],
        "remote_hints": ["google/gemini-2.5-flash-lite", "openai/gpt-5-mini"],
    },
    "texto.raciocinio": {
        "label": "Texto com raciocínio",
        "description": "Planejar grafo, escrever prompt estruturado, decidir pipeline.",
        "prefer_local": True,
        "local_hints": ["qwen3:8b-q4_K_M", "qwen3:14b", "gemma3:12b"],
        "remote_hints": ["anthropic/claude-sonnet-4.5", "openai/gpt-5", "google/gemini-2.5-pro"],
    },
    "visao": {
        "label": "Visão",
        "description": "Descrever imagem, categorizar asset, ler tela, conferir resultado.",
        "prefer_local": True,
        "local_hints": ["qwen3-vl:4b", "qwen2.5vl:3b", "moondream", "qwen2.5vl:7b",
                        "llava:7b", "llava:13b"],
        "remote_hints": ["google/gemini-2.5-flash", "anthropic/claude-sonnet-4.5"],
    },
    "codigo": {
        "label": "Código",
        "description": "Ler repositório, propor patch, escrever teste.",
        "prefer_local": True,
        "local_hints": ["qwen3-coder:7b", "qwen2.5-coder:7b"],
        "remote_hints": ["anthropic/claude-sonnet-4.5", "openai/gpt-5"],
    },
    "embedding": {
        "label": "Vetorização",
        "description": "Transformar texto em vetor para busca semântica.",
        "prefer_local": True,
        "local_hints": ["nomic-embed-text", "mxbai-embed-large", "bge-m3"],
        "remote_hints": ["openai/text-embedding-3-small"],
    },
}


class GatewayError(RuntimeError):
    """Falha com causa acionável: o usuário precisa saber o que fazer a seguir."""

    def __init__(self, code: str, message: str, hint: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint

    def as_dict(self) -> dict[str, Any]:
        return {"erro": self.code, "mensagem": self.message, "como_corrigir": self.hint}


@dataclass
class Resolution:
    """Qual provedor e modelo atenderam o slot, e por quê."""

    provider: str
    model: str
    slot: str
    reason: str
    local: bool


class AIGateway:
    def __init__(self, store: Store):
        self.store = store

    # ---- configuração -------------------------------------------------------

    def settings(self) -> dict[str, Any]:
        raw = self.store.get_setting("ai_gateway") or {}
        return {
            "openrouter_enabled": bool(raw.get("openrouter_enabled", False)),
            "openrouter_key_set": bool(raw.get("openrouter_key")),
            "policy": raw.get("policy", "LOCAL_FIRST"),
            "bindings": raw.get("bindings", {}),
            "site_name": raw.get("site_name", "Avangard CineNode Local"),
        }

    def save_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        raw = dict(self.store.get_setting("ai_gateway") or {})
        for key in ("openrouter_enabled", "policy", "site_name"):
            if key in patch:
                raw[key] = patch[key]
        if "bindings" in patch:
            raw["bindings"] = dict(patch["bindings"] or {})
        # A chave só é gravada quando vem preenchida: mandar vazio não apaga sem intenção.
        if patch.get("openrouter_key"):
            raw["openrouter_key"] = str(patch["openrouter_key"]).strip()
        if patch.get("clear_openrouter_key"):
            raw.pop("openrouter_key", None)
            raw["openrouter_enabled"] = False
        self.store.set_setting("ai_gateway", raw)
        self.store.audit("system", "gateway.settings", "setting", "ai_gateway",
                         {"policy": raw.get("policy"), "openrouter": bool(raw.get("openrouter_key"))})
        return self.settings()

    def _key(self) -> str | None:
        raw = self.store.get_setting("ai_gateway") or {}
        if not raw.get("openrouter_enabled"):
            return None
        key = raw.get("openrouter_key")
        return str(key) if key else None

    # ---- descoberta ---------------------------------------------------------

    async def local_models(self) -> list[dict[str, Any]]:
        """Modelos já baixados no Ollama. Sem Ollama no ar, devolve lista vazia — o
        gateway degrada com aviso, não com exceção."""
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.get(f"{OLLAMA_URL}/api/tags")
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []
        models = []
        for item in data.get("models", []):
            details = item.get("details") or {}
            models.append({
                "id": item.get("name", ""),
                "provider": "ollama",
                "size_bytes": item.get("size", 0),
                "family": details.get("family", ""),
                "parameters": details.get("parameter_size", ""),
                "quantization": details.get("quantization_level", ""),
                "local": True,
            })
        return sorted(models, key=lambda m: m["id"])

    async def remote_models(self) -> list[dict[str, Any]]:
        """Catálogo do OpenRouter. Um endpoint, todos os fornecedores."""
        key = self._key()
        if not key:
            return []
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{OPENROUTER_URL}/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise GatewayError(
                "OPENROUTER_HTTP",
                f"OpenRouter respondeu {exc.response.status_code}.",
                "Confira a chave em Configurações e se ela ainda tem crédito.",
            ) from exc
        except Exception as exc:
            raise GatewayError(
                "OPENROUTER_OFFLINE",
                "Não foi possível falar com o OpenRouter.",
                "Verifique a conexão. O modo local continua funcionando sem ele.",
            ) from exc

        models = []
        for item in data.get("data", []):
            pricing = item.get("pricing") or {}
            modalities = ((item.get("architecture") or {}).get("input_modalities")) or []
            models.append({
                "id": item.get("id", ""),
                "provider": "openrouter",
                "name": item.get("name", item.get("id", "")),
                "vendor": str(item.get("id", "")).split("/")[0],
                "context_length": item.get("context_length"),
                "prompt_price": pricing.get("prompt"),
                "completion_price": pricing.get("completion"),
                "modalities": modalities,
                "vision": "image" in modalities,
                "local": False,
            })
        return sorted(models, key=lambda m: m["id"])

    async def catalog(self) -> dict[str, Any]:
        """O que a tela de roteamento mostra: slots, modelos locais e remotos."""
        local = await self.local_models()
        remote: list[dict[str, Any]] = []
        warning = None
        try:
            remote = await self.remote_models()
        except GatewayError as exc:
            warning = exc.as_dict()
        settings = self.settings()
        slots = []
        for slot_id, spec in CAPABILITY_SLOTS.items():
            bound = settings["bindings"].get(slot_id) or {}
            slots.append({
                "id": slot_id,
                "label": spec["label"],
                "description": spec["description"],
                "sugestoes_locais": spec["local_hints"],
                "sugestoes_remotas": spec["remote_hints"],
                "escolhido": bound,
                "resolvido": self._resolve(slot_id, local, remote, settings),
            })
        return {
            "slots": slots,
            "modelos_locais": local,
            "modelos_remotos": remote,
            "configuracao": settings,
            "aviso": warning,
        }

    # ---- resolução ----------------------------------------------------------

    def _resolve(
        self,
        slot: str,
        local: list[dict[str, Any]],
        remote: list[dict[str, Any]],
        settings: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Escolhe provedor e modelo. A ordem é explícita para o usuário poder discordar."""
        spec = CAPABILITY_SLOTS.get(slot)
        if not spec:
            return None
        bound = settings["bindings"].get(slot) or {}
        local_ids = {model["id"] for model in local}
        remote_ids = {model["id"] for model in remote}

        # 1. Escolha explícita do usuário vence, se o modelo ainda existir.
        if bound.get("provider") == "ollama" and bound.get("model") in local_ids:
            return {"provider": "ollama", "model": bound["model"], "reason": "escolha do usuário", "local": True}
        if bound.get("provider") == "openrouter" and bound.get("model") and remote_ids:
            return {"provider": "openrouter", "model": bound["model"], "reason": "escolha do usuário", "local": False}

        policy = settings.get("policy", "LOCAL_FIRST")
        # 2. Local primeiro, seguindo as dicas do slot na ordem em que foram escritas.
        if policy in ("LOCAL_ONLY", "LOCAL_FIRST"):
            for hint in spec["local_hints"]:
                for candidate in local_ids:
                    if candidate == hint or candidate.startswith(f"{hint.split(':')[0]}:"):
                        return {"provider": "ollama", "model": candidate,
                                "reason": "modelo local compatível", "local": True}
            if policy == "LOCAL_ONLY":
                return None
        # 3. Remoto como extensão, nunca como dependência silenciosa.
        if remote_ids:
            for hint in spec["remote_hints"]:
                if hint in remote_ids:
                    return {"provider": "openrouter", "model": hint,
                            "reason": "sem modelo local para este slot", "local": False}
            return {"provider": "openrouter", "model": sorted(remote_ids)[0],
                    "reason": "primeiro modelo disponível", "local": False}
        # 4. Qualquer local, mesmo fora das dicas, é melhor que nada.
        if local_ids:
            return {"provider": "ollama", "model": sorted(local_ids)[0],
                    "reason": "nenhuma dica combinou; usando o que está instalado", "local": True}
        return None

    async def resolve(self, slot: str) -> Resolution:
        local = await self.local_models()
        remote: list[dict[str, Any]] = []
        try:
            remote = await self.remote_models()
        except GatewayError:
            remote = []
        chosen = self._resolve(slot, local, remote, self.settings())
        if not chosen:
            raise GatewayError(
                "SEM_MODELO",
                f"Nenhum modelo disponível para a capacidade {slot!r}.",
                "Instale um modelo local com `ollama pull "
                f"{CAPABILITY_SLOTS.get(slot, {}).get('local_hints', ['qwen3:4b'])[0]}` "
                "ou ative o OpenRouter em Configurações.",
            )
        return Resolution(chosen["provider"], chosen["model"], slot, chosen["reason"], chosen["local"])

    # ---- execução -----------------------------------------------------------

    async def chat(
        self,
        slot: str,
        messages: list[dict[str, Any]],
        *,
        images: list[Path] | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Chamada única para qualquer provedor. A resposta tem sempre a mesma forma."""
        resolution = await self.resolve(slot)
        if resolution.provider == "ollama":
            content = await self._ollama_chat(resolution.model, messages, images, json_mode, temperature)
        else:
            content = await self._openrouter_chat(resolution.model, messages, images, json_mode, temperature)
        return {
            "conteudo": content,
            "provedor": resolution.provider,
            "modelo": resolution.model,
            "slot": slot,
            "motivo": resolution.reason,
            "local": resolution.local,
        }

    async def _ollama_chat(
        self, model: str, messages: list[dict[str, Any]],
        images: list[Path] | None, json_mode: bool, temperature: float,
    ) -> str:
        payload_messages = [dict(message) for message in messages]
        if images:
            # O Ollama espera base64 puro na última mensagem do usuário.
            encoded = [base64.b64encode(path.read_bytes()).decode("ascii") for path in images]
            for message in reversed(payload_messages):
                if message.get("role") == "user":
                    message["images"] = encoded
                    break
        body: dict[str, Any] = {
            "model": model,
            "messages": payload_messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            body["format"] = "json"
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(f"{OLLAMA_URL}/api/chat", json=body)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:200]
            raise GatewayError(
                "OLLAMA_HTTP", f"Ollama respondeu {exc.response.status_code}: {detail}",
                f"O modelo {model!r} está instalado? Rode `ollama pull {model}`.",
            ) from exc
        except Exception as exc:
            raise GatewayError(
                "OLLAMA_OFFLINE", "O Ollama não respondeu.",
                "Suba com `ollama serve`, ou use start.bat que já cuida disso.",
            ) from exc
        return (data.get("message") or {}).get("content", "")

    async def _openrouter_chat(
        self, model: str, messages: list[dict[str, Any]],
        images: list[Path] | None, json_mode: bool, temperature: float,
    ) -> str:
        key = self._key()
        if not key:
            raise GatewayError(
                "SEM_CHAVE", "OpenRouter está desligado ou sem chave.",
                "Ative e cole a chave em Configurações; ela fica só nesta máquina.",
            )
        payload_messages = [dict(message) for message in messages]
        if images:
            # Formato OpenAI: a mensagem vira lista de partes com data URL.
            partes: list[dict[str, Any]] = []
            for path in images:
                mime = mimetypes.guess_type(path.name)[0] or "image/png"
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                partes.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}})
            for message in reversed(payload_messages):
                if message.get("role") == "user":
                    message["content"] = [{"type": "text", "text": message.get("content", "")}] + partes
                    break
        body: dict[str, Any] = {"model": model, "messages": payload_messages, "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "http://127.0.0.1:8787",
            "X-Title": self.settings()["site_name"],
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(f"{OPENROUTER_URL}/chat/completions", json=body, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise GatewayError(
                "OPENROUTER_HTTP", f"OpenRouter respondeu {exc.response.status_code}.",
                "Confira a chave, o crédito e se o modelo aceita o que foi enviado.",
            ) from exc
        except Exception as exc:
            raise GatewayError(
                "OPENROUTER_OFFLINE", "Não foi possível falar com o OpenRouter.",
                "Verifique a conexão. Modelos locais continuam funcionando.",
            ) from exc
        choices = data.get("choices") or []
        if not choices:
            raise GatewayError("RESPOSTA_VAZIA", "O provedor devolveu uma resposta sem conteúdo.",
                               "Tente outro modelo no seletor.")
        return (choices[0].get("message") or {}).get("content", "")

    async def chat_json(self, slot: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Igual a `chat`, mas garante objeto. Modelo pequeno erra JSON com frequência,
        então o texto bruto volta junto quando o parse falha."""
        result = await self.chat(slot, messages, json_mode=True, **kwargs)
        texto = (result["conteudo"] or "").strip()
        if texto.startswith("```"):
            texto = texto.split("```", 2)[1] if texto.count("```") >= 2 else texto.strip("`")
            texto = texto.removeprefix("json").strip()
        try:
            result["dados"] = json.loads(texto)
        except json.JSONDecodeError:
            inicio, fim = texto.find("{"), texto.rfind("}")
            if inicio >= 0 and fim > inicio:
                try:
                    result["dados"] = json.loads(texto[inicio:fim + 1])
                except json.JSONDecodeError:
                    result["dados"] = None
            else:
                result["dados"] = None
        return result
