from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from .config import AppConfig
from .engines import EngineExecutionError, EngineRegistry
from .schemas import WorkflowGraph, WorkflowNode
from .engines.mesh import MOTIONS as MESH_MOTIONS
from .security import sanitize_filename
from .store import Store


# Movimentos de câmera aplicados ao prompt do gerador de vídeo. É engenharia de prompt
# determinística e local: a descrição é anexada ao prompt do usuário.
# Nenhum modelo proprietário de controle de câmera é usado ou imitado.
CAMERA_MOTIONS: dict[str, str] = {
    "nenhum": "",
    "estática": "static locked-off camera, no camera movement",
    "dolly in": "slow dolly in, camera pushes forward toward the subject",
    "dolly out": "slow dolly out, camera pulls back away from the subject",
    "crash zoom in": "fast crash zoom in, abrupt aggressive push toward the subject",
    "crash zoom out": "fast crash zoom out, abrupt pull away from the subject",
    "zoom in": "smooth optical zoom in on the subject",
    "zoom out": "smooth optical zoom out revealing the surroundings",
    "pan esquerda": "camera pans left horizontally at a steady speed",
    "pan direita": "camera pans right horizontally at a steady speed",
    "whip pan": "fast whip pan with motion blur",
    "tilt up": "camera tilts upward revealing height",
    "tilt down": "camera tilts downward revealing the ground",
    "órbita 360": "camera orbits 360 degrees around the subject, smooth circular arc",
    "arco esquerda": "camera arcs to the left around the subject",
    "arco direita": "camera arcs to the right around the subject",
    "crane up": "crane shot rising upward, camera lifts high above the scene",
    "crane down": "crane shot descending, camera lowers toward the ground",
    "drone fpv": "fpv drone flight, fast sweeping aerial move through the scene",
    "handheld": "handheld camera, subtle organic shake, documentary feel",
    "bullet time": "bullet time, camera orbits while action is frozen in slow motion",
    "dutch angle": "dutch angle, tilted horizon, unsettling framing",
    "hyperlapse": "hyperlapse, fast forward motion through space",
    "foco puxado": "rack focus, focus shifts from foreground to background",
    "parallax": "parallax sweep, foreground and background move at different speeds",
}


def apply_camera_motion(prompt: str, motion: str | None) -> str:
    """Anexa a descrição do movimento ao prompt. Sem movimento, devolve o prompt intacto."""
    fragment = CAMERA_MOTIONS.get(str(motion or "nenhum").strip().lower(), "")
    if not fragment:
        return prompt
    return f"{prompt.rstrip().rstrip('.')}, {fragment}"



# Aspecto e resolução como grandezas de produção, não pixels soltos. O executor
# converte para width/height respeitando o múltiplo exigido pelo engine.
ASPECT_RATIOS: dict[str, float] = {
    "1:1": 1.0, "4:5": 0.8, "9:16": 0.5625, "2:3": 0.6667,
    "3:2": 1.5, "4:3": 1.3333, "16:9": 1.7778, "1.85:1": 1.85,
    "2:1": 2.0, "2.39:1": 2.39, "21:9": 2.3333,
}
# Altura de referência por classe. A largura sai do aspecto.
IMAGE_RESOLUTIONS: dict[str, int] = {
    "base": 1024, "2K": 1440, "4K": 2160, "6K": 3384, "8K": 4320,
}
VIDEO_RESOLUTIONS: dict[str, int] = {
    "base": 480, "HD": 720, "FHD": 1080, "2K": 1440, "4K": 2160,
}
# Perfis de qualidade: steps e cfg. "cinema" e "ultra" custam tempo de GPU real.
QUALITY_PRESETS: dict[str, dict[str, Any]] = {
    "rascunho":  {"steps_image": 4,  "steps_video": 8,  "cfg_scale": 1.0},
    "padrão":    {"steps_image": 8,  "steps_video": 20, "cfg_scale": 6.0},
    "cinema":    {"steps_image": 20, "steps_video": 32, "cfg_scale": 6.5},
    "ultra":     {"steps_image": 40, "steps_video": 50, "cfg_scale": 7.0},
}
# Acabamento de câmera aplicado ao prompt. Grão e motion blur também existem como
# pós real por FFmpeg no nó media.filmlook — aqui é só a intenção de imagem.
CAMERA_LOOKS: dict[str, str] = {
    "nenhum": "",
    "anamórfico": "anamorphic lens, oval bokeh, horizontal flares, cinemascope",
    "profundidade rasa": "shallow depth of field, subject in focus, creamy background bokeh",
    "foco profundo": "deep focus, everything sharp from foreground to background",
    "grande angular": "wide angle lens, 24mm, expansive perspective",
    "teleobjetiva": "telephoto lens, 135mm, compressed perspective, isolated subject",
    "macro": "macro lens, extreme close-up, fine detail",
    "35mm película": "shot on 35mm film, natural grain, halation, filmic color response",
    "16mm película": "shot on 16mm film, pronounced grain, vintage texture",
    "luz natural": "natural available light, soft falloff, motivated sources",
    "contraluz": "backlit, rim light separating subject from background, atmospheric haze",
    "chiaroscuro": "chiaroscuro lighting, deep shadows, single hard key light",
    "hora dourada": "golden hour, warm low sun, long shadows",
    "noite neon": "neon night, wet reflective streets, cyan and magenta practicals",
}


def resolve_dimensions(config: dict[str, Any], *, kind: str, multiple: int) -> tuple[int, int]:
    """Converte aspecto + classe de resolução em largura e altura válidas.

    Só age quando o usuário escolheu um preset; largura/altura manuais continuam
    valendo, para não sequestrar o controle de quem quer números exatos.
    """
    aspect_key = str(config.get("aspect_ratio", "manual"))
    resolution_key = str(config.get("resolution", "manual"))
    if aspect_key == "manual" or resolution_key == "manual":
        return int(config.get("width", 0) or 0), int(config.get("height", 0) or 0)
    table = IMAGE_RESOLUTIONS if kind == "image" else VIDEO_RESOLUTIONS
    if aspect_key not in ASPECT_RATIOS or resolution_key not in table:
        raise EngineExecutionError(
            "INVALID_FORMAT_PRESET",
            f"Combinação inválida: aspecto {aspect_key}, resolução {resolution_key}",
        )
    height = table[resolution_key]
    width = round(height * ASPECT_RATIOS[aspect_key])
    snap = lambda value: max(multiple, int(round(value / multiple)) * multiple)
    return snap(width), snap(height)


def apply_quality(config: dict[str, Any], *, kind: str) -> dict[str, Any]:
    """Aplica o perfil de qualidade sem apagar ajustes explícitos do usuário."""
    preset = QUALITY_PRESETS.get(str(config.get("quality", "manual")))
    if not preset:
        return config
    merged = dict(config)
    merged["steps"] = preset["steps_image"] if kind == "image" else preset["steps_video"]
    merged["cfg_scale"] = preset["cfg_scale"]
    return merged


def apply_camera_look(prompt: str, look: str | None) -> str:
    fragment = CAMERA_LOOKS.get(str(look or "nenhum").strip().lower(), "")
    return f"{prompt.rstrip().rstrip('.')}, {fragment}" if fragment else prompt


# ---------------------------------------------------------------------------
# Portas nomeadas
#
# Antes uma porta era só um tipo: `"image?"`. Dois quadros de referência
# chegavam como duas imagens indistinguíveis e o executor pegava "a última" --
# não havia como dizer qual era o início e qual era o fim da tomada.
#
# A grafia passa a ser `nome:tipo` com sufixo opcional:
#   `?` a porta é opcional        `*` a porta aceita várias conexões
# Sem `nome:`, o nome é o próprio tipo -- toda declaração antiga segue valendo,
# e todo grafo salvo antes disto continua abrindo.
_PORT_RE = re.compile(r"^(?:(?P<name>[a-z0-9_]+):)?(?P<type>[a-z0-9_]+)(?P<flag>[?*]?)$")

PORT_LABELS: dict[str, str] = {
    "text": "Prompt", "image": "Imagem", "video": "Vídeo", "audio": "Áudio",
    "media": "Mídia", "model3d": "Modelo 3D", "data": "Dados",
    "prompt": "Prompt", "negativo": "Negativo",
    "inicio": "Início", "fim": "Fim", "ref": "Referência",
    "logo": "Logo", "mascara": "Máscara", "estilo": "Estilo",
    "dna": "Structure DNA", "controle": "Controle", "trilha": "Trilha",
}


def parse_port(spec: str) -> dict[str, Any]:
    """`"inicio:image?"` -> nome, tipo, opcional, múltiplo e rótulo de tela."""
    match = _PORT_RE.match(str(spec).strip())
    if not match:
        raise ValueError(f"Porta inválida no catálogo: {spec!r}")
    tipo = match.group("type")
    nome = match.group("name") or tipo
    flag = match.group("flag")
    return {
        "name": nome,
        "type": tipo,
        "optional": flag == "?",
        "multi": flag == "*",
        "label": PORT_LABELS.get(nome, PORT_LABELS.get(tipo, nome.capitalize())),
    }


def parse_ports(specs: list[str] | None) -> list[dict[str, Any]]:
    return [parse_port(spec) for spec in (specs or [])]


