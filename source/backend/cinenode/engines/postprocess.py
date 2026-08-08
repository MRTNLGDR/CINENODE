from __future__ import annotations

import json
import shutil
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any

from .common import EngineExecutionError, LogCallback, CancelCheck, find_executable, require_executable, require_file, run_command


class PostProcessEngines:
    def __init__(self, realesrgan: dict[str, Any], rife: dict[str, Any], ffmpeg: dict[str, Any]):
        self.realesrgan = realesrgan
        self.rife = rife
        self.ffmpeg = ffmpeg

    @staticmethod
    def _ncnn_models_arg(executable: str, models_path: str | None) -> tuple[str | None, Path]:
        """Resolve -m para os binários ncnn-vulkan e devolve o cwd correto.

        Os executáveis ncnn-vulkan concatenam o valor de -m ao diretório do próprio
        binário. Passar um caminho absoluto produz `<exedir>\\<caminho absoluto>` e o
        _wfopen falha. A forma suportada é rodar a partir do diretório do binário e
        passar o caminho relativo a ele.
        """
        exe_dir = Path(executable).resolve().parent
        if not models_path:
            return None, exe_dir
        resolved = Path(str(models_path)).expanduser().resolve()
        try:
            return resolved.relative_to(exe_dir).as_posix(), exe_dir
        except ValueError:
            # Fora da pasta do binário: roda a partir da raiz do caminho para manter
            # a concatenação válida.
            return resolved.name, resolved.parent

    async def status(self) -> list[dict[str, Any]]:
        statuses = []
        for engine_id, settings, key in (
            ("realesrgan", self.realesrgan, "binary_path"),
            ("rife", self.rife, "binary_path"),
            ("ffmpeg", self.ffmpeg, "binary_path"),
        ):
            executable = find_executable(settings.get(key))
            if not executable:
                statuses.append({"engine_id": engine_id, "available": False, "version": None, "detail": f"{settings.get(key)!r} não encontrado"})
                continue
            version = "installed"
            if engine_id == "ffmpeg":
                try:
                    result = await run_command([executable, "-version"], timeout=20)
                    version = result.stdout.splitlines()[0][:300]
                except Exception as exc:
                    version = str(exc)[:300]
            statuses.append({"engine_id": engine_id, "available": True, "version": version, "detail": executable})
        return statuses

    async def upscale_image(
        self,
        input_path: Path,
        output_path: Path,
        *,
        scale: int = 4,
        model: str = "realesrgan-x4plus",
        tile: int = 0,
        gpu_id: int = 0,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        executable = require_executable(self.realesrgan.get("binary_path"), "Real-ESRGAN")
        input_path = require_file(str(input_path), "input_image")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = [
            executable, "-i", str(input_path), "-o", str(output_path), "-n", model,
            "-s", str(int(scale)), "-g", str(int(gpu_id)), "-f", output_path.suffix.lstrip(".") or "png",
        ]
        models_arg, work_dir = self._ncnn_models_arg(executable, self.realesrgan.get("models_path"))
        if models_arg:
            args.extend(["-m", models_arg])
        if tile > 0:
            args.extend(["-t", str(int(tile))])
        result = await run_command(
            args,
            cwd=work_dir,
            timeout=int(self.realesrgan.get("timeout_seconds", 14400)),
            cancel_check=cancel_check,
            log=log,
        )
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "Real-ESRGAN não criou a saída", str(output_path))
        return {"path": str(output_path), "command": result.args}

    async def resize_image_ffmpeg(
        self,
        input_path: Path,
        output_path: Path,
        width: int,
        height: int,
        *,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        executable = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
        input_path = require_file(str(input_path), "input_image")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = [
            executable, "-hide_banner", "-y", "-i", str(input_path),
            "-vf", f"scale={int(width)}:{int(height)}:flags=lanczos",
            "-frames:v", "1", str(output_path),
        ]
        result = await run_command(args, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "FFmpeg não criou a imagem", str(output_path))
        return {"path": str(output_path), "command": result.args, "method": "lanczos_non_ai"}

    async def _probe_video(self, input_path: Path, *, log: LogCallback | None = None) -> dict[str, Any]:
        probe = require_executable(self.ffmpeg.get("probe_path", "ffprobe"), "FFprobe")
        result = await run_command(
            [
                probe,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=avg_frame_rate,r_frame_rate,nb_frames,width,height,duration",
                "-of", "json",
                str(input_path),
            ],
            timeout=120,
            log=log,
        )
        try:
            stream = json.loads(result.stdout)["streams"][0]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise EngineExecutionError("MEDIA_PROBE_FAILED", "FFprobe não retornou metadados de vídeo válidos", result.stdout[-2000:]) from exc

        rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1"
        try:
            source_fps = float(Fraction(str(rate)))
        except (ValueError, ZeroDivisionError):
            source_fps = 0.0
        stream["source_fps"] = source_fps
        return stream

    async def interpolate_video(
        self,
        input_path: Path,
        output_path: Path,
        *,
        target_fps: int = 60,
        engine: str = "rife",
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        input_path = require_file(str(input_path), "input_video")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        target_fps = int(target_fps)
        if target_fps < 1 or target_fps > 240:
            raise EngineExecutionError("INVALID_TARGET_FPS", "FPS alvo deve estar entre 1 e 240", str(target_fps))

        if engine == "rife":
            ffmpeg = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
            executable = require_executable(self.rife.get("binary_path"), "RIFE")
            metadata = await self._probe_video(input_path, log=log)
            source_fps = float(metadata.get("source_fps") or 0.0)
            if source_fps <= 0:
                raise EngineExecutionError("MEDIA_PROBE_FAILED", "Não foi possível determinar o FPS de origem", str(input_path))
            if target_fps <= source_fps:
                raise EngineExecutionError(
                    "INVALID_INTERPOLATION_FPS",
                    "RIFE só é usado para aumentar o FPS; escolha um FPS maior que o original ou use FFmpeg.",
                    f"source={source_fps:.3f}, target={target_fps}",
                )

            with tempfile.TemporaryDirectory(prefix="cinenode-rife-", dir=output_path.parent) as temp_dir:
                work_dir = Path(temp_dir)
                frames_in = work_dir / "frames-in"
                frames_out = work_dir / "frames-out"
                frames_in.mkdir()
                frames_out.mkdir()

                extract_args = [
                    ffmpeg, "-hide_banner", "-y", "-i", str(input_path),
                    "-vsync", "0", str(frames_in / "%08d.png"),
                ]
                await run_command(
                    extract_args,
                    timeout=int(self.ffmpeg.get("timeout_seconds", 14400)),
                    cancel_check=cancel_check,
                    log=log,
                )
                input_frames = len(list(frames_in.glob("*.png")))
                if input_frames < 2:
                    raise EngineExecutionError("MEDIA_DECODE_FAILED", "O vídeo precisa ter ao menos dois frames", str(input_path))
                target_frames = max(input_frames + 1, round(input_frames * target_fps / source_fps))

                args = [
                    executable,
                    "-i", str(frames_in),
                    "-o", str(frames_out),
                    "-n", str(target_frames),
                    "-f", "%08d.png",
                ]
                models_arg, rife_cwd = self._ncnn_models_arg(executable, self.rife.get("models_path"))
                if models_arg:
                    args.extend(["-m", models_arg])
                result = await run_command(
                    args,
                    cwd=rife_cwd,
                    timeout=int(self.rife.get("timeout_seconds", 14400)),
                    cancel_check=cancel_check,
                    log=log,
                )
                produced_frames = len(list(frames_out.glob("*.png")))
                if produced_frames < 2:
                    raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "RIFE não produziu frames interpolados", str(frames_out))

                encode_args = [
                    ffmpeg, "-hide_banner", "-y",
                    "-framerate", str(target_fps),
                    "-i", str(frames_out / "%08d.png"),
                    "-i", str(input_path),
                    "-map", "0:v:0", "-map", "1:a?",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", str(output_path),
                ]
                encode_result = await run_command(
                    encode_args,
                    timeout=int(self.ffmpeg.get("timeout_seconds", 14400)),
                    cancel_check=cancel_check,
                    log=log,
                )
                command = {"rife": result.args, "encode": encode_result.args}
        elif engine == "ffmpeg":
            executable = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
            args = [
                executable, "-hide_banner", "-y", "-i", str(input_path),
                "-vf", f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir",
                "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "copy", str(output_path),
            ]
            result = await run_command(args, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
            command = result.args
        else:
            raise EngineExecutionError("INVALID_INTERPOLATION_ENGINE", f"Engine de interpolação não suportada: {engine}")

        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "Interpolação não criou a saída", str(output_path))
        return {"path": str(output_path), "command": command, "engine": engine, "target_fps": target_fps}

    async def upscale_video(
        self,
        input_path: Path,
        output_path: Path,
        work_dir: Path,
        *,
        scale: int = 2,
        model: str = "realesrgan-x4plus",
        target_fps: int | None = None,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        ffmpeg = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
        realesrgan = require_executable(self.realesrgan.get("binary_path"), "Real-ESRGAN")
        input_path = require_file(str(input_path), "input_video")
        frames_in = work_dir / "frames-in"
        frames_out = work_dir / "frames-out"
        shutil.rmtree(work_dir, ignore_errors=True)
        frames_in.mkdir(parents=True)
        frames_out.mkdir(parents=True)
        extract = [ffmpeg, "-hide_banner", "-y", "-i", str(input_path), str(frames_in / "%08d.png")]
        await run_command(extract, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        upscale = [
            realesrgan, "-i", str(frames_in), "-o", str(frames_out), "-n", model,
            "-s", str(int(scale)), "-g", "0", "-f", "png",
        ]
        models_arg, work_cwd = self._ncnn_models_arg(realesrgan, self.realesrgan.get("models_path"))
        if models_arg:
            upscale.extend(["-m", models_arg])
        await run_command(upscale, cwd=work_cwd, timeout=int(self.realesrgan.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        fps = target_fps or 24
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode = [
            ffmpeg, "-hide_banner", "-y", "-framerate", str(int(fps)), "-i", str(frames_out / "%08d.png"),
            "-i", str(input_path), "-map", "0:v:0", "-map", "1:a?", "-c:v", "libx264", "-preset", "slow", "-crf", "15",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-shortest", str(output_path),
        ]
        result = await run_command(encode, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "Upscale de vídeo não criou saída", str(output_path))
        return {"path": str(output_path), "command": result.args, "scale": scale}

    async def concat_videos(
        self,
        inputs: list[Path],
        output_path: Path,
        *,
        width: int = 0,
        height: int = 0,
        fps: int = 0,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        """Concatenate videos with the ffmpeg concat filter.

        Sources may differ in size, frame rate and audio presence, so every input is
        normalised to a common geometry taken from the first clip before concatenation.
        """
        executable = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
        if len(inputs) < 2:
            raise EngineExecutionError("VIDEO_INPUT_MISSING", "Conecte pelo menos dois vídeos ao combinador")
        resolved = [require_file(str(item), "input_video") for item in inputs]
        first = await self._probe_video(resolved[0], log=log)
        target_width = int(width) or int(first.get("width") or 0)
        target_height = int(height) or int(first.get("height") or 0)
        if target_width <= 0 or target_height <= 0:
            raise EngineExecutionError("MEDIA_PROBE_FAILED", "Não foi possível determinar a resolução do primeiro vídeo", str(resolved[0]))
        target_fps = int(fps) or int(round(float(first.get("source_fps") or 0.0))) or 24
        # Even dimensions are required by yuv420p.
        target_width -= target_width % 2
        target_height -= target_height % 2

        args = [executable, "-hide_banner", "-y"]
        for item in resolved:
            args.extend(["-i", str(item)])
        filters = []
        for index in range(len(resolved)):
            filters.append(
                f"[{index}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
                f"setsar=1,fps={target_fps},format=yuv420p[v{index}]"
            )
        streams = "".join(f"[v{index}]" for index in range(len(resolved)))
        filters.append(f"{streams}concat=n={len(resolved)}:v=1:a=0[outv]")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args.extend([
            "-filter_complex", ";".join(filters),
            "-map", "[outv]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
            str(output_path),
        ])
        result = await run_command(args, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "FFmpeg não criou o vídeo combinado", str(output_path))
        return {
            "path": str(output_path), "command": result.args, "clips": len(resolved),
            "width": target_width, "height": target_height, "fps": target_fps,
        }

    async def trim_video(
        self,
        input_path: Path,
        output_path: Path,
        *,
        start_seconds: float = 0.0,
        duration_seconds: float = 0.0,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        executable = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
        input_path = require_file(str(input_path), "input_video")
        start = max(0.0, float(start_seconds))
        duration = float(duration_seconds)
        if duration < 0:
            raise EngineExecutionError("INVALID_TRIM_RANGE", "A duração não pode ser negativa", str(duration))
        metadata = await self._probe_video(input_path, log=log)
        source_duration = float(metadata.get("duration") or 0.0)
        if source_duration > 0 and start >= source_duration:
            raise EngineExecutionError(
                "INVALID_TRIM_RANGE",
                "O início do corte é maior que a duração do vídeo",
                f"start={start}, duration={source_duration}",
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = [executable, "-hide_banner", "-y", "-ss", f"{start:.3f}", "-i", str(input_path)]
        if duration > 0:
            args.extend(["-t", f"{duration:.3f}"])
        args.extend([
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "320k", str(output_path),
        ])
        result = await run_command(args, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "FFmpeg não criou o corte", str(output_path))
        return {"path": str(output_path), "command": result.args, "start_seconds": start, "duration_seconds": duration or None}

    async def extract_audio(
        self,
        input_path: Path,
        output_path: Path,
        *,
        codec: str = "aac",
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        executable = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
        probe = require_executable(self.ffmpeg.get("probe_path", "ffprobe"), "FFprobe")
        input_path = require_file(str(input_path), "input_media")
        streams = await run_command(
            [probe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "json", str(input_path)],
            timeout=120, log=log,
        )
        try:
            has_audio = bool(json.loads(streams.stdout).get("streams"))
        except ValueError:
            has_audio = False
        if not has_audio:
            raise EngineExecutionError("AUDIO_STREAM_MISSING", "O arquivo de origem não possui faixa de áudio", str(input_path))
        codec_args = {
            "aac": ["-c:a", "aac", "-b:a", "320k"],
            "wav": ["-c:a", "pcm_s16le"],
            "flac": ["-c:a", "flac"],
        }
        if codec not in codec_args:
            raise EngineExecutionError("INVALID_CODEC", f"Codec de áudio não suportado: {codec}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = [executable, "-hide_banner", "-y", "-i", str(input_path), "-vn", *codec_args[codec], str(output_path)]
        result = await run_command(args, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "FFmpeg não extraiu o áudio", str(output_path))
        return {"path": str(output_path), "command": result.args, "codec": codec}

    async def mux_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        *,
        mode: str = "shortest",
        volume: float = 1.0,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        executable = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
        video_path = require_file(str(video_path), "input_video")
        audio_path = require_file(str(audio_path), "input_audio")
        if mode not in {"shortest", "longest"}:
            raise EngineExecutionError("INVALID_MUX_MODE", f"Modo de mixagem não suportado: {mode}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = [
            executable, "-hide_banner", "-y",
            "-i", str(video_path), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
        ]
        if abs(float(volume) - 1.0) > 1e-6:
            args.extend(["-filter:a", f"volume={float(volume):.4f}"])
        args.extend(["-c:a", "aac", "-b:a", "320k"])
        if mode == "shortest":
            args.append("-shortest")
        args.append(str(output_path))
        result = await run_command(args, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "FFmpeg não criou o vídeo com áudio", str(output_path))
        return {"path": str(output_path), "command": result.args, "mode": mode, "volume": float(volume)}

    # Leituras técnicas de imagem. São as mesmas ferramentas de um color grading:
    # falsa cor para expor, waveform para luma, vectorscope para croma, alfa para máscara.
    SCOPE_FILTERS = {
        "waveform": "format=yuv444p,waveform=intensity=0.1:mirror=1:components=7:display=overlay,scale=1024:-2",
        "vectorscope": "format=yuv444p,vectorscope=mode=color3:intensity=0.15,scale=1024:1024",
        "histograma": "format=yuv444p,histogram=display_mode=overlay:levels_mode=logarithmic,scale=1024:-2",
        "preto e branco": "format=gray,scale=1024:-2",
        # Falsa cor: mapeia luminância em faixas para caçar clipping e subexposição.
        # Sem format=gray antes: o pseudocolor escreve nos planos do formato de
        # entrada, e um formato de plano único sai cinza — medido, 0% de pixels coloridos.
        "falsa cor": "pseudocolor=preset=turbo,scale=1024:-2",
        "falsa cor (faixas)": "pseudocolor=preset=range2,scale=1024:-2",
        "alfa": "alphaextract,format=gray,scale=1024:-2",
    }

    async def render_scope(
        self,
        input_path: Path,
        output_path: Path,
        *,
        mode: str = "falsa cor",
        frame_seconds: float = 0.0,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        executable = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
        input_path = require_file(str(input_path), "input_media")
        chain = self.SCOPE_FILTERS.get(mode)
        if not chain:
            raise EngineExecutionError("INVALID_SCOPE_MODE", f"Leitura não suportada: {mode}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = [executable, "-hide_banner", "-y"]
        if float(frame_seconds) > 0:
            args.extend(["-ss", f"{float(frame_seconds):.3f}"])
        args.extend(["-i", str(input_path), "-vf", chain, "-frames:v", "1", str(output_path)])
        try:
            result = await run_command(args, timeout=int(self.ffmpeg.get("timeout_seconds", 3600)), cancel_check=cancel_check, log=log)
        except EngineExecutionError as exc:
            if mode == "alfa":
                raise EngineExecutionError(
                    "ALPHA_CHANNEL_MISSING",
                    "A fonte não tem canal alfa para extrair.",
                    str(input_path),
                ) from exc
            raise
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "FFmpeg não gerou a leitura", str(output_path))
        return {"path": str(output_path), "command": result.args, "mode": mode}

    async def film_look(
        self,
        input_path: Path,
        output_path: Path,
        *,
        grain: float = 12,
        motion_blur: int = 0,
        vignette: bool = False,
        saturation: float = 1.0,
        contrast: float = 1.0,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        """Acabamento real, aplicado no arquivo — não é descrição no prompt."""
        executable = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
        input_path = require_file(str(input_path), "input_video")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chain: list[str] = []
        if int(motion_blur) > 1:
            # tmix mistura N quadros: é o borrão de obturador longo, não um blur gaussiano.
            chain.append(f"tmix=frames={int(motion_blur)}:weights='{' '.join(['1'] * int(motion_blur))}'")
        if abs(float(contrast) - 1) > 1e-6 or abs(float(saturation) - 1) > 1e-6:
            chain.append(f"eq=contrast={float(contrast):.3f}:saturation={float(saturation):.3f}")
        if vignette:
            chain.append("vignette=PI/5")
        if float(grain) > 0:
            chain.append(f"noise=alls={int(grain)}:allf=t+u")
        chain.append("format=yuv420p")
        args = [
            executable, "-hide_banner", "-y", "-i", str(input_path),
            "-vf", ",".join(chain),
            "-c:v", "libx264", "-preset", "slow", "-crf", "16",
            "-c:a", "copy", str(output_path),
        ]
        result = await run_command(args, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "FFmpeg não gerou o acabamento", str(output_path))
        return {"path": str(output_path), "command": result.args, "grain": grain, "motion_blur": motion_blur}

    async def export_media(
        self,
        input_path: Path,
        output_path: Path,
        *,
        codec: str = "h264",
        crf: int = 16,
        fps: int | None = None,
        cancel_check: CancelCheck | None = None,
        log: LogCallback | None = None,
    ) -> dict[str, Any]:
        executable = require_executable(self.ffmpeg.get("binary_path", "ffmpeg"), "FFmpeg")
        input_path = require_file(str(input_path), "input_media")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        codec_args = {
            "h264": ["-c:v", "libx264", "-preset", "slow", "-crf", str(int(crf)), "-pix_fmt", "yuv420p"],
            "h265": ["-c:v", "libx265", "-preset", "slow", "-crf", str(int(crf)), "-pix_fmt", "yuv420p10le"],
            "prores": ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"],
            "av1": ["-c:v", "libsvtav1", "-crf", str(int(crf)), "-preset", "6", "-pix_fmt", "yuv420p10le"],
        }
        if codec not in codec_args:
            raise EngineExecutionError("INVALID_CODEC", f"Codec não suportado: {codec}")
        args = [executable, "-hide_banner", "-y", "-i", str(input_path)]
        if fps:
            args.extend(["-r", str(int(fps))])
        args.extend(codec_args[codec])
        args.extend(["-c:a", "aac", "-b:a", "320k", str(output_path)])
        result = await run_command(args, timeout=int(self.ffmpeg.get("timeout_seconds", 14400)), cancel_check=cancel_check, log=log)
        if not output_path.is_file():
            raise EngineExecutionError("ENGINE_OUTPUT_MISSING", "Exportação não criou saída", str(output_path))
        return {"path": str(output_path), "command": result.args, "codec": codec}
