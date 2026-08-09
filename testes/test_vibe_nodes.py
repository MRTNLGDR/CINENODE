"""Nós portados do upstream Vibe-Workflow, executados com FFmpeg real."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from cinenode.engines.postprocess import PostProcessEngines
from cinenode.engines.common import EngineExecutionError

FFMPEG_MISSING = shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None
pytestmark = pytest.mark.skipif(FFMPEG_MISSING, reason="FFmpeg unavailable")


def engines() -> PostProcessEngines:
    return PostProcessEngines(
        realesrgan={"binary_path": ""},
        rife={"binary_path": ""},
        ffmpeg={"binary_path": shutil.which("ffmpeg"), "probe_path": shutil.which("ffprobe"), "timeout_seconds": 180},
    )


def probe(path: Path) -> dict:
    raw = subprocess.check_output([
        shutil.which("ffprobe"), "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,codec_name,width,height",
        "-of", "json", str(path),
    ], text=True)
    return json.loads(raw)


def make_clip(path: Path, *, color: str, seconds: float, width: int, height: int, with_audio: bool) -> Path:
    args = [shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:d={seconds}:r=12"]
    if with_audio:
        args.extend(["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "aac"])
    args.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(seconds), str(path)])
    subprocess.run(args, check=True)
    return path


@pytest.mark.asyncio
@pytest.mark.media
async def test_concat_videos_normalises_geometry(tmp_path: Path):
    first = make_clip(tmp_path / "a.mp4", color="red", seconds=1.0, width=128, height=96, with_audio=False)
    second = make_clip(tmp_path / "b.mp4", color="blue", seconds=1.0, width=64, height=64, with_audio=False)
    output = tmp_path / "combined.mp4"

    result = await engines().concat_videos([first, second], output)

    assert output.is_file()
    assert result["clips"] == 2
    assert (result["width"], result["height"]) == (128, 96)
    info = probe(output)
    video = next(item for item in info["streams"] if item["codec_type"] == "video")
    assert (video["width"], video["height"]) == (128, 96)
    # As duas fontes têm 1s cada; a saída precisa somá-las.
    assert float(info["format"]["duration"]) > 1.5


@pytest.mark.asyncio
@pytest.mark.media
async def test_concat_videos_requires_two_inputs(tmp_path: Path):
    single = make_clip(tmp_path / "only.mp4", color="green", seconds=0.5, width=64, height=64, with_audio=False)
    with pytest.raises(EngineExecutionError) as excinfo:
        await engines().concat_videos([single], tmp_path / "out.mp4")
    assert excinfo.value.code == "VIDEO_INPUT_MISSING"


@pytest.mark.asyncio
@pytest.mark.media
async def test_trim_video_cuts_requested_range(tmp_path: Path):
    source = make_clip(tmp_path / "source.mp4", color="orange", seconds=2.0, width=64, height=64, with_audio=False)
    output = tmp_path / "trim.mp4"

    result = await engines().trim_video(source, output, start_seconds=0.5, duration_seconds=0.5)

    assert output.is_file()
    assert result["start_seconds"] == 0.5
    duration = float(probe(output)["format"]["duration"])
    assert 0.3 < duration < 0.8


@pytest.mark.asyncio
@pytest.mark.media
async def test_trim_video_rejects_start_after_end(tmp_path: Path):
    source = make_clip(tmp_path / "short.mp4", color="white", seconds=1.0, width=64, height=64, with_audio=False)
    with pytest.raises(EngineExecutionError) as excinfo:
        await engines().trim_video(source, tmp_path / "out.mp4", start_seconds=30.0)
    assert excinfo.value.code == "INVALID_TRIM_RANGE"


@pytest.mark.asyncio
@pytest.mark.media
async def test_extract_audio_and_mux_round_trip(tmp_path: Path):
    with_audio = make_clip(tmp_path / "voiced.mp4", color="black", seconds=1.0, width=64, height=64, with_audio=True)
    silent = make_clip(tmp_path / "silent.mp4", color="gray", seconds=1.0, width=64, height=64, with_audio=False)
    track = tmp_path / "track.m4a"
    muxed = tmp_path / "muxed.mp4"

    await engines().extract_audio(with_audio, track, codec="aac")
    assert track.is_file()
    assert any(item["codec_type"] == "audio" for item in probe(track)["streams"])

    await engines().mux_audio(silent, track, muxed, mode="shortest", volume=0.5)
    assert muxed.is_file()
    streams = {item["codec_type"] for item in probe(muxed)["streams"]}
    assert streams == {"video", "audio"}


@pytest.mark.asyncio
@pytest.mark.media
async def test_extract_audio_reports_missing_track(tmp_path: Path):
    silent = make_clip(tmp_path / "mute.mp4", color="purple", seconds=0.5, width=64, height=64, with_audio=False)
    with pytest.raises(EngineExecutionError) as excinfo:
        await engines().extract_audio(silent, tmp_path / "out.m4a")
    assert excinfo.value.code == "AUDIO_STREAM_MISSING"