NODE_CATALOG: list[dict[str, Any]] = [
    {
        "type": "input.text", "category": "Entrada", "label": "Prompt", "description": "Texto, roteiro, descrição visual ou restrições.",
        "inputs": [], "outputs": ["text"],
        "fields": [{"key": "text", "label": "Texto", "type": "textarea", "required": True, "default": ""}],
    },
    {
        "type": "input.asset", "category": "Entrada", "label": "Asset", "description": "Imagem, vídeo ou áudio importado na galeria.",
        "inputs": [], "outputs": ["media"],
        "fields": [{"key": "asset_id", "label": "Asset ID", "type": "asset", "required": True, "default": ""}],
    },
    {
        "type": "llm.enhance", "category": "LLM", "label": "Aprimorar prompt", "description": "Ollama ou OpenCode local. OpenRouter é opcional e sai da máquina.",
        "inputs": ["text"], "outputs": ["text"],
        "fields": [
            {"key": "provider", "label": "Provider", "type": "select", "options": ["ollama", "opencode", "openrouter"], "default": "ollama", "ui": "chips"},
            {"key": "model", "label": "Modelo opcional", "type": "text", "default": ""},
            {"key": "instruction", "label": "Instrução", "type": "textarea", "default": ""},
        ],
    },
    {
        "type": "image.generate", "category": "Imagem", "label": "Gerar imagem", "description": "sd.cpp, WanGP ou ComfyUI local.",
        # Cada referência entra pela sua própria porta: o executor sabe qual é a
        # máscara e qual é o logo sem depender da ordem em que foram ligadas.
        "inputs": ["prompt:text", "negativo:text?", "ref:image*", "estilo:image?",
                   "mascara:image?", "logo:image?", "controle:image?"],
        "outputs": ["image"],
        "fields": [
            {"key": "engine", "label": "Engine", "type": "select", "options": ["sd_cpp", "wangp", "comfyui"], "default": "sd_cpp", "ui": "chips"},
            {"key": "profile_id", "label": "Perfil", "type": "model_profile", "kind": "image", "default": "z-image-turbo-fast"},
            {"key": "negative_prompt", "label": "Prompt negativo", "type": "textarea", "default": ""},
            {"key": "aspect_ratio", "label": "Aspecto", "type": "select", "options": ["manual", *ASPECT_RATIOS], "default": "16:9", "ui": "ratio"},
            {"key": "resolution", "label": "Resolução", "type": "select", "options": ["manual", *IMAGE_RESOLUTIONS], "default": "base", "ui": "chips"},
            {"key": "quality", "label": "Qualidade", "type": "select", "options": ["manual", *QUALITY_PRESETS], "default": "padrão", "ui": "chips"},
            {"key": "camera_look", "label": "Look de câmera", "type": "select", "options": list(CAMERA_LOOKS), "default": "nenhum", "ui": "picker"},
            {"key": "width", "label": "Largura base", "type": "number", "min": 256, "max": 10368, "step": 64, "default": 1024, "show_if": {"any": [{"aspect_ratio": "manual"}, {"resolution": "manual"}]}},
            {"key": "height", "label": "Altura base", "type": "number", "min": 256, "max": 4608, "step": 64, "default": 1024, "show_if": {"any": [{"aspect_ratio": "manual"}, {"resolution": "manual"}]}},
            {"key": "steps", "label": "Steps", "type": "number", "min": 1, "max": 150, "default": 8, "show_if": {"quality": "manual"}},
            {"key": "seed", "label": "Seed (-1 aleatória)", "type": "number", "default": -1, "ui": "seed"},
            {"key": "workflow_path", "label": "Workflow ComfyUI API JSON", "type": "path", "default": "", "show_if": {"engine": "comfyui"}},
        ],
    },
    {
        "type": "video.generate", "category": "Vídeo", "label": "Gerar take", "description": "Text-to-video, image-to-video e start/end frame local.",
        # Início e fim são portas distintas: é o que separa um image-to-video de
        # uma interpolação guiada entre dois quadros escolhidos.
        "inputs": ["prompt:text", "negativo:text?", "inicio:image?", "fim:image?",
                   "ref:image*", "logo:image?", "controle:video?"],
        "outputs": ["video"],
        "fields": [
            {"key": "engine", "label": "Engine", "type": "select", "options": ["sd_cpp", "wangp", "comfyui"], "default": "sd_cpp", "ui": "chips"},
            {"key": "profile_id", "label": "Perfil", "type": "model_profile", "kind": "video", "default": "wan21-t2v-1.3b-fast"},
            {"key": "negative_prompt", "label": "Prompt negativo", "type": "textarea", "default": ""},
            {"key": "camera_motion", "label": "Movimento de câmera", "type": "select", "options": list(CAMERA_MOTIONS), "default": "nenhum", "ui": "picker"},
            {"key": "camera_look", "label": "Look de câmera", "type": "select", "options": list(CAMERA_LOOKS), "default": "nenhum", "ui": "picker"},
            {"key": "aspect_ratio", "label": "Aspecto", "type": "select", "options": ["manual", *ASPECT_RATIOS], "default": "16:9", "ui": "ratio"},
            {"key": "resolution", "label": "Resolução", "type": "select", "options": ["manual", *VIDEO_RESOLUTIONS], "default": "base", "ui": "chips"},
            {"key": "quality", "label": "Qualidade", "type": "select", "options": ["manual", *QUALITY_PRESETS], "default": "padrão", "ui": "chips"},
            {"key": "width", "label": "Largura base", "type": "number", "min": 256, "max": 4096, "step": 16, "default": 832, "show_if": {"any": [{"aspect_ratio": "manual"}, {"resolution": "manual"}]}},
            {"key": "height", "label": "Altura base", "type": "number", "min": 256, "max": 2160, "step": 16, "default": 480, "show_if": {"any": [{"aspect_ratio": "manual"}, {"resolution": "manual"}]}},
            {"key": "frames", "label": "Frames", "type": "number", "min": 9, "max": 1000, "default": 33},
            {"key": "fps", "label": "FPS", "type": "number", "min": 1, "max": 120, "default": 16},
            {"key": "steps", "label": "Steps", "type": "number", "min": 1, "max": 100, "default": 20, "show_if": {"quality": "manual"}},
            {"key": "seed", "label": "Seed", "type": "number", "default": -1, "ui": "seed"},
            {"key": "workflow_path", "label": "Workflow ComfyUI API JSON", "type": "path", "default": "", "show_if": {"engine": "comfyui"}},
            {"key": "wangp_settings", "label": "Settings WanGP JSON", "type": "json", "default": {}, "show_if": {"engine": "wangp"}},
        ],
    },
    {
        "type": "vision.edge", "category": "Controle visual", "label": "Contorno Canny",
        "description": "Linhas limpas para guiar composição e estrutura. Determinístico, sem modelo.",
        "inputs": ["image"], "outputs": ["image"],
        "fields": [
            {"key": "sigma", "label": "Suavização", "type": "number", "min": 0.4, "max": 4.0, "step": 0.1, "default": 1.4, "ui": "slider"},
            {"key": "limiar_baixo", "label": "Limiar baixo", "type": "number", "min": 0.01, "max": 0.5, "step": 0.01, "default": 0.08, "ui": "slider"},
            {"key": "limiar_alto", "label": "Limiar alto", "type": "number", "min": 0.05, "max": 0.9, "step": 0.01, "default": 0.20, "ui": "slider"},
        ],
    },
    {
        "type": "vision.softedge", "category": "Controle visual", "label": "Contorno suave",
        "description": "Gradiente Sobel. Guia a forma sem travar o detalhe como o Canny.",
        "inputs": ["image"], "outputs": ["image"],
        "fields": [
            {"key": "sigma", "label": "Suavização", "type": "number", "min": 0.2, "max": 6.0, "step": 0.1, "default": 1.0, "ui": "slider"},
        ],
    },
    {
        "type": "vision.normals", "category": "Controle visual", "label": "Mapa de normais",
        "description": "Relevo estimado da luminância, em tangent ou object space.",
        "inputs": ["image"], "outputs": ["image"],
        "fields": [
            {"key": "intensidade", "label": "Intensidade", "type": "number", "min": 0.1, "max": 8.0, "step": 0.1, "default": 1.0, "ui": "slider"},
            {"key": "sigma", "label": "Suavização", "type": "number", "min": 0.0, "max": 6.0, "step": 0.1, "default": 1.0, "ui": "slider"},
            {"key": "espaco", "label": "Espaço", "type": "select", "options": ["tangent", "object"], "default": "tangent", "ui": "chips"},
        ],
    },
    {
        "type": "vision.structure", "category": "Controle visual", "label": "Mapa de estrutura",
        "description": "Diferença de gaussianas: separa detalhe de forma. Preserva composição no re-render.",
        "inputs": ["image"], "outputs": ["image"],
        "fields": [
            {"key": "sigma_detalhe", "label": "Detalhe", "type": "number", "min": 0.2, "max": 6.0, "step": 0.1, "default": 1.0, "ui": "slider"},
            {"key": "sigma_base", "label": "Base", "type": "number", "min": 2.0, "max": 40.0, "step": 0.5, "default": 12.0, "ui": "slider"},
        ],
    },
    {
        "type": "vision.threshold", "category": "Controle visual", "label": "Limiar adaptativo",
        "description": "Binariza por média local. Para planta baixa e documento com luz desigual.",
        "inputs": ["image"], "outputs": ["image"],
        "fields": [
            {"key": "janela", "label": "Janela", "type": "number", "min": 5, "max": 201, "step": 2, "default": 31, "ui": "slider"},
            {"key": "offset", "label": "Offset", "type": "number", "min": 0.0, "max": 0.3, "step": 0.005, "default": 0.02, "ui": "slider"},
        ],
    },
    {
        "type": "vision.depth", "category": "Controle visual", "label": "Mapa de profundidade",
        "description": "Profundidade monocular por modelo neural local. Exige peso baixado.",
        "inputs": ["image"], "outputs": ["image"],
        "fields": [
            {"key": "modelo", "label": "Modelo", "type": "select", "options": ["depth-anything-v2-small"], "default": "depth-anything-v2-small", "ui": "chips"},
            {"key": "inverter", "label": "Inverter", "type": "select", "options": ["nao", "sim"], "default": "nao", "ui": "chips"},
        ],
    },
    {
        "type": "image.upscale", "category": "Pós", "label": "Upscale AI imagem", "description": "Real-ESRGAN NCNN Vulkan em tiles.",
        "inputs": ["image"], "outputs": ["image"],
        "fields": [
            {"key": "scale", "label": "Escala", "type": "select", "options": [2, 3, 4], "default": 4, "ui": "chips"},
            {"key": "model", "label": "Modelo", "type": "select", "options": ["realesrgan-x4plus", "realesrgan-x4plus-anime", "realesr-animevideov3"], "default": "realesrgan-x4plus", "ui": "chips"},
            # Medido nesta RTX 4090 Laptop, 1024²→4×: tile=0 leva 244,9 s e tile=256 leva 6,0 s.
            {"key": "tile", "label": "Tile (0 auto)", "type": "number", "min": 0, "max": 2048, "default": 256},
        ],
    },
    {
        "type": "image.resize", "category": "Pós", "label": "Resize Lanczos", "description": "Resize determinístico não-IA por FFmpeg.",
        "inputs": ["image"], "outputs": ["image"],
        "fields": [
            {"key": "width", "label": "Largura", "type": "number", "min": 64, "max": 16384, "default": 3840},
            {"key": "height", "label": "Altura", "type": "number", "min": 64, "max": 16384, "default": 2160},
        ],
    },
    {
        "type": "video.interpolate", "category": "Pós", "label": "Interpolar FPS", "description": "RIFE NCNN Vulkan ou minterpolate FFmpeg.",
        "inputs": ["video"], "outputs": ["video"],
        "fields": [
            {"key": "engine", "label": "Engine", "type": "select", "options": ["rife", "ffmpeg"], "default": "rife", "ui": "chips"},
            {"key": "target_fps", "label": "FPS final", "type": "number", "min": 2, "max": 240, "default": 60},
        ],
    },
    {
        "type": "video.upscale", "category": "Pós", "label": "Upscale AI vídeo", "description": "Extrai frames, aplica Real-ESRGAN e recompõe com áudio.",
        "inputs": ["video"], "outputs": ["video"],
        "fields": [
            {"key": "scale", "label": "Escala", "type": "select", "options": [2, 3, 4], "default": 2, "ui": "chips"},
            {"key": "model", "label": "Modelo", "type": "text", "default": "realesrgan-x4plus"},
            {"key": "target_fps", "label": "FPS", "type": "number", "min": 1, "max": 240, "default": 24},
        ],
    },
    {
        "type": "media.export", "category": "Saída", "label": "Exportar filme", "description": "Encode final 4K/8K em H.264, H.265, ProRes ou AV1.",
        "inputs": ["video"], "outputs": ["video"],
        "fields": [
            {"key": "codec", "label": "Codec", "type": "select", "options": ["h264", "h265", "prores", "av1"], "default": "h265", "ui": "chips"},
            {"key": "crf", "label": "CRF", "type": "number", "min": 0, "max": 51, "default": 16},
            {"key": "fps", "label": "FPS opcional", "type": "number", "min": 0, "max": 240, "default": 0},
            {"key": "filename", "label": "Nome do arquivo", "type": "text", "default": "filme-final.mp4"},
        ],
    },
    {
        "type": "output.preview", "category": "Saída", "label": "Saída/preview", "description": "Marca uma saída terminal e a registra na galeria.",
        "inputs": ["media"], "outputs": ["media"], "fields": [],
    },
    {
        "type": "text.concat", "category": "Utilidades", "label": "Concatenar prompt",
        "description": "Junta os textos de todas as entradas conectadas em um único prompt.",
        "inputs": ["text*"], "outputs": ["text"],
        "fields": [
            {"key": "separator", "label": "Separador", "type": "text", "default": ", "},
            {"key": "prefix", "label": "Prefixo", "type": "text", "default": ""},
            {"key": "suffix", "label": "Sufixo", "type": "text", "default": ""},
            {"key": "skip_empty", "label": "Ignorar entradas vazias", "type": "select", "options": ["sim", "não"], "default": "sim", "ui": "chips"},
        ],
    },
    {
        "type": "video.concat", "category": "Utilidades", "label": "Combinar vídeos",
        "description": "Concatena os vídeos das entradas na ordem das conexões, normalizando resolução e FPS por FFmpeg.",
        "inputs": ["video*"], "outputs": ["video"],
        "fields": [
            {"key": "width", "label": "Largura (0 = do primeiro)", "type": "number", "min": 0, "max": 7680, "step": 2, "default": 0},
            {"key": "height", "label": "Altura (0 = do primeiro)", "type": "number", "min": 0, "max": 4320, "step": 2, "default": 0},
            {"key": "fps", "label": "FPS (0 = do primeiro)", "type": "number", "min": 0, "max": 240, "default": 0},
        ],
    },
    {
        "type": "video.trim", "category": "Utilidades", "label": "Cortar vídeo",
        "description": "Recorta um trecho por tempo de início e duração via FFmpeg.",
        "inputs": ["video"], "outputs": ["video"],
        "fields": [
            {"key": "start_seconds", "label": "Início (s)", "type": "number", "min": 0, "step": 0.1, "default": 0, "min": 0, "max": 600, "ui": "slider"},
            {"key": "duration_seconds", "label": "Duração (s, 0 = até o fim)", "type": "number", "min": 0, "step": 0.1, "default": 0, "min": 0, "max": 600, "ui": "slider"},
        ],
    },
    {
        "type": "audio.extract", "category": "Áudio", "label": "Extrair áudio",
        "description": "Separa a faixa de áudio de um vídeo. Falha com erro real se não houver áudio.",
        "inputs": ["video"], "outputs": ["audio"],
        "fields": [
            {"key": "codec", "label": "Codec", "type": "select", "options": ["aac", "wav", "flac"], "default": "aac", "ui": "chips"},
        ],
    },
    {
        "type": "audio.mux", "category": "Áudio", "label": "Aplicar áudio ao vídeo",
        "description": "Combina um vídeo e um áudio em um único arquivo, sem recodificar o vídeo.",
        "inputs": ["video", "audio"], "outputs": ["video"],
        "fields": [
            {"key": "mode", "label": "Duração", "type": "select", "options": ["shortest", "longest"], "default": "shortest", "ui": "chips"},
            {"key": "volume", "label": "Volume", "type": "number", "min": 0, "max": 4, "step": 0.05, "default": 1},
        ],
    },
    {
        "type": "model3d.generate", "category": "3D", "label": "Gerar 3D",
        "description": "Imagem para malha 3D com Hunyuan3D-2 no sidecar ComfyUI local. Saída .glb.",
        "inputs": ["image"], "outputs": ["model3d"],
        "fields": [
            {"key": "checkpoint", "label": "Checkpoint", "type": "text", "default": "hunyuan3d-dit-v2_fp16.safetensors"},
            {"key": "steps", "label": "Steps", "type": "number", "min": 1, "max": 100, "default": 30},
            {"key": "cfg", "label": "CFG", "type": "number", "min": 1, "max": 20, "step": 0.5, "default": 5.5},
            {"key": "resolution", "label": "Tokens do latente", "type": "number", "min": 512, "max": 8192, "step": 256, "default": 3072},
            {"key": "octree_resolution", "label": "Resolução do octree", "type": "number", "min": 16, "max": 512, "step": 16, "default": 256},
            {"key": "num_chunks", "label": "Chunks do decode", "type": "number", "min": 1000, "max": 500000, "step": 1000, "default": 8000},
            {"key": "threshold", "label": "Limiar da malha", "type": "number", "min": -1, "max": 1, "step": 0.05, "default": 0.6},
            {"key": "seed", "label": "Seed", "type": "number", "default": -1, "ui": "seed"},
        ],
    },
    {
        "type": "human.dna", "category": "Personagem", "label": "DNA humano",
        "description": "Mede rosto e corpo das referências com MediaPipe local e consolida em uma ficha versionada.",
        "inputs": ["image"], "outputs": ["media"],
        "fields": [
            {"key": "altura_real_m", "label": "Altura real (m)", "type": "number",
             "min": 0, "max": 2.5, "step": 0.01, "default": 0, "ui": "slider"},
            {"key": "limite_angulo", "label": "Ângulo máximo do rosto", "type": "number",
             "min": 10, "max": 80, "step": 5, "default": 35, "ui": "slider"},
            {"key": "titular", "label": "Titular das referências", "type": "text", "default": ""},
            {"key": "base_de_direitos", "label": "Base de direitos", "type": "select",
             "options": ["sintético", "titular consentiu", "licenciado", "não declarado"],
             "default": "não declarado", "ui": "chips"},
        ],
    },
    {
        "type": "media.scopes", "category": "Análise", "label": "Scopes e falsa cor",
        "description": "Waveform, vectorscope, histograma, falsa cor, preto e branco e canal alfa por FFmpeg.",
        "inputs": ["media"], "outputs": ["image"],
        "fields": [
            {"key": "mode", "label": "Leitura", "type": "select",
             "options": ["falsa cor", "falsa cor (faixas)", "waveform", "vectorscope", "histograma", "preto e branco", "alfa"], "default": "falsa cor", "ui": "chips"},
            {"key": "frame_seconds", "label": "Segundo do frame (vídeo)", "type": "number", "min": 0, "step": 0.1, "default": 0, "min": 0, "max": 600, "ui": "slider"},
        ],
    },
    {
        "type": "media.filmlook", "category": "Pós", "label": "Acabamento de película",
        "description": "Grão, motion blur, vinheta e halação reais por FFmpeg — não é prompt.",
        "inputs": ["video"], "outputs": ["video"],
        "fields": [
            {"key": "grain", "label": "Grão", "type": "number", "min": 0, "max": 60, "default": 12},
            {"key": "motion_blur", "label": "Motion blur (frames)", "type": "number", "min": 0, "max": 8, "default": 0},
            {"key": "vignette", "label": "Vinheta", "type": "select", "options": ["não", "sim"], "default": "não", "ui": "chips"},
            {"key": "saturation", "label": "Saturação", "type": "number", "min": 0, "max": 3, "step": 0.05, "default": 1},
            {"key": "contrast", "label": "Contraste", "type": "number", "min": 0.5, "max": 2, "step": 0.05, "default": 1},
        ],
    },
    # ---- Fase E: personagem. Cada nó chama uma operação do PERZON que calcula
    # de verdade. O catálogo do PERZON tem 1697 contratos; aqui só entra o que roda.
    {
        "type": "human.mesh.check", "category": "Personagem", "label": "Checar malha",
        "description": "Mede estanqueidade, gênero, componentes soltos, faces degeneradas e vértices duplicados. Diz o que cada defeito quebra depois.",
        "inputs": ["model3d"], "outputs": ["data"],
        "fields": [],
    },
    {
        "type": "human.mesh.repair", "category": "Personagem", "label": "Reparar malha",
        "description": "Solda vértices coincidentes, remove faces degeneradas, reorienta normais e fecha buracos. Conservador: só faz o que não inventa geometria.",
        "inputs": ["model3d"], "outputs": ["model3d"],
        "fields": [
            {"key": "fechar_buracos", "label": "Fechar buracos", "type": "select", "options": ["sim", "não"], "default": "sim", "ui": "chips"},
        ],
    },
    {
        "type": "human.mesh.normalize", "category": "Personagem", "label": "Escala canônica",
        "description": "Põe o personagem em metros, centrado, com os pés na origem — a convenção que glTF e motor de jogo esperam.",
        "inputs": ["model3d"], "outputs": ["model3d"],
        "fields": [
            {"key": "altura_alvo_m", "label": "Altura alvo (m)", "type": "number", "min": 0.1, "max": 5.0, "step": 0.01, "default": 1.75},
        ],
    },
    {
        "type": "human.rig.build", "category": "Personagem", "label": "Esqueleto e pesos",
        "description": "Gera 20 juntas das proporções medidas da malha e calcula peso de skin por distância ao osso, limitado a 4 influências — o teto do glTF.",
        "inputs": ["model3d"], "outputs": ["data"],
        "fields": [
            {"key": "max_influencias", "label": "Influências por vértice", "type": "number", "min": 1, "max": 8, "default": 4},
        ],
    },
    {
        "type": "human.rig.validate", "category": "Personagem", "label": "Validar rig",
        "description": "Acusa peso não normalizado, osso sem influência e par esquerda/direita assimétrico — defeitos que só apareceriam depois de animar.",
        "inputs": ["model3d"], "outputs": ["data"],
        "fields": [],
    },
    {
        "type": "human.material.maps", "category": "Personagem", "label": "Mapas PBR",
        "description": "Deriva normal, rugosidade e oclusão da textura de entrada. Nada é ruído nem preset: tudo sai de medida sobre o pixel.",
        "inputs": ["image"], "outputs": ["image"],
        "fields": [
            {"key": "mapa", "label": "Mapa", "type": "select", "options": ["normal", "rugosidade", "oclusão"], "default": "normal", "ui": "chips"},
            {"key": "forca", "label": "Força (normal)", "type": "number", "min": 0.1, "max": 10.0, "step": 0.1, "default": 2.0},
            {"key": "janela", "label": "Janela (rugosidade)", "type": "number", "min": 3, "max": 63, "step": 2, "default": 9},
            {"key": "raio", "label": "Raio (oclusão)", "type": "number", "min": 3, "max": 129, "step": 2, "default": 21},
        ],
    },
    {
        "type": "human.material.check", "category": "Personagem", "label": "Validar PBR",
        "description": "Confere albedo na faixa fisicamente plausível e acusa iluminação assada na textura, que daria duas sombras ao objeto no render.",
        "inputs": ["image"], "outputs": ["data"],
        "fields": [],
    },
    {
        "type": "model3d.retopology", "category": "3D", "label": "Retopologia",
        "description": "Limpeza, decimação por erro quádrico e normais suaves. Algoritmo determinístico, sem IA.",
        "inputs": ["model3d"], "outputs": ["model3d"],
        "fields": [
            {"key": "target_triangles", "label": "Triângulos alvo (0 usa a razão)", "type": "number", "min": 0, "max": 2000000, "step": 1000, "default": 20000},
            {"key": "ratio", "label": "Razão quando alvo = 0", "type": "number", "min": 0.01, "max": 1, "step": 0.01, "default": 0.1},
            {"key": "aggressiveness", "label": "Agressividade", "type": "number", "min": 1, "max": 10, "default": 7},
            {"key": "keep_largest", "label": "Manter só o maior corpo", "type": "select", "options": ["sim", "não"], "default": "sim", "ui": "chips"},
            {"key": "smooth_angle", "label": "Ângulo de suavização (0 desliga)", "type": "number", "min": 0, "max": 90, "default": 45},
        ],
    },
    {
        "type": "model3d.texture", "category": "3D", "label": "UV e textura",
        "description": "Unwrap com xatlas e textura assada por projeção planar da imagem de origem.",
        "inputs": ["model3d", "image"], "outputs": ["model3d"],
        "fields": [
            {"key": "resolution", "label": "Resolução do atlas", "type": "select", "options": [512, 1024, 2048, 4096], "default": 1024, "ui": "chips"},
            {"key": "axis", "label": "Eixo de projeção", "type": "select", "options": ["-z", "+z", "-x", "+x", "-y", "+y"], "default": "-z", "ui": "chips"},
        ],
    },
    {
        "type": "model3d.animate", "category": "3D", "label": "Animar malha",
        "description": "Escreve canais de animação glTF TRS. Transformação rígida, não é rigging esqueletal.",
        "inputs": ["model3d"], "outputs": ["model3d"],
        "fields": [
            {"key": "motion", "label": "Movimento", "type": "select", "options": list(MESH_MOTIONS), "default": "turntable", "ui": "chips"},
            {"key": "duration", "label": "Duração (s)", "type": "number", "min": 0.5, "max": 60, "step": 0.5, "default": 4},
            {"key": "keyframes", "label": "Keyframes", "type": "number", "min": 4, "max": 600, "default": 48},
        ],
    },
    {
        "type": "model3d.export", "category": "3D", "label": "Exportar malha",
        "description": "Converte a malha para GLB, glTF, OBJ, PLY ou STL.",
        "inputs": ["model3d"], "outputs": ["model3d"],
        "fields": [
            {"key": "format", "label": "Formato", "type": "select", "options": ["glb", "gltf", "obj", "ply", "stl"], "default": "glb", "ui": "chips"},
            {"key": "filename", "label": "Nome do arquivo", "type": "text", "default": "malha-final"},
        ],
    },
]

