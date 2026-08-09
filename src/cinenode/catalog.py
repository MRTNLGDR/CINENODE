from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NodeSpec:
    type: str
    category: str
    label: str
    description: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    defaults: dict[str, Any]


SPECS = (
    NodeSpec("input.text", "Entrada", "Texto", "Texto ou prompt de entrada.", (), ("value",), {"value": ""}),
    NodeSpec("input.number", "Entrada", "Número", "Valor numérico de entrada.", (), ("value",), {"value": 0}),
    NodeSpec("input.json", "Entrada", "JSON", "Objeto JSON de entrada.", (), ("value",), {"value": {}}),
    NodeSpec("input.file", "Entrada", "Arquivo", "Caminho de um asset enviado ao CineNode.", (), ("path",), {"asset_id": ""}),
    NodeSpec("text.template", "Texto", "Template", "Aplica variáveis a um template com {nome}.", ("value",), ("text",), {"template": "{value}"}),
    NodeSpec("text.concat", "Texto", "Concatenar", "Une duas entradas de texto.", ("a", "b"), ("text",), {"separator": " "}),
    NodeSpec("math.add", "Lógica", "Somar", "Soma duas entradas numéricas.", ("a", "b"), ("value",), {}),
    NodeSpec("math.multiply", "Lógica", "Multiplicar", "Multiplica duas entradas numéricas.", ("a", "b"), ("value",), {}),
    NodeSpec("logic.if", "Lógica", "Condição", "Seleciona um valor por condição booleana.", ("condition", "when_true", "when_false"), ("value",), {}),
    NodeSpec("data.merge", "Dados", "Mesclar JSON", "Mescla objetos JSON.", ("a", "b"), ("value",), {}),
    NodeSpec("util.delay", "Utilitário", "Aguardar", "Aguarda por alguns segundos, com cancelamento.", ("value",), ("value",), {"seconds": 1}),
    NodeSpec("media.image.info", "Mídia", "Analisar imagem", "Lê resolução, modo e formato com Pillow.", ("path",), ("info",), {}),
    NodeSpec("media.ffprobe", "Mídia", "Analisar vídeo/áudio", "Executa ffprobe e retorna metadados JSON.", ("path",), ("info",), {}),
    NodeSpec("media.ffmpeg.transcode", "Mídia", "Transcodificar", "Transcodifica um arquivo com FFmpeg sem shell.", ("path",), ("path",), {"extension": ".mp4", "video_codec": "libx264", "audio_codec": "aac"}),
    NodeSpec("ai.ollama.chat", "IA local", "Ollama Chat", "Executa um modelo Ollama local.", ("prompt",), ("text",), {"base_url": "http://127.0.0.1:11434", "model": "qwen2.5:7b", "system": ""}),
    NodeSpec("ai.comfy.workflow", "IA local", "ComfyUI Workflow", "Envia um workflow API JSON ao ComfyUI local.", ("prompt",), ("result",), {"base_url": "http://127.0.0.1:8188", "workflow": {}, "timeout": 900}),
    NodeSpec("output.text", "Saída", "Saída de texto", "Marca o texto como saída final.", ("value",), ("value",), {}),
    NodeSpec("output.json", "Saída", "Saída JSON", "Marca dados como saída final.", ("value",), ("value",), {}),
)

BY_TYPE = {spec.type: spec for spec in SPECS}


def catalog_payload() -> list[dict[str, Any]]:
    return [asdict(spec) for spec in SPECS]
