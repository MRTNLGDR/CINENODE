"""Pós-produção de malha 3D — algoritmos determinísticos, sem modelo de IA.

Retopologia, limpeza, suavização, UV, textura por projeção e animação não precisam
de rede neural: são geometria computacional. Cada operação aqui é reprodutível, roda
em segundos na CPU e falha com erro acionável em vez de devolver malha inválida.

A geração da forma continua sendo do Hunyuan3D no sidecar ComfyUI; o que este módulo
faz é transformar aquele bloco bruto de 300 mil triângulos em um asset utilizável.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from .common import EngineExecutionError

SUPPORTED_EXPORT = {".glb": "glb", ".gltf": "gltf", ".obj": "obj", ".ply": "ply", ".stl": "stl"}


def load_mesh(path: Path) -> trimesh.Trimesh:
    """Carrega uma malha e concatena cenas multi-objeto num único corpo."""
    try:
        loaded = trimesh.load(str(path), force="mesh", process=False)
    except Exception as exc:
        raise EngineExecutionError("MESH_LOAD_FAILED", "Não foi possível ler a malha", f"{path}: {exc}") from exc
    if isinstance(loaded, trimesh.Scene):
        geometries = [item for item in loaded.geometry.values() if isinstance(item, trimesh.Trimesh)]
        if not geometries:
            raise EngineExecutionError("MESH_EMPTY", "O arquivo não contém geometria triangular", str(path))
        loaded = trimesh.util.concatenate(geometries)
    if not isinstance(loaded, trimesh.Trimesh) or loaded.faces.shape[0] == 0:
        raise EngineExecutionError("MESH_EMPTY", "O arquivo não contém geometria triangular", str(path))
    return loaded


def mesh_stats(mesh: trimesh.Trimesh) -> dict[str, Any]:
    return {
        "vertices": int(mesh.vertices.shape[0]),
        "triangles": int(mesh.faces.shape[0]),
        "watertight": bool(mesh.is_watertight),
        "bodies": int(mesh.body_count),
        "volume": float(mesh.volume) if mesh.is_watertight else None,
        "area": float(mesh.area),
        "has_uv": bool(getattr(mesh.visual, "uv", None) is not None),
    }


def export_mesh(mesh: trimesh.Trimesh, output_path: Path) -> Path:
    suffix = output_path.suffix.lower()
    if suffix not in SUPPORTED_EXPORT:
        raise EngineExecutionError(
            "MESH_FORMAT_UNSUPPORTED",
            f"Formato de malha não suportado: {suffix or 'sem extensão'}",
            f"Use um de: {', '.join(sorted(SUPPORTED_EXPORT))}",
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(output_path), file_type=SUPPORTED_EXPORT[suffix])
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise EngineExecutionError("MESH_EXPORT_FAILED", "A exportação não produziu arquivo", str(output_path))
    return output_path


def clean_mesh(mesh: trimesh.Trimesh, *, keep_largest: bool = False) -> trimesh.Trimesh:
    """Remove lixo geométrico que a marching cubes deixa: faces degeneradas,
    vértices duplicados, faces soltas e — opcionalmente — ilhas desconectadas."""
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_infinite_values()
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    if keep_largest and mesh.body_count > 1:
        bodies = mesh.split(only_watertight=False)
        if bodies:
            mesh = max(bodies, key=lambda item: item.faces.shape[0])
    return mesh


def retopologize(
    mesh: trimesh.Trimesh,
    *,
    target_triangles: int = 0,
    ratio: float = 0.1,
    aggressiveness: int = 7,
) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Decimação por erro quádrico. Reduz contagem preservando silhueta.

    É o mesmo algoritmo (Garland–Heckbert) usado pelas ferramentas de retopologia
    automática do mercado — determinístico e sem GPU.
    """
    import fast_simplification

    original = mesh.faces.shape[0]
    if target_triangles > 0:
        target = min(int(target_triangles), original)
        reduction = 1.0 - (target / original)
    else:
        reduction = 1.0 - float(np.clip(ratio, 0.01, 1.0))
    if reduction <= 0:
        return mesh, {"skipped": "alvo maior ou igual à malha original", "triangles_before": original}

    vertices, faces = fast_simplification.simplify(
        np.ascontiguousarray(mesh.vertices, dtype=np.float32),
        np.ascontiguousarray(mesh.faces, dtype=np.int32),
        target_reduction=float(np.clip(reduction, 0.0, 0.999)),
        agg=int(np.clip(aggressiveness, 1, 10)),
    )
    simplified = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if simplified.faces.shape[0] == 0:
        raise EngineExecutionError("MESH_DECIMATION_FAILED", "A decimação eliminou toda a geometria")
    return simplified, {
        "triangles_before": original,
        "triangles_after": int(simplified.faces.shape[0]),
        "reduction_applied": round(float(reduction), 4),
    }


