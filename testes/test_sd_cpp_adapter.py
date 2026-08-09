from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

from cinenode.engines.sd_cpp import StableDiffusionCppEngine

FAKE_SD_CLI_SH = """#!/usr/bin/env bash
set -euo pipefail
out=''
fps=16
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    --fps) fps="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[[ -n "$out" ]]
ffmpeg -hide_banner -loglevel error -y -f lavfi -i color=c=blue:s=64x48:d=0.25 -r "$fps" -c:v mjpeg "$out"
"""

# CreateProcess cannot run an extension-less shell script, so Windows gets a .cmd twin.
FAKE_SD_CLI_CMD = """@echo off
setlocal
set "out="
set "fps=16"
:parse
rem [%1] distinguishes "no argument left" from a legitimately empty argument ("").
if [%1]==[] goto run
if /i "%~1"=="-o" goto setout
if /i "%~1"=="--fps" goto setfps
shift
goto parse
:setout
set "out=%~2"
shift
shift
goto parse
:setfps
set "fps=%~2"
shift
shift
goto parse
:run
if not defined out exit /b 1
ffmpeg -hide_banner -loglevel error -y -f lavfi -i color=c=blue:s=64x48:d=0.25 -r %fps% -c:v mjpeg "%out%"
"""


def _write_fake_sd_cli(tmp_path: Path) -> Path:
    if sys.platform == "win32":
        fake = tmp_path / "sd-cli.cmd"
        fake.write_text(FAKE_SD_CLI_CMD, encoding="utf-8")
        return fake
    fake = tmp_path / "sd-cli"
    fake.write_text(FAKE_SD_CLI_SH, encoding="utf-8")
    fake.chmod(0o755)
    return fake


@pytest.mark.asyncio
@pytest.mark.media
@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg unavailable")
async def test_sd_cpp_video_adapter_transcodes_native_avi(tmp_path: Path):
    fake = _write_fake_sd_cli(tmp_path)
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    output = tmp_path / "result.mp4"
    engine = StableDiffusionCppEngine(
        {"binary_path": str(fake), "ffmpeg_path": shutil.which("ffmpeg"), "timeout_seconds": 30}
    )
    result = await engine.generate_video(
        {"diffusion_model": str(model), "defaults": {"width": 64, "height": 48, "frames": 9, "fps": 20}},
        "test prompt",
        "",
        output,
        {"steps": 1, "offload_to_cpu": False},
    )
    assert output.is_file()
    assert not output.with_suffix(".native.avi").exists()
    assert result["path"] == str(output)
    assert result["transcode_command"]
    assert str(output.with_suffix(".native.avi")) in result["command"]
    probe = os.popen(f'ffprobe -v error -show_entries format=format_name -of default=nw=1:nk=1 "{output}"').read().strip()
    assert "mp4" in probe
