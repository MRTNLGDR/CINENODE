"""Worker do estúdio: conversa, propõe grafos e nunca inventa um nó.

A fonte da verdade é o próprio NODE_CATALOG e o validador real de workflow. Toda
proposta do modelo passa por `validate_workflow` antes de chegar ao usuário; se
não passar, o erro volta para o modelo corrigir. O provider é plugável: Ollama
local por padrão, OpenRouter opcional para qualquer outro fornecedor.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import httpx

from .engines.common import EngineExecutionError
from .schemas import WorkflowGraph
from .store import Store
from .workflow import CATALOG_BY_TYPE, NODE_CATALOG, validate_workflow

MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = """Você é o worker do Avangard CineNode Local, um estúdio de geração
de imagem, vídeo, áudio e 3D que roda inteiramente na máquina do usuário.

Regras:
- Só use tipos de nó que vierem de `listar_nos`. Nunca invente um tipo.
- Antes de responder com um grafo, chame `validar_grafo`. Se voltar inválido, corrija
  e valide de novo.
- Conecte respeitando os tipos de porta: a saída de um nó precisa casar com a entrada
  do próximo. `media` aceita qualquer coisa.
- Todo gerador deve terminar em um `output.preview`, para o resultado aparecer.
- Prefira poucos nós bem configurados a grafos enormes.
- Responda em português, direto, sem enrolação. Explique o que montou em uma ou duas frases.
- Você pode abrir o painel lateral quando precisar: `abrir_navegador` para pesquisar na web,
  `abrir_software` para operar ComfyUI, Flowise, Brainlink ou Dify, e `ler_pagina` para ler
  o texto de uma página sem depender da tela. Diga sempre por que está abrindo.
- Não abra o painel sem necessidade: ele ocupa a tela do usuário.

Forma exata do grafo. Todo `edge` precisa de `id`. Nós só aceitam as chaves
`id`, `type`, `position` e `config` — qualquer outra chave é recusada, e os
parâmetros do nó vão dentro de `config`:

{"version": 1,
 "nodes": [{"id": "prompt-1", "type": "input.text", "position": {"x": 80, "y": 120},
            "config": {"text": "..."}}],
 "edges": [{"id": "e1", "source": "prompt-1", "target": "take-1"}],
 "metadata": {}}