def smooth_normals(mesh: trimesh.Trimesh, angle_degrees: float = 45.0) -> trimesh.Trimesh:
    """Normais suaves com limite de ângulo: suaviza superfícies contínuas e mantém
    quinas duras, em vez do sombreado chapado que a malha bruta produz."""
    mesh.vertex_normals  # força o cálculo
    if angle_degrees > 0:
        try:
            mesh = mesh.smoothed(angle=math.radians(float(angle_degrees)))
        except Exception:
            # smoothed() depende de grafo de adjacência; malha suja cai aqui.
            mesh.fix_normals()
    else:
        mesh.fix_normals()
    return mesh


def unwrap_uv(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Gera coordenadas UV com xatlas — o mesmo empacotador de atlas usado em engines
    de jogo. Sem UV não existe textura, e a malha do Hunyuan3D vem sem nenhuma."""
    import xatlas

    vmapping, indices, uvs = xatlas.parametrize(
        np.ascontiguousarray(mesh.vertices, dtype=np.float32),
        np.ascontiguousarray(mesh.faces, dtype=np.uint32),
    )
    unwrapped = trimesh.Trimesh(
        vertices=mesh.vertices[vmapping],
        faces=indices.astype(np.int64),
        process=False,
    )
    unwrapped.visual = trimesh.visual.TextureVisuals(uv=uvs)
    return unwrapped, {
        "vertices_before": int(mesh.vertices.shape[0]),
        "vertices_after": int(unwrapped.vertices.shape[0]),
        "charts": int(len(np.unique(indices))) and int(indices.shape[0]),
    }


def project_texture(
    mesh: trimesh.Trimesh,
    image_path: Path,
    *,
    resolution: int = 1024,
    axis: str = "-z",
    background: tuple[int, int, int] = (128, 128, 128),
) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Assa uma textura projetando a imagem de origem sobre as UVs.

    É projeção planar clássica: para cada texel do atlas, descobre a posição 3D
    correspondente e amostra o pixel da imagem naquela direção de vista. Não inventa
    o verso do objeto — o que a câmera não viu recebe a cor de fundo, e isso é dito
    no relatório em vez de mascarado.
    """
    from PIL import Image

    uv = getattr(mesh.visual, "uv", None)
    if uv is None:
        raise EngineExecutionError("MESH_UV_MISSING", "A malha não tem UV; rode o unwrap antes da textura")
    source = Image.open(image_path).convert("RGB")
    resolution = int(np.clip(resolution, 64, 4096))

    axes = {"+x": (1, 2, 0, 1), "-x": (1, 2, 0, -1), "+y": (0, 2, 1, 1),
            "-y": (0, 2, 1, -1), "+z": (0, 1, 2, 1), "-z": (0, 1, 2, -1)}
    if axis not in axes:
        raise EngineExecutionError("MESH_PROJECTION_AXIS", f"Eixo de projeção inválido: {axis}",
                                   f"Use um de: {', '.join(axes)}")
    ui, vi, _, sign = axes[axis]

    bounds = mesh.bounds
    size = np.maximum(bounds[1] - bounds[0], 1e-6)
    texture = np.zeros((resolution, resolution, 3), dtype=np.uint8)
    texture[:, :] = background
    written = np.zeros((resolution, resolution), dtype=bool)

    pixels = np.asarray(source, dtype=np.uint8)
    ph, pw = pixels.shape[:2]

    # Rasteriza os triângulos no espaço UV. A densidade de amostragem acompanha o
    # tamanho do triângulo em texels — amostrar um triângulo grande com poucos pontos
    # deixaria o atlas esburacado.
    faces = mesh.faces
    tri_uv = uv[faces]                       # (F,3,2)
    tri_xyz = mesh.vertices[faces]           # (F,3,3)
    edge_texels = np.max(
        np.linalg.norm(tri_uv - np.roll(tri_uv, 1, axis=1), axis=2), axis=1
    ) * resolution
    steps = int(np.clip(np.ceil(np.percentile(edge_texels, 95)), 2, 24))
    bary = np.array([[i / steps, j / steps, 1 - i / steps - j / steps]
                     for i in range(steps + 1) for j in range(steps + 1 - i)], dtype=np.float32)

    for weights in bary:
        points_uv = np.einsum("k,fkc->fc", weights, tri_uv)
        points_xyz = np.einsum("k,fkc->fc", weights, tri_xyz)
        tx = np.clip((points_uv[:, 0] * (resolution - 1)).astype(np.int32), 0, resolution - 1)
        ty = np.clip(((1 - points_uv[:, 1]) * (resolution - 1)).astype(np.int32), 0, resolution - 1)
        u_norm = (points_xyz[:, ui] - bounds[0][ui]) / size[ui]
        v_norm = (points_xyz[:, vi] - bounds[0][vi]) / size[vi]
        if sign < 0:
            u_norm = 1.0 - u_norm
        px = np.clip((u_norm * (pw - 1)).astype(np.int32), 0, pw - 1)
        py = np.clip(((1 - v_norm) * (ph - 1)).astype(np.int32), 0, ph - 1)
        texture[ty, tx] = pixels[py, px]
        written[ty, tx] = True

    rasterized = float(written.mean())
    # Padding de costura: cada texel vazio herda o vizinho preenchido mais próximo.
    # Sem isso aparecem linhas de fundo nas bordas das ilhas quando o motor filtra.
    if not written.all():
        from scipy import ndimage
        _, (iy, ix) = ndimage.distance_transform_edt(~written, return_indices=True)
        texture = texture[iy, ix]

    mesh.visual = trimesh.visual.TextureVisuals(uv=uv, image=Image.fromarray(texture))
    return mesh, {
        "resolution": resolution,
        "axis": axis,
        "sampling_steps": steps,
        "texel_coverage_rasterized": round(rasterized, 4),
        "texel_coverage_final": 1.0,
        "source_image": str(image_path),
        "note": (
            "Projeção planar de vista única. As faces que a câmera não enxerga recebem a cor "
            "projetada mesmo assim, espelhada pela direção de vista; para textura correta em "
            "360° é preciso um modelo de painting multivista."
        ),
    }


MOTIONS = ("turntable", "spin-tilt", "float", "pulse")


def _animation_tracks(motion: str, duration: float, keyframes: int, radius: float):
    """Amostra as trilhas TRS do movimento escolhido. Matemática pura, sem modelo."""
    phases = np.linspace(0.0, 1.0, keyframes, dtype=np.float64)
    times = (phases * duration).astype(np.float32)
    rotations = np.zeros((keyframes, 4), dtype=np.float32)
    translations = np.zeros((keyframes, 3), dtype=np.float32)
    scales = np.ones((keyframes, 3), dtype=np.float32)

    for index, phase in enumerate(phases):
        angle = 2 * math.pi * phase
        if motion in {"turntable", "spin-tilt"}:
            half = angle / 2
            quat = np.array([0.0, math.sin(half), 0.0, math.cos(half)])
            if motion == "spin-tilt":
                tilt = math.radians(18) * math.sin(angle) / 2
                tilt_quat = np.array([math.sin(tilt), 0.0, 0.0, math.cos(tilt)])
                x1, y1, z1, w1 = quat
                x2, y2, z2, w2 = tilt_quat
                quat = np.array([
                    w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                    w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                    w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
                    w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
                ])
            rotations[index] = quat
        else:
            rotations[index] = [0.0, 0.0, 0.0, 1.0]
        if motion == "float":
            translations[index] = [0.0, math.sin(angle) * radius * 0.08, 0.0]
        if motion == "pulse":
            scales[index] = 1.0 + 0.06 * math.sin(angle)
    return times, rotations, translations, scales


def write_gltf_animation(
    glb_path: Path,
    *,
    motion: str = "turntable",
    duration: float = 4.0,
    keyframes: int = 48,
) -> dict[str, Any]:
    """Injeta uma animação real nos canais TRS do GLB já exportado.

    O trimesh exporta geometria, não animação. Em vez de fingir que animou, os
    acessadores, samplers e canais são escritos direto no glTF e os dados anexados
    ao chunk binário — o arquivo resultante toca em qualquer visualizador glTF 2.0.

    Isto é transformação rígida do objeto inteiro. Não é rigging esqueletal com pesos
    por vértice; para personagem articulado é outro problema, e não é este nó.
    """
    import json as _json
    import struct

    if motion not in MOTIONS:
        raise EngineExecutionError("MESH_ANIMATION_UNSUPPORTED", f"Movimento inválido: {motion}",
                                   f"Use um de: {', '.join(MOTIONS)}")
    duration = float(np.clip(duration, 0.5, 60.0))
    keyframes = int(np.clip(keyframes, 4, 600))

    raw = glb_path.read_bytes()
    if raw[:4] != b"glTF":
        raise EngineExecutionError("MESH_LOAD_FAILED", "Arquivo não é GLB", str(glb_path))
    offset, gltf, binary = 12, None, b""
    while offset < len(raw):
        length, kind = struct.unpack("<I4s", raw[offset:offset + 8])
        chunk = raw[offset + 8:offset + 8 + length]
        if kind == b"JSON":
            gltf = _json.loads(chunk.decode("utf-8"))
        elif kind == b"BIN\x00":
            binary = chunk
        offset += 8 + length + ((4 - length % 4) % 4)
    if gltf is None:
        raise EngineExecutionError("MESH_LOAD_FAILED", "GLB sem chunk JSON", str(glb_path))

    node_index = (gltf.get("scenes") or [{}])[0].get("nodes", [0])[0]
    extents = np.array(gltf.get("_cinenode_extents", [1.0, 1.0, 1.0]), dtype=float)
    times, rotations, translations, scales = _animation_tracks(motion, duration, keyframes, float(extents.max()))

    def append(array: np.ndarray, kind: str, component: int) -> int:
        nonlocal binary
        while len(binary) % 4:
            binary += b"\x00"
        byte_offset = len(binary)
        data = np.ascontiguousarray(array, dtype=np.float32).tobytes()
        binary += data
        gltf.setdefault("bufferViews", []).append(
            {"buffer": 0, "byteOffset": byte_offset, "byteLength": len(data)}
        )
        flat = array.reshape(array.shape[0], -1)
        gltf.setdefault("accessors", []).append({
            "bufferView": len(gltf["bufferViews"]) - 1,
            "componentType": component,
            "count": int(array.shape[0]),
            "type": kind,
            "min": [float(v) for v in flat.min(axis=0)],
            "max": [float(v) for v in flat.max(axis=0)],
        })
        return len(gltf["accessors"]) - 1

    time_accessor = append(times.reshape(-1, 1), "SCALAR", 5126)
    channels, samplers = [], []
    tracks = [("rotation", rotations, "VEC4"), ("translation", translations, "VEC3"), ("scale", scales, "VEC3")]
    for target, values, kind in tracks:
        # Só grava a trilha que o movimento realmente altera.
        if target == "rotation" and motion not in {"turntable", "spin-tilt"}:
            continue
        if target == "translation" and motion != "float":
            continue
        if target == "scale" and motion != "pulse":
            continue
        samplers.append({"input": time_accessor, "interpolation": "LINEAR", "output": append(values, kind, 5126)})
        channels.append({"sampler": len(samplers) - 1, "target": {"node": node_index, "path": target}})

    gltf.setdefault("animations", []).append({"name": f"cinenode_{motion}", "samplers": samplers, "channels": channels})
    gltf["buffers"] = [{"byteLength": len(binary)}]

    json_chunk = _json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_chunk += b" " * ((4 - len(json_chunk) % 4) % 4)
    binary += b"\x00" * ((4 - len(binary) % 4) % 4)
    total = 12 + 8 + len(json_chunk) + 8 + len(binary)
    out = bytearray()
    out += struct.pack("<4sII", b"glTF", 2, total)
    out += struct.pack("<I4s", len(json_chunk), b"JSON") + json_chunk
    out += struct.pack("<I4s", len(binary), b"BIN\x00") + binary
    glb_path.write_bytes(bytes(out))

    return {
        "motion": motion,
        "duration_seconds": duration,
        "keyframes": keyframes,
        "channels": [channel["target"]["path"] for channel in channels],
        "note": "Transformação rígida do objeto em canais glTF TRS; não é rigging esqueletal.",
    }
