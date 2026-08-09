from __future__ import annotations

import json
import mimetypes
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import httpx
from PIL import Image

from .config import Settings
from .security import require_local_url, safe_child


class EngineError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def engine_status() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for name, command in (("ffmpeg", "ffmpeg"), ("ffprobe", "ffprobe")):
        path = shutil.which(command)
        result.append({"id": name, "kind": "binary", "available": bool(path), "path": path})
    for name, url, health in (
        ("ollama", "http://127.0.0.1:11434", "/api/tags"),
        ("comfyui", "http://127.0.0.1:8188", "/system_stats"),
    ):
        available = False
        detail = "não iniciado"
        try:
            with httpx.Client(timeout=0.6) as client:
                response = client.get(url + health)
                available = response.status_code < 500
                detail = f"HTTP {response.status_code}"
        except Exception as exc:
            detail = type(exc).__name__
        result.append({"id": name, "kind": "sidecar", "available": available, "url": url, "detail": detail})
    return result


def image_info(settings: Settings, path_value: str) -> dict[str, Any]:
    path = safe_child(settings.home, path_value)
    if not path.is_file():
        raise EngineError("FILE_NOT_FOUND", f"Arquivo não encontrado: {path_value}")
    try:
        with Image.open(path) as image:
            return {
                "path": str(path.relative_to(settings.home)),
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "format": image.format,
                "frames": getattr(image, "n_frames", 1),
                "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            }
    except Exception as exc:
        raise EngineError("IMAGE_READ_FAILED", str(exc)) from exc


def ffprobe(settings: Settings, path_value: str) -> dict[str, Any]:
    binary = shutil.which("ffprobe")
    if not binary:
        raise EngineError("FFPROBE_MISSING", "ffprobe não está instalado. Rode o instalador com engines.")
    path = safe_child(settings.home, path_value)
    if not path.is_file():
        raise EngineError("FILE_NOT_FOUND", f"Arquivo não encontrado: {path_value}")
    command = [binary, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]
    cp = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if cp.returncode != 0:
        raise EngineError("FFPROBE_FAILED", cp.stderr.strip() or "ffprobe falhou")
    try:
        return json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise EngineError("FFPROBE_INVALID_JSON", str(exc)) from exc


def ffmpeg_transcode(settings: Settings, *, job_id: str, path_value: str, extension: str,
                     video_codec: str, audio_codec: str, cancel: Callable[[], bool],
                     event: Callable[[str, dict[str, Any]], None]) -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise EngineError("FFMPEG_MISSING", "FFmpeg não está instalado. Rode o instalador com engines.")
    source = safe_child(settings.home, path_value)
    if not source.is_file():
        raise EngineError("FILE_NOT_FOUND", f"Arquivo não encontrado: {path_value}")
    suffix = extension if extension.startswith(".") else "." + extension
    output_dir = settings.outputs_dir / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{source.stem}-transcoded{suffix}"
    command = [binary, "-y", "-i", str(source), "-c:v", video_codec, "-c:a", audio_codec, str(output)]
    event("process_started", {"engine": "ffmpeg", "command": [Path(command[0]).name, *command[1:]]})
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    while process.poll() is None:
        if cancel():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            raise EngineError("JOB_CANCELLED", "Transcodificação cancelada")
        time.sleep(0.2)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise EngineError("FFMPEG_FAILED", (stderr or stdout)[-4000:])
    return str(output.relative_to(settings.home))


def ollama_chat(prompt: str, params: dict[str, Any]) -> str:
    base_url = require_local_url(str(params.get("base_url") or "http://127.0.0.1:11434")).rstrip("/")
    model = str(params.get("model") or "qwen2.5:7b")
    messages: list[dict[str, str]] = []
    system = str(params.get("system") or "").strip()
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        response = httpx.post(
            base_url + "/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=float(params.get("timeout", 600)),
        )
        response.raise_for_status()
        data = response.json()
        return str((data.get("message") or {}).get("content") or data.get("response") or "")
    except Exception as exc:
        raise EngineError("OLLAMA_FAILED", f"Ollama não respondeu: {exc}") from exc


def _replace_prompt(value: Any, prompt: str) -> Any:
    if isinstance(value, str):
        return value.replace("{{prompt}}", prompt)
    if isinstance(value, list):
        return [_replace_prompt(item, prompt) for item in value]
    if isinstance(value, dict):
        return {key: _replace_prompt(item, prompt) for key, item in value.items()}
    return value


def comfy_workflow(prompt: str, params: dict[str, Any], *, cancel: Callable[[], bool],
                   event: Callable[[str, dict[str, Any]], None]) -> dict[str, Any]:
    base_url = require_local_url(str(params.get("base_url") or "http://127.0.0.1:8188")).rstrip("/")
    workflow = params.get("workflow")
    if not isinstance(workflow, dict) or not workflow:
        raise EngineError(
            "COMFY_WORKFLOW_REQUIRED",
            "Forneça em workflow o JSON API exportado pelo ComfyUI. Use {{prompt}} nos campos substituíveis.",
        )
    payload = _replace_prompt(workflow, prompt)
    timeout = max(5.0, float(params.get("timeout", 900)))
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(base_url + "/prompt", json={"prompt": payload})
            response.raise_for_status()
            prompt_id = response.json().get("prompt_id")
            if not prompt_id:
                raise EngineError("COMFY_NO_PROMPT_ID", "ComfyUI não retornou prompt_id")
            event("engine_queued", {"engine": "comfyui", "prompt_id": prompt_id})
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if cancel():
                    try:
                        client.post(base_url + "/interrupt")
                    except Exception:
                        pass
                    raise EngineError("JOB_CANCELLED", "Workflow ComfyUI cancelado")
                history = client.get(base_url + f"/history/{prompt_id}")
                if history.status_code == 200:
                    body = history.json()
                    record = body.get(prompt_id)
                    if record:
                        status = record.get("status") or {}
                        if status.get("status_str") == "error" or status.get("completed") is False and status.get("messages"):
                            messages = status.get("messages") or []
                            if any(item and item[0] == "execution_error" for item in messages if isinstance(item, list)):
                                raise EngineError("COMFY_EXECUTION_FAILED", json.dumps(messages, ensure_ascii=False)[-4000:])
                        if record.get("outputs") is not None:
                            return {"prompt_id": prompt_id, "outputs": record.get("outputs"), "status": status}
                time.sleep(0.75)
            raise EngineError("COMFY_TIMEOUT", f"ComfyUI excedeu {timeout:.0f}s")
    except EngineError:
        raise
    except Exception as exc:
        raise EngineError("COMFY_FAILED", f"ComfyUI não respondeu: {exc}") from exc