"""


def _tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "listar_nos",
                "description": "Lista os tipos de nó disponíveis com portas de entrada, saída e campos configuráveis.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {"type": "string", "description": "Filtra por categoria, opcional."}
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "detalhar_no",
                "description": "Devolve os campos, valores padrão e opções de um tipo de nó específico.",
                "parameters": {
                    "type": "object",
                    "properties": {"tipo": {"type": "string"}},
                    "required": ["tipo"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "listar_perfis",
                "description": "Lista os perfis de modelo instalados e se os arquivos estão presentes.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "listar_assets",
                "description": "Lista as mídias já disponíveis no projeto para usar como referência.",
                "parameters": {
                    "type": "object",
                    "properties": {"limite": {"type": "integer"}},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "abrir_navegador",
                "description": (
                    "Abre o painel lateral no navegador interno e vai até um endereço ou "
                    "busca. Use quando precisar consultar documentação, procurar um "
                    "workflow de referência ou conferir um serviço na web."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "alvo": {"type": "string", "description": "URL completa ou termo de busca."},
                        "motivo": {"type": "string", "description": "Por que está abrindo, em uma frase."},
                    },
                    "required": ["alvo"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "abrir_software",
                "description": (
                    "Abre no painel lateral um software controlável já registrado — "
                    "ComfyUI, Flowise, Brainlink, Dify e outros. Só funciona se o alvo "
                    "estiver no ar; a resposta diz o estado real."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Identificador do alvo, ex.: comfyui, flowise, brainlink."},
                        "motivo": {"type": "string"},
                    },
                    "required": ["id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "ler_pagina",
                "description": (
                    "Lê o texto de uma página pela rede local do servidor e devolve o "
                    "conteúdo. Use para pesquisar sem depender do que aparece na tela."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "limite": {"type": "integer", "description": "Máximo de caracteres, padrão 4000."},
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "validar_grafo",
                "description": "Valida um grafo com o mesmo validador da aplicação. Use sempre antes de propor.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "grafo": {
                            "type": "object",
                            "description": "Objeto com version, nodes, edges e metadata.",
                        }
                    },
                    "required": ["grafo"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "propor_grafo",
                "description": "Entrega o grafo final ao usuário para aprovação. Chame só depois de validar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "grafo": {"type": "object"},
                        "resumo": {"type": "string", "description": "O que o grafo faz, em uma frase."},
                    },
                    "required": ["grafo", "resumo"],
                },
            },
        },
    ]


@dataclass
class AgentResult:
    reply: str
    proposal: dict[str, Any] | None = None
    painel_acoes: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    tool_trace: list[dict[str, Any]] = field(default_factory=list)


class StudioAgent:
    def __init__(self, store: Store):
        self.store = store
        # Ações que o front deve executar no painel depois desta resposta.
        self.painel_acoes: list[dict[str, Any]] = []

    # ---------- ferramentas ----------

    @staticmethod
    def _fold(value: str) -> str:
        """Compara sem acento e sem caixa: o modelo escreve 'video', o catálogo diz 'Vídeo'."""
        return "".join(
            ch for ch in unicodedata.normalize("NFD", str(value).strip().lower())
            if unicodedata.category(ch) != "Mn"
        )

    def _catalog_digest(self, categoria: str | None = None) -> Any:
        items = NODE_CATALOG
        if categoria:
            wanted = self._fold(categoria)
            items = [item for item in NODE_CATALOG if wanted in self._fold(item["category"])]
            if not items:
                # Devolver lista vazia fazia o modelo concluir que o nó não existe.
                return {
                    "aviso": f"Nenhuma categoria corresponde a {categoria!r}.",
                    "categorias_disponiveis": sorted({item["category"] for item in NODE_CATALOG}),
                    "itens": [],
                }
        return [
            {
                "tipo": item["type"],
                "categoria": item["category"],
                "rotulo": item["label"],
                "descricao": item["description"],
                "entradas": item.get("inputs", []),
                "saidas": item.get("outputs", []),
                "campos": [field_["key"] for field_ in item.get("fields", [])],
            }
            for item in items
        ]

    def _node_detail(self, tipo: str) -> dict[str, Any]:
        item = CATALOG_BY_TYPE.get(tipo)
        if not item:
            return {"erro": f"Tipo desconhecido: {tipo}", "tipos_validos": sorted(CATALOG_BY_TYPE)}
        return {
            "tipo": item["type"],
            "entradas": item.get("inputs", []),
            "saidas": item.get("outputs", []),
            "campos": item.get("fields", []),
        }

    def _profiles(self) -> list[dict[str, Any]]:
        profiles = self.store.get_setting("model_profiles") or {}
        result = []
        for key, profile in profiles.items():
            missing = [
                field_ for field_ in ("diffusion_model", "vae", "t5xxl", "llm", "clip_l", "high_noise_diffusion_model")
                if profile.get(field_) and not __import__("pathlib").Path(str(profile[field_])).is_file()
            ]
            result.append({
                "id": key, "rotulo": profile.get("label"), "tipo": profile.get("kind"),
                "pronto": not missing, "arquivos_ausentes": len(missing),
            })
        return result

    def _assets(self, limite: int = 12) -> list[dict[str, Any]]:
        items = self.store.list_assets(limit=max(1, min(int(limite or 12), 50)))
        return [
            {"id": item["id"], "nome": item.get("original_name") or item["id"],
             "tipo": item.get("kind"), "mime": item.get("mime_type")}
            for item in items
        ]

    def _validate(self, grafo: Any) -> dict[str, Any]:
        if not isinstance(grafo, dict):
            return {"valid": False, "errors": [{"code": "INVALID_PAYLOAD", "message": "grafo precisa ser um objeto"}]}
        try:
            parsed = WorkflowGraph.model_validate(grafo)
        except Exception as exc:
            # Devolver só o erro do pydantic não ensina nada: vai junto a forma correta.
            return {
                "valid": False,
                "errors": [{"code": "SCHEMA_ERROR", "message": str(exc)[:600]}],
                "como_corrigir": [
                    "todo edge precisa de um campo id único",
                    "nós aceitam apenas id, type, position e config",
                    "parâmetros do nó ficam dentro de config",
                ],
                "exemplo_minimo": {
                    "version": 1,
                    "nodes": [
                        {"id": "prompt-1", "type": "input.text", "position": {"x": 80, "y": 120},
                         "config": {"text": "uma cidade neon na chuva"}},
                        {"id": "take-1", "type": "video.generate", "position": {"x": 460, "y": 120},
                         "config": {"profile_id": "wan21-t2v-1.3b-fast", "camera_motion": "dolly in"}},
                        {"id": "out-1", "type": "output.preview", "position": {"x": 840, "y": 120}, "config": {}},
                    ],
                    "edges": [
                        {"id": "e1", "source": "prompt-1", "target": "take-1"},
                        {"id": "e2", "source": "take-1", "target": "out-1"},
                    ],
                    "metadata": {},
                },
            }
        report = validate_workflow(parsed)
        return {
            "valid": report["valid"],
            "errors": report["errors"],
            "warnings": report["warnings"],
            "ordem": report["order"],
        }

    def _run_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "listar_nos":
            return self._catalog_digest(arguments.get("categoria"))
        if name == "detalhar_no":
            return self._node_detail(str(arguments.get("tipo", "")))
        if name == "listar_perfis":
            return self._profiles()
        if name == "listar_assets":
            return self._assets(arguments.get("limite", 12))
        if name == "abrir_navegador":
            alvo = str(arguments.get("alvo", "")).strip()
            if not alvo:
                return {"erro": "informe uma URL ou um termo de busca"}
            self.painel_acoes.append({
                "tipo": "navegador", "alvo": alvo,
                "motivo": str(arguments.get("motivo", "")).strip(),
            })
            return {"aceito": True, "abrindo": alvo,
                    "observacao": "O painel abre na tela do usuário. Continue o raciocínio."}
        if name == "abrir_software":
            identificador = str(arguments.get("id", "")).strip().lower()
            conhecidos = {alvo["id"]: alvo for alvo in self.alvos_de_software()}
            if identificador not in conhecidos:
                return {"erro": f"alvo desconhecido: {identificador}",
                        "alvos_disponiveis": sorted(conhecidos)}
            self.painel_acoes.append({
                "tipo": "software", "alvo": identificador,
                "motivo": str(arguments.get("motivo", "")).strip(),
            })
            return {"aceito": True, "abrindo": identificador, **conhecidos[identificador]}
        if name == "ler_pagina":
            return self._ler_pagina(str(arguments.get("url", "")), int(arguments.get("limite", 4000)))
        if name == "validar_grafo":
            return self._validate(arguments.get("grafo"))
        if name == "propor_grafo":
            report = self._validate(arguments.get("grafo"))
            if not report["valid"]:
                return {"aceito": False, "motivo": "grafo inválido", **report}
            return {"aceito": True}
        return {"erro": f"ferramenta desconhecida: {name}"}


    # ---------- painel lateral sob comando do worker ----------

    ALVOS_DE_SOFTWARE = [
        {"id": "comfyui", "nome": "ComfyUI", "url": "http://127.0.0.1:8188",
         "health": "http://127.0.0.1:8188/system_stats",
         "para_que": "montar e rodar workflows de difusão"},
        {"id": "ollama", "nome": "Ollama", "url": "http://127.0.0.1:11434",
         "health": "http://127.0.0.1:11434/api/version",
         "para_que": "servir modelos de linguagem e visão locais"},
        {"id": "brainlink", "nome": "Brainlink", "url": "http://127.0.0.1:8080",
         "health": "http://127.0.0.1:8080",
         "para_que": "documentos, regras e governança"},
        {"id": "flowise", "nome": "Flowise", "url": "http://127.0.0.1:3000",
         "health": "http://127.0.0.1:3000/api/v1/ping",
         "para_que": "montar fluxos de agente visualmente"},
        {"id": "dify", "nome": "Dify", "url": "http://127.0.0.1:8090",
         "health": "http://127.0.0.1:8090/console/api/setup",
         "para_que": "construir aplicações de LLM e RAG"},
    ]

    def alvos_de_software(self) -> list[dict[str, Any]]:
        """Padrão mais o que o usuário registrou em Configurações."""
        registrados = self.store.get_setting("mcp_targets") or []
        por_id = {alvo["id"]: dict(alvo) for alvo in self.ALVOS_DE_SOFTWARE}
        for extra in registrados:
            if extra.get("id"):
                por_id[extra["id"]] = {**por_id.get(extra["id"], {}), **extra}
        return list(por_id.values())

    def _ler_pagina(self, url: str, limite: int = 4000) -> dict[str, Any]:
        """Lê pelo servidor, não pelo navegador: o worker precisa do texto, não do pixel."""
        url = (url or "").strip()
        if not url:
            return {"erro": "informe a url"}
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        try:
            with httpx.Client(timeout=25.0, follow_redirects=True) as client:
                resposta = client.get(url, headers={"User-Agent": "CineNode/0.4 worker"})
        except Exception as exc:  # noqa: BLE001 - rede falha de muitas formas
            return {"erro": "REDE", "detalhe": str(exc)[:160],
                    "como_corrigir": "Confira o endereço e a conexão."}
        html = resposta.text
        titulo = ""
        achado = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        if achado:
            titulo = re.sub(r"\s+", " ", achado.group(1)).strip()[:200]
        limpo = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
        limpo = re.sub(r"(?s)<[^>]+>", " ", limpo)
        texto = re.sub(r"\s+", " ", limpo).strip()
        return {"url": str(resposta.url), "status": resposta.status_code,
                "titulo": titulo, "texto": texto[:max(200, limite)],
                "truncado": len(texto) > limite}

    # ---------- provider ----------

    def _provider_config(self) -> tuple[str, dict[str, Any]]:
        engines = self.store.get_setting("engines") or {}
        openrouter = engines.get("openrouter") or {}
        if openrouter.get("enabled") and (openrouter.get("api_key") or "").strip():
            return "openrouter", openrouter
        return "ollama", engines.get("ollama") or {}

    async def _chat(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        provider, settings = self._provider_config()
        tools = _tool_schemas()
        if provider == "openrouter":
            base = str(settings.get("base_url", "https://openrouter.ai/api/v1")).rstrip("/")
            payload = {"model": settings.get("model"), "messages": messages, "tools": tools}
            headers = {"Authorization": f"Bearer {settings['api_key']}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=float(settings.get("timeout_seconds", 300))) as client:
                response = await client.post(f"{base}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                choice = response.json()["choices"][0]["message"]
            return {
                "content": choice.get("content") or "",
                "tool_calls": [
                    {"name": call["function"]["name"],
                     "arguments": json.loads(call["function"].get("arguments") or "{}")}
                    for call in (choice.get("tool_calls") or [])
                ],
            }

        base = str(settings.get("base_url", "http://127.0.0.1:11434")).rstrip("/")
        model = settings.get("model")
        if not model:
            raise EngineExecutionError("LLM_MODEL_MISSING", "Nenhum modelo local configurado para o worker")
        payload = {"model": model, "stream": False, "messages": messages, "tools": tools,
                   "options": {"temperature": 0.3, "num_ctx": 16384}}
        async with httpx.AsyncClient(timeout=float(settings.get("timeout_seconds", 600))) as client:
            response = await client.post(f"{base}/api/chat", json=payload)
            response.raise_for_status()
            message = response.json().get("message") or {}
        return {
            "content": message.get("content") or "",
            "tool_calls": [
                {"name": call["function"]["name"], "arguments": call["function"].get("arguments") or {}}
                for call in (message.get("tool_calls") or [])
            ],
        }

    # ---------- laço ----------

    async def converse(self, history: list[dict[str, str]], graph: dict[str, Any] | None) -> AgentResult:
        context = {
            "grafo_atual": graph or {"version": 1, "nodes": [], "edges": [], "metadata": {}},
            "total_de_nos_no_catalogo": len(NODE_CATALOG),
        }
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Contexto do projeto aberto: {json.dumps(context, ensure_ascii=False)[:4000]}"},
        ]
        messages.extend({"role": item["role"], "content": item["content"]} for item in history)

        trace: list[dict[str, Any]] = []
        nudged = False
        proposal: dict[str, Any] | None = None
        summary = ""

        for _ in range(MAX_TOOL_ROUNDS):
            try:
                answer = await self._chat(messages)
            except httpx.ConnectError as exc:
                provider, settings = self._provider_config()
                if provider == "ollama":
                    raise EngineExecutionError(
                        "AGENT_PROVIDER_OFFLINE",
                        "O Ollama local não está no ar.",
                        f"Suba com `ollama serve` e confira {settings.get('base_url', 'http://127.0.0.1:11434')}. Detalhe: {exc}",
                    ) from exc
                raise EngineExecutionError(
                    "AGENT_PROVIDER_OFFLINE",
                    "O provider remoto do worker não respondeu.",
                    f"Confira engines.openrouter.base_url e a conexão. Detalhe: {exc}",
                ) from exc
            except httpx.HTTPError as exc:
                raise EngineExecutionError("AGENT_PROVIDER_FAILED", "Falha ao consultar o provider do worker", str(exc)) from exc

            calls = answer.get("tool_calls") or []
            if not calls:
                reply = answer.get("content", "").strip()
                # Modelo que para sem propor nem falar nada não é resposta: cutuca uma vez.
                if not reply and proposal is None and not nudged:
                    nudged = True
                    messages.append({
                        "role": "user",
                        "content": (
                            "Você ainda não entregou nada. Monte o grafo agora, chame `validar_grafo` "
                            "e depois `propor_grafo` com o grafo e um resumo de uma frase."
                        ),
                    })
                    continue
                if not reply and proposal is not None:
                    reply = summary or "Grafo pronto para revisão."
                if not reply:
                    reply = "Não consegui montar um grafo para esse pedido. Descreva o resultado desejado com mais detalhe."
                return AgentResult(reply=reply, proposal=proposal, summary=summary, tool_trace=trace,
                                   painel_acoes=list(self.painel_acoes))

            messages.append({"role": "assistant", "content": answer.get("content") or "", "tool_calls": [
                {"function": {"name": call["name"], "arguments": call["arguments"]}} for call in calls
            ]})
            for call in calls:
                result = self._run_tool(call["name"], call["arguments"] or {})
                trace.append({"ferramenta": call["name"], "resultado_resumo": _summarize(result)})
                if call["name"] == "propor_grafo" and isinstance(result, dict) and result.get("aceito"):
                    proposal = call["arguments"].get("grafo")
                    summary = str(call["arguments"].get("resumo") or "")
                messages.append({
                    "role": "tool", "name": call["name"],
                    "content": json.dumps(result, ensure_ascii=False)[:6000],
                })

        return AgentResult(
            reply="Não consegui fechar uma proposta válida dentro do limite de rodadas.",
            proposal=proposal, summary=summary, tool_trace=trace,
        )


def _summarize(result: Any) -> str:
    if isinstance(result, list):
        return f"{len(result)} itens"
    if isinstance(result, dict):
        if "valid" in result:
            return "válido" if result["valid"] else f"inválido: {len(result.get('errors') or [])} erro(s)"
        if "aceito" in result:
            return "aceito" if result["aceito"] else "recusado"
        return ", ".join(list(result)[:4])
    return str(result)[:80]