CATALOG_BY_TYPE = {item["type"]: item for item in NODE_CATALOG}
_NODE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class WorkflowValidationError(ValueError):
    def __init__(self, errors: list[dict[str, Any]]):
        super().__init__("Workflow inválido")
        self.errors = errors



def preflight_workflow(
    graph: WorkflowGraph,
    *,
    store: Store,
    config: AppConfig,
    sidecar_health: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Recusa antes de gastar GPU o que só falharia depois de esperar na fila.

    Das 23 falhas medidas neste projeto, 8 eram detectáveis um segundo antes:
    prompt não conectado, asset vazio, arquivo de workflow inexistente e sidecar
    fora do ar. Este pré-voo transforma cada uma num problema apontado no nó.

    Devolve problemas por nó. Lista vazia significa que a execução pode começar.
    """
    problemas: list[dict[str, Any]] = []
    saude = sidecar_health or {}

    def anotar(node_id: str, codigo: str, mensagem: str, como_corrigir: str) -> None:
        problemas.append({"node_id": node_id, "codigo": codigo,
                          "mensagem": mensagem, "como_corrigir": como_corrigir})

    entradas: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    portas_ligadas: dict[str, set[str]] = {node.id: set() for node in graph.nodes}
    for edge in graph.edges:
        if edge.target in entradas:
            entradas[edge.target].append(edge.source)
            if edge.target_handle:
                portas_ligadas[edge.target].add(edge.target_handle)

    for node in graph.nodes:
        item = CATALOG_BY_TYPE.get(node.type)
        if not item:
            anotar(node.id, "TIPO_DESCONHECIDO", f"O tipo {node.type} não existe no catálogo.",
                   "Remova o nó ou troque por um tipo válido.")
            continue
        config_no = node.config or {}

        # Entrada obrigatória declarada e não conectada. Com portas nomeadas o
        # aviso diz QUAL porta falta -- "Início não conectado" em vez do genérico
        # "precisa de entrada", que não dizia onde ligar.
        portas_entrada = parse_ports(item.get("inputs"))
        obrigatorias = [p for p in portas_entrada if not p["optional"] and not p["multi"]]
        rotulo = item.get("label", node.type)
        if portas_entrada and not entradas[node.id]:
            faltando = obrigatorias or portas_entrada
            anotar(node.id, "ENTRADA_NAO_CONECTADA",
                   f"{rotulo} precisa de entrada e nada está conectado nele.",
                   f"Conecte um nó que produza {', '.join(p['label'] for p in faltando)}.")
        elif portas_ligadas[node.id]:
            # Só cobramos porta a porta quando o grafo já usa handles; grafos
            # antigos não têm essa informação e não podem ser reprovados por ela.
            for porta in obrigatorias:
                if porta["name"] not in portas_ligadas[node.id]:
                    anotar(node.id, "PORTA_NAO_CONECTADA",
                           f"A porta {porta['label']} de {rotulo} está vazia.",
                           f"Ligue um nó de {porta['type']} na porta {porta['label']}.")

        # Campo obrigatório vazio.
        for campo in item.get("fields", []):
            if not campo.get("required"):
                continue
            valor = config_no.get(campo["key"])
            if valor in (None, "", []):
                anotar(node.id, "CAMPO_OBRIGATORIO_VAZIO",
                       f"O campo {campo['label']} está vazio.",
                       f"Preencha {campo['label']} no nó.")

        # Asset apontado precisa existir no disco, não só no grafo.
        asset_id = str(config_no.get("asset_id", "")).strip()
        if node.type == "input.asset" and asset_id:
            try:
                asset = store.get_asset(asset_id)
                if not Path(asset["path"]).is_file():
                    anotar(node.id, "ASSET_SEM_ARQUIVO",
                           "O arquivo deste asset não está mais no disco.",
                           "Reenvie o arquivo ou escolha outro asset.")
            except Exception:  # noqa: BLE001 - asset removido é caso esperado
                anotar(node.id, "ASSET_INEXISTENTE",
                       f"O asset {asset_id} não existe mais na biblioteca.",
                       "Escolha outro asset no nó.")

        # Workflow do ComfyUI apontado por caminho.
        caminho_workflow = str(config_no.get("workflow_path", "")).strip()
        if caminho_workflow and not Path(caminho_workflow).is_file():
            anotar(node.id, "WORKFLOW_INEXISTENTE",
                   f"O workflow {Path(caminho_workflow).name} não existe no caminho indicado.",
                   "Corrija o caminho ou deixe em branco para usar o padrão.")

        # Sidecar exigido pelo engine escolhido.
        engine = str(config_no.get("engine", "")).strip()
        if engine == "comfyui" or node.type.startswith("model3d."):
            if saude.get("comfyui") is False:
                anotar(node.id, "SIDECAR_FORA",
                       "Este nó depende do ComfyUI, que não está respondendo.",
                       "Suba com scripts/run-comfy.ps1, ou use start.bat.")

    return {"pronto": not problemas, "problemas": problemas,
            "total_nos": len(graph.nodes), "com_problema": len({p["node_id"] for p in problemas})}

def validate_workflow(graph: WorkflowGraph, *, for_execution: bool = False) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    nodes = {node.id: node for node in graph.nodes}
    for node in graph.nodes:
        if not _NODE_ID_RE.match(node.id):
            errors.append({"code": "INVALID_NODE_ID", "node_id": node.id, "message": "ID contém caracteres inválidos"})
        if node.id in node_ids:
            errors.append({"code": "DUPLICATE_NODE", "node_id": node.id, "message": "ID de nó duplicado"})
        node_ids.add(node.id)
        if node.type not in CATALOG_BY_TYPE:
            errors.append({"code": "UNKNOWN_NODE_TYPE", "node_id": node.id, "message": f"Tipo desconhecido: {node.type}"})
    edge_ids: set[str] = set()
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    indegree: dict[str, int] = {node_id: 0 for node_id in node_ids}
    ocupadas: dict[tuple[str, str], str] = {}  # (nó, porta) -> aresta que a tomou
    for edge in graph.edges:
        if edge.id in edge_ids:
            errors.append({"code": "DUPLICATE_EDGE", "edge_id": edge.id, "message": "ID de conexão duplicado"})
        edge_ids.add(edge.id)
        if edge.source not in nodes or edge.target not in nodes:
            errors.append({"code": "DANGLING_EDGE", "edge_id": edge.id, "message": "Conexão aponta para nó inexistente"})
            continue
        if edge.source == edge.target:
            errors.append({"code": "SELF_EDGE", "edge_id": edge.id, "message": "Nó não pode conectar em si mesmo"})
            continue
        # Porta nomeada: existe? aceita este tipo? Uma porta simples já ocupada
        # não recebe uma segunda ligação -- quem quer várias declara `*`.
        alvo = CATALOG_BY_TYPE.get(nodes[edge.target].type)
        if alvo and edge.target_handle:
            porta = next((p for p in parse_ports(alvo.get("inputs")) if p["name"] == edge.target_handle), None)
            if not porta:
                errors.append({"code": "UNKNOWN_PORT", "edge_id": edge.id, "node_id": edge.target,
                               "message": f"A porta {edge.target_handle} não existe em {alvo.get('label', edge.target)}"})
            else:
                origem = CATALOG_BY_TYPE.get(nodes[edge.source].type)
                saidas = {p["type"] for p in parse_ports((origem or {}).get("outputs"))}
                if saidas and porta["type"] not in saidas and "media" not in saidas and porta["type"] != "media":
                    errors.append({"code": "PORT_TYPE_MISMATCH", "edge_id": edge.id, "node_id": edge.target,
                                   "message": f"A porta {porta['label']} espera {porta['type']}, "
                                              f"mas a origem entrega {'/'.join(sorted(saidas))}"})
                elif not porta["multi"] and ocupadas.get((edge.target, porta["name"])):
                    errors.append({"code": "PORT_ALREADY_USED", "edge_id": edge.id, "node_id": edge.target,
                                   "message": f"A porta {porta['label']} já tem uma conexão"})
                else:
                    ocupadas[(edge.target, porta["name"])] = edge.id
        outgoing[edge.source].append(edge.target)
        indegree[edge.target] += 1
    queue = sorted([node_id for node_id, degree in indegree.items() if degree == 0])
    order: list[str] = []
    while queue:
        current = queue.pop(0)
        order.append(current)
        for target in outgoing[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
                queue.sort()
    if len(order) != len(nodes):
        errors.append({"code": "WORKFLOW_CYCLE", "message": "O workflow contém ciclo"})
    if for_execution and not graph.nodes:
        errors.append({"code": "EMPTY_WORKFLOW", "message": "Adicione pelo menos um nó antes de executar"})
    terminal = sorted(node_id for node_id in node_ids if not outgoing[node_id])
    if graph.nodes and not terminal:
        warnings.append({"code": "NO_TERMINAL_NODE", "message": "Nenhum nó terminal encontrado"})
    return {"valid": not errors, "errors": errors, "warnings": warnings, "order": order, "terminal_nodes": terminal}


@dataclass(slots=True)
class ExecutionResult:
    node_results: dict[str, dict[str, Any]]
    terminal_results: list[dict[str, Any]]
    assets: list[dict[str, Any]]


ProgressCallback = Callable[[float, str], Awaitable[None]]
LogCallback = Callable[[str, str], Awaitable[None]]
CancelCheck = Callable[[], bool]


class WorkflowExecutor:
    def __init__(self, store: Store, registry: EngineRegistry, config: AppConfig):
        self.store = store
        self.registry = registry
        self.config = config

    @staticmethod
    def _upstream(graph: WorkflowGraph, node_id: str, results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        """Resultados que chegam ao nó, cada um carimbado com a porta de entrada.

        O carimbo vai numa cópia rasa (`_handle`) para não sujar o resultado que
        o nó de origem publicou -- ele pode alimentar várias portas diferentes.
        """
        entradas: list[dict[str, Any]] = []
        for edge in graph.edges:
            if edge.target != node_id or edge.source not in results:
                continue
            item = dict(results[edge.source])
            item["_handle"] = getattr(edge, "target_handle", None) or None
            entradas.append(item)
        return entradas

    @staticmethod
    def _porta(upstream: list[dict[str, Any]], handle: str) -> list[dict[str, Any]]:
        """Só o que entrou por esta porta. Vazio quando ninguém ligou nela."""
        return [item for item in upstream if item.get("_handle") == handle]

    @classmethod
    def _path_da_porta(
        cls,
        upstream: list[dict[str, Any]],
        handle: str,
        kinds: set[str] | None = None,
    ) -> Path | None:
        """Arquivo ligado numa porta nomeada.

        Sem correspondência devolve None -- e o chamador decide se cai para o
        comportamento antigo (`_first_path`) ou trata como não conectado. Grafos
        salvos antes das portas nomeadas não têm `target_handle` e continuam indo
        pelo caminho antigo.
        """
        return cls._first_path(cls._porta(upstream, handle), kinds)

    @classmethod
    def _paths_da_porta(
        cls,
        upstream: list[dict[str, Any]],
        handle: str,
        kinds: set[str] | None = None,
    ) -> list[Path]:
        return cls._all_paths(cls._porta(upstream, handle), kinds)

    @classmethod
    def _texto_da_porta(cls, upstream: list[dict[str, Any]], handle: str, fallback: str = "") -> str:
        """Texto da porta nomeada; sem ela, a regra antiga (último texto que chegou)."""
        na_porta = cls._first_text(cls._porta(upstream, handle), "")
        return na_porta or cls._first_text(upstream, fallback)

    @classmethod
    def _anexar_referencias(
        cls,
        config: dict[str, Any],
        upstream: list[dict[str, Any]],
        portas: dict[str, str],
        *,
        kinds: set[str] | None = None,
    ) -> dict[str, Any]:
        """Copia para o config os arquivos ligados em cada porta de referência.

        Porta `*` vira lista de caminhos; porta simples vira um caminho. Chave
        ausente significa porta vazia -- o engine não recebe entrada fantasma.
        """
        resultado = dict(config)
        for handle, chave in portas.items():
            arquivos = cls._paths_da_porta(upstream, handle, kinds)
            if not arquivos:
                continue
            resultado[chave] = [str(p) for p in arquivos] if chave.endswith("s") else str(arquivos[-1])
        return resultado

    @staticmethod
    def _first_text(upstream: list[dict[str, Any]], fallback: str = "") -> str:
        for item in reversed(upstream):
            value = item.get("text")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return fallback.strip()

    @staticmethod
    def _all_texts(upstream: list[dict[str, Any]]) -> list[str]:
        return [item["text"] for item in upstream if isinstance(item.get("text"), str)]

    @staticmethod
    def _all_paths(upstream: list[dict[str, Any]], kinds: set[str] | None = None) -> list[Path]:
        paths: list[Path] = []
        for item in upstream:
            path = item.get("path")
            if not path or (kinds is not None and item.get("kind") not in kinds):
                continue
            candidate = Path(str(path)).resolve()
            if candidate.is_file():
                paths.append(candidate)
        return paths

    @staticmethod
    def _first_path(upstream: list[dict[str, Any]], kinds: set[str] | None = None) -> Path | None:
        for item in reversed(upstream):
            path = item.get("path")
            kind = item.get("kind")
            if path and (kinds is None or kind in kinds):
                candidate = Path(str(path)).resolve()
                if candidate.is_file():
                    return candidate
        return None

    async def execute(
        self,
        job_id: str,
        project_id: str | None,
        graph: WorkflowGraph,
        *,
        progress: ProgressCallback,
        log: LogCallback,
        cancel_check: CancelCheck,
    ) -> ExecutionResult:
        validation = validate_workflow(graph, for_execution=True)
        if not validation["valid"]:
            raise WorkflowValidationError(validation["errors"])
        output_dir = self.config.outputs_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        nodes = {node.id: node for node in graph.nodes}
        results: dict[str, dict[str, Any]] = {}
        assets: list[dict[str, Any]] = []
        order: list[str] = validation["order"]
        for index, node_id in enumerate(order):
            if cancel_check():
                raise EngineExecutionError("JOB_CANCELLED", "Execução cancelada pelo usuário")
            node = nodes[node_id]
            await progress(index / max(1, len(order)) * 100.0, node_id)
            await log("info", f"Executando {node.type} ({node.id})")
            upstream = self._upstream(graph, node.id, results)
            result = await self._execute_node(
                node,
                upstream,
                output_dir,
                job_id,
                project_id,
                cancel_check=cancel_check,
                log=log,
            )
            results[node.id] = result
            if result.get("asset"):
                assets.append(result["asset"])
        await progress(100.0, "")
        terminal_results = [results[node_id] for node_id in validation["terminal_nodes"] if node_id in results]
        return ExecutionResult(results, terminal_results, assets)

    def _checar_identidade(self, prompt: str, upstream: list[dict[str, Any]]) -> None:
        """Consulta a política de identidade antes de gerar.

        Sintético passa. Sem referência de imagem, passa. Só o caso de rosto de
        pessoa usado como identidade em conteúdo sexual explícito, sem base de
        direitos declarada no asset, é recusado — com a instrução de como declarar.
        """
        from .policy import BASE_PADRAO, PoliticaIdentidade, Referencia, prompt_pede_explicito

        if not prompt_pede_explicito(prompt):
            return
        referencias: list[Referencia] = []
        for item in upstream:
            if item.get("kind") != "image" or not item.get("path"):
                continue
            asset = item.get("asset") or {}
            direitos = (asset.get("metadata") or {}).get("direitos") or {}
            referencias.append(Referencia(
                asset_id=asset.get("id") or Path(item["path"]).stem,
                caminho=Path(item["path"]),
                base_de_direitos=str(direitos.get("base", BASE_PADRAO)),
                titular=str(direitos.get("titular", "")),
            ))
        if not referencias:
            return
        PoliticaIdentidade(self.config.home).exigir(prompt, referencias)

    # ---- Fase E ---------------------------------------------------------

    # Cada nó de personagem mapeia para um `feature_id` do PERZON. A tabela fica
    # aqui, e não espalhada em ifs, para que acrescentar uma operação seja uma
    # linha em vez de um ramo novo.
    _PERZON_POR_NO: dict[str, str] = {
        "human.mesh.check": "PZ-06-topologia-estavel",
        "human.mesh.repair": "PZ-07-remover-duplicados",
        "human.mesh.normalize": "PZ-06-pontos-de-medicao",
        "human.rig.build": "PZ-11-peso-automatico",
        "human.rig.validate": "PZ-11-validar-hierarquia",
        "human.material.check": "PZ-08-correcao-de-cor",
    }
    _PERZON_MAPA_PBR: dict[str, str] = {
        "normal": "PZ-08-normal",
        "rugosidade": "PZ-08-roughness",
        "oclusão": "PZ-08-reconstrucao-de-area-oculta",
    }

    def _executar_perzon(self, node: Any, source: str, config: dict[str, Any],
                         project_id: str | None, job_id: str | None) -> dict[str, Any]:
        from .perzon import PerzonEngine, PerzonOperationError

        if node.type == "human.material.maps":
            escolha = str(config.get("mapa", "normal"))
            feature = self._PERZON_MAPA_PBR.get(escolha)
            if feature is None:
                raise EngineExecutionError(
                    "MAPA_DESCONHECIDO", f"Mapa '{escolha}' não existe.",
                    f"Escolha um de: {', '.join(self._PERZON_MAPA_PBR)}")
            # Cada mapa usa um parâmetro só; mandar os três daria PARAMETRO_DESCONHECIDO.
            chave = {"normal": "forca", "rugosidade": "janela", "oclusão": "raio"}[escolha]
            bruto = config.get(chave)
            parametros = {chave: bruto} if bruto is not None else {}
        else:
            feature = self._PERZON_POR_NO.get(node.type)
            if feature is None:
                raise EngineExecutionError(
                    "NO_SEM_OPERACAO", f"{node.type} não tem operação PERZON associada.")
            parametros = {}
            if node.type == "human.mesh.normalize" and config.get("altura_alvo_m") is not None:
                parametros["altura_alvo_m"] = float(config["altura_alvo_m"])
            if node.type == "human.rig.build" and config.get("max_influencias") is not None:
                parametros["max_influencias"] = int(config["max_influencias"])

        motor = PerzonEngine(self.config.outputs_dir)
        try:
            resultado = motor.executar(feature, str(source), parametros)
        except PerzonOperationError as erro:
            raise EngineExecutionError(erro.codigo, erro.mensagem, erro.dica) from erro

        # `human.mesh.repair` fecha buracos quando pedido: duas operações, um nó.
        if node.type == "human.mesh.repair" and str(config.get("fechar_buracos", "sim")) == "sim":
            reparada = resultado["artefatos"][0]["caminho"] if resultado["artefatos"] else str(source)
            fechado = motor.executar("PZ-07-preencher-buracos", reparada, {})
            resultado["metrica"] = {**resultado["metrica"], "buracos": fechado["metrica"]}
            resultado["artefatos"] = fechado["artefatos"] or resultado["artefatos"]

        if not resultado["artefatos"]:
            return {"kind": "data", "data": resultado["metrica"],
                    "text": json.dumps(resultado["metrica"], ensure_ascii=False)[:4000],
                    "engine_result": resultado}

        artefato = resultado["artefatos"][0]
        asset = self.store.add_asset(
            Path(artefato["caminho"]), artefato["tipo"], project_id, job_id,
            metadata={"node_id": node.id, "operation": feature, "origem": "perzon"})
        return {"kind": artefato["tipo"], "path": artefato["caminho"], "asset": asset,
                "engine_result": resultado}

    async def _execute_node(
        self,
        node: WorkflowNode,
        upstream: list[dict[str, Any]],
        output_dir: Path,
        job_id: str,
        project_id: str | None,
        *,
        cancel_check: CancelCheck,
        log: LogCallback,
    ) -> dict[str, Any]:
        config = dict(node.config)

        async def engine_log(stream: str, line: str) -> None:
            await log(stream, line)

        runtime = {"cancel_check": cancel_check, "log": engine_log}
        if node.type == "input.text":
            text = str(config.get("text", "")).strip()
            if not text:
                raise EngineExecutionError("PROMPT_EMPTY", f"O nó {node.id} não contém texto")
            return {"kind": "text", "text": text}

        if node.type == "input.asset":
            asset_id = str(config.get("asset_id", "")).strip()
            if not asset_id:
                raise EngineExecutionError("ASSET_ID_MISSING", f"O nó {node.id} não possui asset_id")
            asset = self.store.get_asset(asset_id)
            path = Path(asset["path"]).resolve()
            if not path.is_file():
                raise EngineExecutionError("ASSET_FILE_MISSING", "O arquivo do asset não existe", str(path))
            mime = str(asset["mime_type"])
            if mime.startswith("image/"):
                kind = "image"
            elif mime.startswith("video/"):
                kind = "video"
            elif mime.startswith("audio/"):
                kind = "audio"
            else:
                kind = "media"
            return {"kind": kind, "path": str(path), "asset": asset}

        if node.type == "llm.enhance":
            prompt = self._first_text(upstream, str(config.get("prompt", "")))
            if not prompt:
                raise EngineExecutionError("PROMPT_INPUT_MISSING", "Conecte um prompt ao nó LLM")
            text = await self.registry.enhance_prompt(prompt, config, **runtime)
            return {"kind": "text", "text": text, "source_prompt": prompt}

        if node.type == "image.generate":
            prompt = self._texto_da_porta(upstream, "prompt", str(config.get("prompt", "")))
            self._checar_identidade(prompt, upstream)
            if not prompt:
                raise EngineExecutionError("PROMPT_INPUT_MISSING", "Conecte um prompt ao gerador de imagem")
            prompt = apply_camera_look(prompt, config.get("camera_look"))
            config = apply_quality(config, kind="image")
            width, height = resolve_dimensions(config, kind="image", multiple=64)
            if width and height:
                config["width"], config["height"] = width, height
            negativo_ligado = self._texto_da_porta(upstream, "negativo", "")
            if negativo_ligado:
                config["negative_prompt"] = negativo_ligado
            config = self._anexar_referencias(config, upstream, {
                "ref": "reference_images", "estilo": "style_image",
                "mascara": "mask_image", "logo": "logo_image", "controle": "control_image",
            }, kinds={"image"})
            output = output_dir / f"{sanitize_filename(node.id)}.png"
            generated = await self.registry.generate_image(prompt, str(config.get("negative_prompt", "")), output, config, **runtime)
            actual = Path(generated["path"]).resolve()
            asset = self.store.add_asset(actual, "image", project_id, job_id, metadata={"node_id": node.id, "engine": config.get("engine"), "profile_id": config.get("profile_id")})
            return {"kind": "image", "path": str(actual), "asset": asset, "engine_result": generated}

        if node.type == "video.generate":
            prompt = self._texto_da_porta(upstream, "prompt", str(config.get("prompt", "")))
            self._checar_identidade(prompt, upstream)
            if not prompt:
                raise EngineExecutionError("PROMPT_INPUT_MISSING", "Conecte um prompt ao gerador de vídeo")
            prompt = apply_camera_motion(prompt, config.get("camera_motion"))
            prompt = apply_camera_look(prompt, config.get("camera_look"))
            config = apply_quality(config, kind="video")
            width, height = resolve_dimensions(config, kind="video", multiple=16)
            if width and height:
                config["width"], config["height"] = width, height
            negativo_ligado = self._texto_da_porta(upstream, "negativo", "")
            if negativo_ligado:
                config["negative_prompt"] = negativo_ligado
            # `inicio` é o quadro que o modelo anima. `fim` fecha a interpolação:
            # quem liga os dois pede um percurso entre dois quadros escolhidos,
            # não um image-to-video solto.
            quadro_inicial = self._path_da_porta(upstream, "inicio", {"image"})
            quadro_final = self._path_da_porta(upstream, "fim", {"image"})
            # Grafo salvo antes das portas nomeadas: sem handle, vale a regra antiga.
            input_image = quadro_inicial or self._first_path(upstream, {"image"})
            if quadro_final:
                config["end_frame"] = str(quadro_final)
            config = self._anexar_referencias(config, upstream, {
                "ref": "reference_images", "logo": "logo_image",
            }, kinds={"image"})
            controle = self._path_da_porta(upstream, "controle", {"video"})
            if controle:
                config["control_video"] = str(controle)
            output = output_dir / f"{sanitize_filename(node.id)}.mp4"
            generated = await self.registry.generate_video(prompt, str(config.get("negative_prompt", "")), output, config, input_image=input_image, **runtime)
            actual = Path(generated["path"]).resolve()
            asset = self.store.add_asset(actual, "video", project_id, job_id, metadata={"node_id": node.id, "engine": config.get("engine"), "profile_id": config.get("profile_id")})
            return {"kind": "video", "path": str(actual), "asset": asset, "engine_result": generated}

        if node.type.startswith("vision."):
            source = self._first_path(upstream, {"image"})
            if not source:
                raise EngineExecutionError(
                    "IMAGE_INPUT_MISSING",
                    f"Conecte uma imagem ao nó {node.type}",
                )
            from .engines import vision as vision_engine

            sufixo = node.type.split(".", 1)[1]
            output = output_dir / f"{sanitize_filename(node.id)}-{sufixo}.png"
            origem = Path(source)

            if node.type == "vision.edge":
                generated = vision_engine.canny(
                    origem, output,
                    sigma=float(config.get("sigma", 1.4)),
                    limiar_baixo=float(config.get("limiar_baixo", 0.08)),
                    limiar_alto=float(config.get("limiar_alto", 0.20)),
                )
            elif node.type == "vision.softedge":
                generated = vision_engine.sobel(origem, output, sigma=float(config.get("sigma", 1.0)))
            elif node.type == "vision.normals":
                generated = vision_engine.normais(
                    origem, output,
                    intensidade=float(config.get("intensidade", 1.0)),
                    sigma=float(config.get("sigma", 1.0)),
                    espaco=str(config.get("espaco", "tangent")),
                )
            elif node.type == "vision.structure":
                generated = vision_engine.estrutura(
                    origem, output,
                    sigma_detalhe=float(config.get("sigma_detalhe", 1.0)),
                    sigma_base=float(config.get("sigma_base", 12.0)),
                )
            elif node.type == "vision.threshold":
                generated = vision_engine.limiar_adaptativo(
                    origem, output,
                    janela=int(config.get("janela", 31)),
                    offset=float(config.get("offset", 0.02)),
                )
            elif node.type == "vision.depth":
                generated = vision_engine.profundidade(
                    origem, output,
                    modelos_dir=self.config.models_dir,
                    modelo=str(config.get("modelo", "depth-anything-v2-small")),
                    inverter=str(config.get("inverter", "nao")) == "sim",
                )
            else:
                raise EngineExecutionError("NODE_UNSUPPORTED", f"Nó de visão desconhecido: {node.type}")

            asset = self.store.add_asset(
                output, "image", project_id, job_id,
                metadata={"node_id": node.id, "operation": node.type, "mapa": generated},
            )
            return {"kind": "image", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "image.upscale":
            source = self._first_path(upstream, {"image"})
            if not source:
                raise EngineExecutionError("IMAGE_INPUT_MISSING", "Conecte uma imagem ao upscale")
            output = output_dir / f"{sanitize_filename(node.id)}-upscaled.png"
            generated = await self.registry.postprocess().upscale_image(
                source, output,
                scale=int(config.get("scale", 4)), model=str(config.get("model", "realesrgan-x4plus")),
                tile=int(config.get("tile", 0)), **runtime,
            )
            asset = self.store.add_asset(output, "image", project_id, job_id, metadata={"node_id": node.id, "operation": "ai_upscale", "scale": config.get("scale", 4)})
            return {"kind": "image", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "image.resize":
            source = self._first_path(upstream, {"image"})
            if not source:
                raise EngineExecutionError("IMAGE_INPUT_MISSING", "Conecte uma imagem ao resize")
            output = output_dir / f"{sanitize_filename(node.id)}-resized.png"
            generated = await self.registry.postprocess().resize_image_ffmpeg(source, output, int(config.get("width", 3840)), int(config.get("height", 2160)), **runtime)
            asset = self.store.add_asset(output, "image", project_id, job_id, metadata={"node_id": node.id, "operation": "lanczos_resize", "width": config.get("width"), "height": config.get("height")})
            return {"kind": "image", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "video.interpolate":
            source = self._first_path(upstream, {"video"})
            if not source:
                raise EngineExecutionError("VIDEO_INPUT_MISSING", "Conecte um vídeo à interpolação")
            output = output_dir / f"{sanitize_filename(node.id)}-interpolated.mp4"
            generated = await self.registry.postprocess().interpolate_video(source, output, target_fps=int(config.get("target_fps", 60)), engine=str(config.get("engine", "rife")), **runtime)
            asset = self.store.add_asset(output, "video", project_id, job_id, metadata={"node_id": node.id, "operation": "interpolate", "target_fps": config.get("target_fps", 60)})
            return {"kind": "video", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "video.upscale":
            source = self._first_path(upstream, {"video"})
            if not source:
                raise EngineExecutionError("VIDEO_INPUT_MISSING", "Conecte um vídeo ao upscale")
            output = output_dir / f"{sanitize_filename(node.id)}-upscaled.mp4"
            work_dir = output_dir / f".{sanitize_filename(node.id)}-frames"
            generated = await self.registry.postprocess().upscale_video(
                source, output, work_dir,
                scale=int(config.get("scale", 2)), model=str(config.get("model", "realesrgan-x4plus")),
                target_fps=int(config.get("target_fps", 24)), **runtime,
            )
            asset = self.store.add_asset(output, "video", project_id, job_id, metadata={"node_id": node.id, "operation": "ai_video_upscale", "scale": config.get("scale", 2)})
            return {"kind": "video", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "media.export":
            source = self._first_path(upstream, {"video"})
            if not source:
                raise EngineExecutionError("VIDEO_INPUT_MISSING", "Conecte um vídeo à exportação")
            filename = sanitize_filename(str(config.get("filename", "filme-final.mp4")), "filme-final.mp4")
            suffix = ".mov" if str(config.get("codec", "h265")) == "prores" else ".mp4"
            output = output_dir / (Path(filename).stem + suffix)
            generated = await self.registry.postprocess().export_media(
                source, output, codec=str(config.get("codec", "h265")), crf=int(config.get("crf", 16)),
                fps=int(config.get("fps")) if int(config.get("fps", 0) or 0) > 0 else None, **runtime,
            )
            asset = self.store.add_asset(output, "video", project_id, job_id, original_name=output.name, metadata={"node_id": node.id, "operation": "export", "codec": config.get("codec")})
            return {"kind": "video", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "output.preview":
            if not upstream:
                raise EngineExecutionError("MEDIA_INPUT_MISSING", "Conecte um resultado ao preview")
            return dict(upstream[-1])

        if node.type == "model3d.generate":
            source = self._first_path(upstream, {"image"})
            if not source:
                raise EngineExecutionError("IMAGE_INPUT_MISSING", "Conecte uma imagem ao gerador 3D")
            output = output_dir / f"{sanitize_filename(node.id)}-mesh"
            generated = await self.registry.generate_model3d(source, output, config, **runtime)
            mesh = Path(generated["path"]).resolve()
            asset = self.store.add_asset(
                mesh, "model3d", project_id, job_id,
                metadata={"node_id": node.id, "engine": "comfyui", "checkpoint": config.get("checkpoint")},
            )
            return {"kind": "model3d", "path": str(mesh), "asset": asset, "engine_result": generated}

        # ---- Fase E: personagem ------------------------------------------
        # Chamam o mesmo motor da rota /api/perzon/executar. Um cálculo só, dois
        # caminhos até ele — duplicar a lógica aqui criaria duas verdades.
        if node.type.startswith("human.mesh.") or node.type.startswith("human.rig."):
            source = self._first_path(upstream, {"model3d"})
            if not source:
                raise EngineExecutionError(
                    "MESH_INPUT_MISSING", f"Conecte uma malha ao nó {node.type}")
            return self._executar_perzon(node, source, config, project_id, job_id)

        if node.type.startswith("human.material."):
            source = self._first_path(upstream, {"image"})
            if not source:
                raise EngineExecutionError(
                    "IMAGE_INPUT_MISSING", f"Conecte uma imagem ao nó {node.type}")
            return self._executar_perzon(node, source, config, project_id, job_id)

        if node.type == "model3d.retopology":
            source = self._first_path(upstream, {"model3d"})
            if not source:
                raise EngineExecutionError("MESH_INPUT_MISSING", "Conecte uma malha à retopologia")
            output = output_dir / f"{sanitize_filename(node.id)}-retopo.glb"
            report = await self.registry.mesh_retopology(source, output, config, **runtime)
            asset = self.store.add_asset(output, "model3d", project_id, job_id, metadata={"node_id": node.id, "operation": "retopology", **report["stats_after"]})
            return {"kind": "model3d", "path": str(output), "asset": asset, "engine_result": report}

        if node.type == "model3d.texture":
            source = self._first_path(upstream, {"model3d"})
            image = self._first_path(upstream, {"image"})
            if not source:
                raise EngineExecutionError("MESH_INPUT_MISSING", "Conecte uma malha ao nó de textura")
            if not image:
                raise EngineExecutionError("IMAGE_INPUT_MISSING", "Conecte a imagem de origem ao nó de textura")
            output = output_dir / f"{sanitize_filename(node.id)}-textured.glb"
            report = await self.registry.mesh_texture(source, image, output, config, **runtime)
            asset = self.store.add_asset(output, "model3d", project_id, job_id, metadata={"node_id": node.id, "operation": "texture"})
            return {"kind": "model3d", "path": str(output), "asset": asset, "engine_result": report}

        if node.type == "model3d.animate":
            source = self._first_path(upstream, {"model3d"})
            if not source:
                raise EngineExecutionError("MESH_INPUT_MISSING", "Conecte uma malha ao nó de animação")
            output = output_dir / f"{sanitize_filename(node.id)}-animated.glb"
            report = await self.registry.mesh_animate(source, output, config, **runtime)
            asset = self.store.add_asset(output, "model3d", project_id, job_id, metadata={"node_id": node.id, "operation": "animate", "motion": report["motion"]})
            return {"kind": "model3d", "path": str(output), "asset": asset, "engine_result": report}

        if node.type == "model3d.export":
            source = self._first_path(upstream, {"model3d"})
            if not source:
                raise EngineExecutionError("MESH_INPUT_MISSING", "Conecte uma malha à exportação")
            suffix = str(config.get("format", "glb")).lower()
            name = sanitize_filename(str(config.get("filename", "malha-final")), "malha-final")
            output = output_dir / f"{Path(name).stem}.{suffix}"
            report = await self.registry.mesh_export(source, output, **runtime)
            asset = self.store.add_asset(output, "model3d", project_id, job_id, original_name=output.name, metadata={"node_id": node.id, "operation": "export", "format": suffix})
            return {"kind": "model3d", "path": str(output), "asset": asset, "engine_result": report}

        if node.type == "text.concat":
            parts = self._all_texts(upstream)
            if str(config.get("skip_empty", "sim")) == "sim":
                parts = [part for part in parts if part.strip()]
            if not parts:
                raise EngineExecutionError("PROMPT_INPUT_MISSING", "Conecte ao menos um texto ao concatenador")
            separator = str(config.get("separator", ", "))
            text = f"{config.get('prefix', '')}{separator.join(part.strip() for part in parts)}{config.get('suffix', '')}".strip()
            if not text:
                raise EngineExecutionError("PROMPT_EMPTY", f"A concatenação de {node.id} resultou em texto vazio")
            return {"kind": "text", "text": text, "inputs": len(parts)}

        if node.type == "video.concat":
            sources = self._all_paths(upstream, {"video"})
            if len(sources) < 2:
                raise EngineExecutionError("VIDEO_INPUT_MISSING", "Conecte pelo menos dois vídeos ao combinador")
            output = output_dir / f"{sanitize_filename(node.id)}-combined.mp4"
            generated = await self.registry.postprocess().concat_videos(
                sources, output,
                width=int(config.get("width", 0) or 0), height=int(config.get("height", 0) or 0),
                fps=int(config.get("fps", 0) or 0), **runtime,
            )
            asset = self.store.add_asset(output, "video", project_id, job_id, metadata={"node_id": node.id, "operation": "concat", "clips": len(sources)})
            return {"kind": "video", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "video.trim":
            source = self._first_path(upstream, {"video"})
            if not source:
                raise EngineExecutionError("VIDEO_INPUT_MISSING", "Conecte um vídeo ao corte")
            output = output_dir / f"{sanitize_filename(node.id)}-trimmed.mp4"
            generated = await self.registry.postprocess().trim_video(
                source, output,
                start_seconds=float(config.get("start_seconds", 0) or 0),
                duration_seconds=float(config.get("duration_seconds", 0) or 0),
                **runtime,
            )
            asset = self.store.add_asset(output, "video", project_id, job_id, metadata={"node_id": node.id, "operation": "trim"})
            return {"kind": "video", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "audio.extract":
            source = self._first_path(upstream, {"video", "media"})
            if not source:
                raise EngineExecutionError("VIDEO_INPUT_MISSING", "Conecte um vídeo à extração de áudio")
            codec = str(config.get("codec", "aac"))
            suffix = {"aac": ".m4a", "wav": ".wav", "flac": ".flac"}.get(codec, ".m4a")
            output = output_dir / f"{sanitize_filename(node.id)}-audio{suffix}"
            generated = await self.registry.postprocess().extract_audio(source, output, codec=codec, **runtime)
            asset = self.store.add_asset(output, "audio", project_id, job_id, metadata={"node_id": node.id, "operation": "extract_audio", "codec": codec})
            return {"kind": "audio", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "audio.mux":
            video_source = self._first_path(upstream, {"video"})
            audio_source = self._first_path(upstream, {"audio"})
            if not video_source:
                raise EngineExecutionError("VIDEO_INPUT_MISSING", "Conecte um vídeo ao nó de áudio")
            if not audio_source:
                raise EngineExecutionError("AUDIO_INPUT_MISSING", "Conecte um áudio ao nó de áudio")
            output = output_dir / f"{sanitize_filename(node.id)}-with-audio.mp4"
            generated = await self.registry.postprocess().mux_audio(
                video_source, audio_source, output,
                mode=str(config.get("mode", "shortest")), volume=float(config.get("volume", 1) or 1),
                **runtime,
            )
            asset = self.store.add_asset(output, "video", project_id, job_id, metadata={"node_id": node.id, "operation": "mux_audio"})
            return {"kind": "video", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "human.dna":
            # Todas as referências de imagem que chegaram, não só a primeira: a ficha
            # ganha precisão com o número de ângulos, e a mediana precisa de amostra.
            fontes = [Path(item["path"]) for item in upstream
                      if item.get("kind") == "image" and item.get("path")]
            if not fontes:
                raise EngineExecutionError(
                    "DNA_SEM_REFERENCIA",
                    "Conecte ao menos uma imagem com rosto ou corpo visível",
                    "Use um nó de Asset ou o resultado de uma geração de imagem",
                )
            base_direitos = str(config.get("base_de_direitos", "não declarado"))
            titular = str(config.get("titular", "")).strip()
            if base_direitos == "titular consentiu" and not titular:
                raise EngineExecutionError(
                    "CONSENTIMENTO_SEM_TITULAR",
                    "A base de direitos diz que o titular consentiu, mas o titular não foi nomeado",
                    "Preencha o campo Titular, ou mude a base de direitos",
                )

            from .engines.humandna import HumanDnaEngine, LIMITE_ANGULO_GRAUS

            motor = HumanDnaEngine(self.config.home)
            limite = float(config.get("limite_angulo", LIMITE_ANGULO_GRAUS) or LIMITE_ANGULO_GRAUS)
            leituras = []
            for caminho in fontes:
                await log("stdout", f"DNA: lendo {caminho.name}")
                leitura = motor.ler(caminho, caminho.stem)
                # O limite é do usuário; o motor só sabe o padrão.
                if leitura.face and (abs(leitura.yaw_graus) > limite
                                     or abs(leitura.pitch_graus) > limite):
                    leitura.medida_confiavel = False
                leituras.append(leitura)

            altura = float(config.get("altura_real_m", 0) or 0)
            ficha = motor.consolidar(
                leituras,
                altura_real_m=altura if altura > 0.5 else None,
                consentimento={"titular": titular or None, "base_de_direitos": base_direitos},
            )
            ficha["limite_angulo_graus"] = limite
            output = output_dir / f"{sanitize_filename(node.id)}-humandna.json"
            output.write_text(json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")
            asset = self.store.add_asset(
                output, "data", project_id, job_id,
                metadata={"node_id": node.id, "operation": "human.dna",
                          "referencias": len(leituras),
                          "usadas": ficha["resumo"]["com_face"],
                          "descartadas": len(ficha["resumo"]["descartadas_por_angulo"])},
            )
            await log("stdout",
                      f"DNA: {ficha['resumo']['com_face']} de {len(leituras)} referências usadas, "
                      f"{len(ficha['resumo']['descartadas_por_angulo'])} descartadas por ângulo")
            return {"kind": "data", "path": str(output), "asset": asset, "dna": ficha["resumo"]}

        if node.type == "media.scopes":
            source = self._first_path(upstream)
            if not source:
                raise EngineExecutionError("MEDIA_INPUT_MISSING", "Conecte uma imagem ou vídeo à análise")
            mode = str(config.get("mode", "falsa cor"))
            output = output_dir / f"{sanitize_filename(node.id)}-{sanitize_filename(mode)}.png"
            generated = await self.registry.postprocess().render_scope(
                source, output, mode=mode,
                frame_seconds=float(config.get("frame_seconds", 0) or 0), **runtime,
            )
            asset = self.store.add_asset(output, "image", project_id, job_id, metadata={"node_id": node.id, "operation": "scope", "mode": mode})
            return {"kind": "image", "path": str(output), "asset": asset, "engine_result": generated}

        if node.type == "media.filmlook":
            source = self._first_path(upstream, {"video"})
            if not source:
                raise EngineExecutionError("VIDEO_INPUT_MISSING", "Conecte um vídeo ao acabamento")
            output = output_dir / f"{sanitize_filename(node.id)}-filmlook.mp4"
            generated = await self.registry.postprocess().film_look(
                source, output,
                grain=float(config.get("grain", 12) or 0),
                motion_blur=int(config.get("motion_blur", 0) or 0),
                vignette=str(config.get("vignette", "não")) == "sim",
                saturation=float(config.get("saturation", 1) or 1),
                contrast=float(config.get("contrast", 1) or 1),
                **runtime,
            )
            asset = self.store.add_asset(output, "video", project_id, job_id, metadata={"node_id": node.id, "operation": "filmlook"})
            return {"kind": "video", "path": str(output), "asset": asset, "engine_result": generated}

        raise EngineExecutionError("NODE_NOT_IMPLEMENTED", f"Nó não implementado: {node.type}")
