from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..config import AppConfig
from ..store import Store
from .common import EngineExecutionError, find_executable, run_command
from .comfyui import ComfyUIEngine
from .llm import LocalLLMEngine
from .postprocess import PostProcessEngines
from .sd_cpp import StableDiffusionCppEngine
from .wangp import WanGPEngine


class EngineRegistry:
    def __init__(self, store: Store, config: AppConfig):
        self.store = store
        self.config = config

    def _settings(self) -> dict[str, Any]:
        return self.store.get_setting("engines") or {}

    def profiles(self) -> dict[str, Any]:
        return self.store.get_setting("model_profiles") or {}

    def _sd_cpp_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        merged = dict(settings.get("sd_cpp") or {})
        ffmpeg = settings.get("ffmpeg") or {}
        merged.setdefault("ffmpeg_path", ffmpeg.get("binary_path", "ffmpeg"))
        return merged

    def _profile(self, profile_id: str, expected_kind: str | None = None) -> dict[str, Any]:
        profile = self.profiles().get(profile_id)
        if not profile:
            raise EngineExecutionError("MODEL_PROFILE_MISSING", f"Perfil de modelo não encontrado: {profile_id}")
        if expected_kind and profile.get("kind") != expected_kind:
            raise EngineExecutionError("MODEL_KIND_MISMATCH", f"O perfil {profile_id} não é do tipo {expected_kind}")
        return profile

    @staticmethod
    async def gpu_info() -> dict[str, Any]:
        """GPU real detectada por nvidia-smi. Sem placa, devolve available=False."""
        executable = find_executable("nvidia-smi")
        if not executable:
            return {"available": False, "detail": "nvidia-smi não encontrado; execução recai para CPU"}
        try:
            result = await run_command(
                [executable, "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader,nounits"],
                timeout=30,
            )
        except Exception as exc:
            return {"available": False, "detail": str(exc)[:300]}
        line = (result.stdout or "").splitlines()[0] if result.stdout else ""
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 4:
            return {"available": False, "detail": f"saída inesperada de nvidia-smi: {line[:200]}"}
        name, total, used, driver = parts[0], parts[1], parts[2], parts[3]
        return {
            "available": True, "name": name, "driver": driver,
            "vram_total_mib": int(float(total)), "vram_used_mib": int(float(used)),
            "label": f"{name} · {round(float(total) / 1024)} GB VRAM",
        }

    async def status_all(self) -> list[dict[str, Any]]:
        settings = self._settings()
        statuses: list[dict[str, Any]] = []
        statuses.append(await StableDiffusionCppEngine(self._sd_cpp_settings(settings)).status())
        statuses.extend(await LocalLLMEngine(settings.get("ollama") or {}, settings.get("opencode") or {}, settings.get("openrouter") or {}).status())
        statuses.extend(await PostProcessEngines(settings.get("realesrgan") or {}, settings.get("rife") or {}, settings.get("ffmpeg") or {}).status())
        statuses.append(await ComfyUIEngine(settings.get("comfyui") or {}).status())
        statuses.append(await WanGPEngine(settings.get("wangp") or {}).status())
        return statuses

    async def enhance_prompt(self, prompt: str, config: dict[str, Any], **runtime: Any) -> str:
        settings = self._settings()
        engine = LocalLLMEngine(settings.get("ollama") or {}, settings.get("opencode") or {}, settings.get("openrouter") or {})
        return await engine.enhance(
            prompt,
            provider=str(config.get("provider", "ollama")),
            model=config.get("model"),
            instruction=config.get("instruction"),
            **runtime,
        )

    async def generate_image(self, prompt: str, negative: str, output_path: Path, config: dict[str, Any], **runtime: Any) -> dict[str, Any]:
        settings = self._settings()
        engine_id = str(config.get("engine", "sd_cpp"))
        if engine_id == "sd_cpp":
            profile = self._profile(str(config.get("profile_id", "z-image-turbo-fast")), "image")
            return await StableDiffusionCppEngine(self._sd_cpp_settings(settings)).generate_image(profile, prompt, negative, output_path, config, **runtime)
        if engine_id == "comfyui":
            workflow_path = Path(str(config.get("workflow_path", ""))).expanduser().resolve()
            if not workflow_path.is_file():
                raise EngineExecutionError("COMFYUI_WORKFLOW_MISSING", "Workflow ComfyUI não encontrado", str(workflow_path))
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            files = await ComfyUIEngine(settings.get("comfyui") or {}).execute_workflow(
                workflow,
                output_path.parent,
                {"{{prompt}}": prompt, "{{negative_prompt}}": negative, "{{seed}}": int(config.get("seed", -1)), "{{width}}": int(config.get("width", 1024)), "{{height}}": int(config.get("height", 1024))},
                cancel_check=runtime.get("cancel_check"),
            )
            return {"path": str(files[0]), "paths": [str(path) for path in files], "engine": "comfyui"}
        if engine_id == "wangp":
            payload = dict(config.get("wangp_settings") or {})
            payload.setdefault("prompt", prompt)
            files = await WanGPEngine(settings.get("wangp") or {}).generate(payload, output_path.parent, output_path.parent / ".wangp-work", **runtime)
            return {"path": str(files[0]), "paths": [str(path) for path in files], "engine": "wangp"}
        raise EngineExecutionError("ENGINE_NOT_SUPPORTED", f"Engine de imagem não suportada: {engine_id}")

    async def generate_video(self, prompt: str, negative: str, output_path: Path, config: dict[str, Any], input_image: Path | None = None, **runtime: Any) -> dict[str, Any]:
        settings = self._settings()
        engine_id = str(config.get("engine", "sd_cpp"))
        if engine_id == "sd_cpp":
            profile = self._profile(str(config.get("profile_id", "wan21-t2v-1.3b-fast")), "video")
            return await StableDiffusionCppEngine(self._sd_cpp_settings(settings)).generate_video(profile, prompt, negative, output_path, config, input_image=input_image, **runtime)
        if engine_id == "wangp":
            payload = dict(config.get("wangp_settings") or {})
            payload.setdefault("prompt", prompt)
            if input_image:
                payload.setdefault("image_start", str(input_image))
            files = await WanGPEngine(settings.get("wangp") or {}).generate(payload, output_path.parent, output_path.parent / ".wangp-work", **runtime)
            return {"path": str(files[0]), "paths": [str(path) for path in files], "engine": "wangp"}
        if engine_id == "comfyui":
            workflow_path = Path(str(config.get("workflow_path", ""))).expanduser().resolve()
            if not workflow_path.is_file():
                raise EngineExecutionError("COMFYUI_WORKFLOW_MISSING", "Workflow ComfyUI não encontrado", str(workflow_path))
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            files = await ComfyUIEngine(settings.get("comfyui") or {}).execute_workflow(
                workflow,
                output_path.parent,
                {"{{prompt}}": prompt, "{{negative_prompt}}": negative, "{{seed}}": int(config.get("seed", -1)), "{{width}}": int(config.get("width", 832)), "{{height}}": int(config.get("height", 480)), "{{frames}}": int(config.get("frames", 33)), "{{input_image}}": str(input_image or "")},
                cancel_check=runtime.get("cancel_check"),
            )
            return {"path": str(files[0]), "paths": [str(path) for path in files], "engine": "comfyui"}
        raise EngineExecutionError("ENGINE_NOT_SUPPORTED", f"Engine de vídeo não suportada: {engine_id}")

    @staticmethod
    def workflow_template(name: str) -> dict[str, Any]:
        """Template de workflow ComfyUI que viaja dentro do pacote."""
        path = Path(__file__).resolve().parent.parent / "workflows" / "comfy" / f"{name}.json"
        if not path.is_file():
            raise EngineExecutionError("COMFYUI_WORKFLOW_MISSING", f"Template não encontrado: {name}", str(path))
        return {key: value for key, value in json.loads(path.read_text(encoding="utf-8")).items() if not key.startswith("_")}

    async def generate_model3d(self, image_path: Path, output_prefix: Path, config: dict[str, Any], **runtime: Any) -> dict[str, Any]:
        """Imagem para malha .glb via Hunyuan3D-2 no sidecar ComfyUI.

        A imagem é enviada ao ComfyUI porque o LoadImage lê da pasta de input dele,
        não do disco do CineNode.
        """
        settings = self._settings()
        engine = ComfyUIEngine(settings.get("comfyui") or {})
        status = await engine.status()
        if not status.get("available"):
            raise EngineExecutionError(
                "COMFYUI_UNAVAILABLE",
                "O sidecar ComfyUI não está no ar.",
                f"Suba com scripts\\run-comfy.ps1. Detalhe: {status.get('detail')}",
            )
        uploaded = await engine.upload_image(image_path)
        seed = int(config.get("seed", -1))
        if seed < 0:
            seed = int.from_bytes(os.urandom(4), "big")
        tokens = {
            "{{IMAGE_NAME}}": uploaded,
            "{{CKPT_NAME}}": str(config.get("checkpoint", "hunyuan3d-dit-v2_fp16.safetensors")),
            "{{RESOLUTION}}": int(config.get("resolution", 3072)),
            "{{SEED}}": seed,
            "{{STEPS}}": int(config.get("steps", 30)),
            "{{CFG}}": float(config.get("cfg", 5.5)),
            "{{NUM_CHUNKS}}": int(config.get("num_chunks", 8000)),
            "{{OCTREE_RESOLUTION}}": int(config.get("octree_resolution", 256)),
            "{{THRESHOLD}}": float(config.get("threshold", 0.6)),
            "{{FILENAME_PREFIX}}": f"cinenode/{output_prefix.name}",
        }
        files = await engine.execute_workflow(
            self.workflow_template("hunyuan3d-v2-image-to-mesh"),
            output_prefix.parent,
            tokens,
            cancel_check=runtime.get("cancel_check"),
        )
        meshes = [item for item in files if item.suffix.lower() in {".glb", ".gltf", ".obj", ".ply"}] or files
        return {"path": str(meshes[0]), "paths": [str(item) for item in files], "engine": "comfyui", "seed": seed}

    def comfyui(self) -> ComfyUIEngine:
        settings = self.store.get_setting("engines") or {}
        return ComfyUIEngine(settings.get("comfyui") or {})

    # ---- Pós-produção de malha. Roda em thread para não travar o loop async:
    # é CPU pura e uma decimação de 300 mil triângulos bloquearia a fila inteira.

    @staticmethod
    async def _in_thread(func, *args, **kwargs):
        import asyncio
        return await asyncio.to_thread(func, *args, **kwargs)

    async def mesh_retopology(self, source: Path, output: Path, config: dict[str, Any], **runtime: Any) -> dict[str, Any]:
        from . import mesh as mesh_ops

        def work() -> dict[str, Any]:
            loaded = mesh_ops.load_mesh(source)
            before = mesh_ops.mesh_stats(loaded)
            cleaned = mesh_ops.clean_mesh(loaded, keep_largest=str(config.get("keep_largest", "sim")) == "sim")
            simplified, report = mesh_ops.retopologize(
                cleaned,
                target_triangles=int(config.get("target_triangles", 0) or 0),
                ratio=float(config.get("ratio", 0.1) or 0.1),
                aggressiveness=int(config.get("aggressiveness", 7) or 7),
            )
            angle = float(config.get("smooth_angle", 45) or 0)
            if angle > 0:
                simplified = mesh_ops.smooth_normals(simplified, angle)
            mesh_ops.export_mesh(simplified, output)
            return {"stats_before": before, "stats_after": mesh_ops.mesh_stats(simplified), "decimation": report}

        return await self._in_thread(work)

    async def mesh_texture(self, source: Path, image: Path, output: Path, config: dict[str, Any], **runtime: Any) -> dict[str, Any]:
        from . import mesh as mesh_ops

        def work() -> dict[str, Any]:
            loaded = mesh_ops.load_mesh(source)
            unwrapped, uv_report = mesh_ops.unwrap_uv(loaded)
            textured, texture_report = mesh_ops.project_texture(
                unwrapped, image,
                resolution=int(config.get("resolution", 1024) or 1024),
                axis=str(config.get("axis", "-z")),
            )
            mesh_ops.export_mesh(textured, output)
            return {"uv": uv_report, "texture": texture_report, "stats": mesh_ops.mesh_stats(textured)}

        return await self._in_thread(work)

    async def mesh_animate(self, source: Path, output: Path, config: dict[str, Any], **runtime: Any) -> dict[str, Any]:
        from . import mesh as mesh_ops

        def work() -> dict[str, Any]:
            if source.suffix.lower() != ".glb":
                mesh_ops.export_mesh(mesh_ops.load_mesh(source), output)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(source.read_bytes())
            return mesh_ops.write_gltf_animation(
                output,
                motion=str(config.get("motion", "turntable")),
                duration=float(config.get("duration", 4) or 4),
                keyframes=int(config.get("keyframes", 48) or 48),
            )

        return await self._in_thread(work)

    async def mesh_export(self, source: Path, output: Path, **runtime: Any) -> dict[str, Any]:
        from . import mesh as mesh_ops

        def work() -> dict[str, Any]:
            loaded = mesh_ops.load_mesh(source)
            mesh_ops.export_mesh(loaded, output)
            return {"path": str(output), "stats": mesh_ops.mesh_stats(loaded), "bytes": output.stat().st_size}

        return await self._in_thread(work)

    def postprocess(self) -> PostProcessEngines:
        settings = self._settings()
        return PostProcessEngines(settings.get("realesrgan") or {}, settings.get("rife") or {}, settings.get("ffmpeg") or {})
