"""Mapas de controle visual: contorno, profundidade, normais e estrutura.

Estes mapas são o que transforma "prompt mágico" em direção determinística de cena.
Eles alimentam ControlNet, continuidade entre planos e o pipeline 3D.

Duas famílias, com honestidade sobre a diferença:

- **Determinística** (Canny, Sobel, luminância, normais a partir de profundidade):
  matemática pura em numpy. Sem download, sem modelo, resultado idêntico toda vez.
- **Neural** (profundidade monocular): exige peso baixado e verificado. Quando o peso
  não está no disco, o nó recusa com a instrução exata de instalação — nunca devolve
  um mapa inventado.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .common import EngineExecutionError

# Limite de trabalho. Acima disso a imagem é reduzida, processada e reampliada:
# um mapa de controle não precisa de 8K para guiar a geração, e o custo explode.
MAX_LADO = 2048


# ---------------------------------------------------------------- utilidades

def carregar_rgb(caminho: Path) -> np.ndarray:
    """Lê a imagem como float32 em [0,1], já em RGB."""
    if not caminho.is_file():
        raise EngineExecutionError("IMAGEM_AUSENTE", f"Arquivo não encontrado: {caminho}")
    with Image.open(caminho) as img:
        img = img.convert("RGB")
        largura, altura = img.size
        maior = max(largura, altura)
        if maior > MAX_LADO:
            escala = MAX_LADO / maior
            img = img.resize((max(1, round(largura * escala)), max(1, round(altura * escala))),
                             Image.LANCZOS)
        return np.asarray(img, dtype=np.float32) / 255.0


def salvar_cinza(dados: np.ndarray, destino: Path) -> Path:
    """Grava um mapa de canal único como PNG de 8 bits."""
    normalizado = np.clip(dados, 0.0, 1.0)
    Image.fromarray((normalizado * 255.0 + 0.5).astype(np.uint8), mode="L").save(destino)
    return destino


def salvar_rgb(dados: np.ndarray, destino: Path) -> Path:
    normalizado = np.clip(dados, 0.0, 1.0)
    Image.fromarray((normalizado * 255.0 + 0.5).astype(np.uint8), mode="RGB").save(destino)
    return destino


def luminancia(rgb: np.ndarray) -> np.ndarray:
    """Rec.709. Usar a média dos canais escureceria o verde e clarearia o azul."""
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def _kernel_gaussiano(sigma: float) -> np.ndarray:
    raio = max(1, int(math.ceil(sigma * 3)))
    eixo = np.arange(-raio, raio + 1, dtype=np.float32)
    kernel = np.exp(-(eixo ** 2) / (2.0 * sigma * sigma))
    return kernel / kernel.sum()


def _convolucao_separavel(canal: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Gaussiana separável: O(n) por eixo em vez de O(n²) do kernel 2D."""
    raio = len(kernel) // 2
    esticado = np.pad(canal, raio, mode="edge")
    horizontal = np.zeros_like(canal)
    for deslocamento, peso in enumerate(kernel):
        horizontal += esticado[raio:raio + canal.shape[0],
                               deslocamento:deslocamento + canal.shape[1]] * peso
    esticado = np.pad(horizontal, raio, mode="edge")
    vertical = np.zeros_like(canal)
    for deslocamento, peso in enumerate(kernel):
        vertical += esticado[deslocamento:deslocamento + canal.shape[0],
                             raio:raio + canal.shape[1]] * peso
    return vertical


def borrar(canal: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return canal
    return _convolucao_separavel(canal, _kernel_gaussiano(sigma))


def _gradientes_sobel(canal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    esticado = np.pad(canal, 1, mode="edge")
    # Sobel 3x3 escrito por deslocamento de janelas: mais rápido que laço em Python.
    gx = (
        -1 * esticado[0:-2, 0:-2] + 1 * esticado[0:-2, 2:]
        - 2 * esticado[1:-1, 0:-2] + 2 * esticado[1:-1, 2:]
        - 1 * esticado[2:, 0:-2] + 1 * esticado[2:, 2:]
    )
    gy = (
        -1 * esticado[0:-2, 0:-2] - 2 * esticado[0:-2, 1:-1] - 1 * esticado[0:-2, 2:]
        + 1 * esticado[2:, 0:-2] + 2 * esticado[2:, 1:-1] + 1 * esticado[2:, 2:]
    )
    return gx, gy


# ---------------------------------------------------------------- operadores

def sobel(caminho: Path, destino: Path, *, sigma: float = 1.0) -> dict[str, Any]:
    """Magnitude do gradiente. Contorno suave, bom para SoftEdge."""
    rgb = carregar_rgb(caminho)
    cinza = borrar(luminancia(rgb), sigma)
    gx, gy = _gradientes_sobel(cinza)
    magnitude = np.hypot(gx, gy)
    pico = float(magnitude.max())
    if pico > 0:
        magnitude /= pico
    salvar_cinza(magnitude, destino)
    return {"operador": "sobel", "sigma": sigma, "pico_gradiente": round(pico, 5),
            "dimensoes": [int(cinza.shape[1]), int(cinza.shape[0])]}


def canny(
    caminho: Path,
    destino: Path,
    *,
    sigma: float = 1.4,
    limiar_baixo: float = 0.08,
    limiar_alto: float = 0.20,
) -> dict[str, Any]:
    """Canny completo: suavização, gradiente, supressão de não-máximos, histerese.

    Escrito aqui em vez de puxar OpenCV porque o projeto já tem numpy e o algoritmo
    cabe em 40 linhas — instalar 90 MB de dependência para isto seria desproporcional.
    """
    rgb = carregar_rgb(caminho)
    cinza = borrar(luminancia(rgb), sigma)
    gx, gy = _gradientes_sobel(cinza)
    magnitude = np.hypot(gx, gy)
    pico = float(magnitude.max())
    if pico <= 0:
        salvar_cinza(np.zeros_like(magnitude), destino)
        return {"operador": "canny", "aviso": "imagem sem gradiente detectável",
                "pixels_de_borda": 0}
    magnitude /= pico
    angulo = np.rad2deg(np.arctan2(gy, gx)) % 180.0

    # Supressão de não-máximos: mantém só o cume da crista de gradiente.
    fino = np.zeros_like(magnitude)
    m = np.pad(magnitude, 1, mode="constant")
    centro = m[1:-1, 1:-1]
    setores = [
        ((angulo < 22.5) | (angulo >= 157.5), m[1:-1, 0:-2], m[1:-1, 2:]),        # horizontal
        ((angulo >= 22.5) & (angulo < 67.5), m[0:-2, 2:], m[2:, 0:-2]),           # diagonal /
        ((angulo >= 67.5) & (angulo < 112.5), m[0:-2, 1:-1], m[2:, 1:-1]),        # vertical
        ((angulo >= 112.5) & (angulo < 157.5), m[0:-2, 0:-2], m[2:, 2:]),         # diagonal \
    ]
    for mascara, vizinho_a, vizinho_b in setores:
        e_cume = (centro >= vizinho_a) & (centro >= vizinho_b)
        fino[mascara & e_cume] = centro[mascara & e_cume]

    forte = fino >= limiar_alto
    fraco = (fino >= limiar_baixo) & ~forte

    # Histerese: pixel fraco só vira borda se estiver ligado a um forte. Propaga até
    # estabilizar, para uma linha longa não morrer no meio.
    resultado = forte.copy()
    for _ in range(64):
        vizinhanca = np.zeros_like(resultado)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                vizinhanca |= np.roll(np.roll(resultado, dy, axis=0), dx, axis=1)
        promovidos = fraco & vizinhanca & ~resultado
        if not promovidos.any():
            break
        resultado |= promovidos

    salvar_cinza(resultado.astype(np.float32), destino)
    return {
        "operador": "canny", "sigma": sigma,
        "limiar_baixo": limiar_baixo, "limiar_alto": limiar_alto,
        "pixels_de_borda": int(resultado.sum()),
        "proporcao_de_borda": round(float(resultado.mean()), 5),
        "dimensoes": [int(cinza.shape[1]), int(cinza.shape[0])],
    }


def normais_de_profundidade(
    profundidade: np.ndarray,
    *,
    intensidade: float = 1.0,
    espaco: str = "tangent",
) -> np.ndarray:
    """Mapa de normais a partir de um mapa de profundidade.

    A normal é o produto vetorial das derivadas da superfície. Em `tangent space` o
    canal azul aponta para fora da tela, que é a convenção que motores 3D esperam.
    """
    gx, gy = _gradientes_sobel(profundidade.astype(np.float32))
    escala = max(1e-6, intensidade)
    nx = -gx * escala
    ny = -gy * escala
    nz = np.ones_like(profundidade)
    norma = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / norma, ny / norma, nz / norma
    if espaco == "object":
        # Espaço de objeto usa o intervalo cheio; tangent remapeia para [0,1].
        return np.stack([nx, ny, nz], axis=-1)
    return np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5], axis=-1)


def normais(caminho: Path, destino: Path, *, intensidade: float = 1.0,
            sigma: float = 1.0, espaco: str = "tangent") -> dict[str, Any]:
    """Normais estimadas da luminância. É uma aproximação de relevo, não geometria
    real — para geometria real, use profundidade neural como entrada."""
    rgb = carregar_rgb(caminho)
    relevo = borrar(luminancia(rgb), sigma)
    mapa = normais_de_profundidade(relevo, intensidade=intensidade, espaco=espaco)
    salvar_rgb(mapa, destino)
    return {"operador": "normais", "origem": "luminancia", "espaco": espaco,
            "intensidade": intensidade,
            "dimensoes": [int(relevo.shape[1]), int(relevo.shape[0])]}


def estrutura(caminho: Path, destino: Path, *, sigma_detalhe: float = 1.0,
              sigma_base: float = 12.0) -> dict[str, Any]:
    """Diferença de gaussianas: separa detalhe de forma.

    É o mapa que preserva a composição de um render quando se pede foto realista,
    sem carregar a textura original junto.
    """
    rgb = carregar_rgb(caminho)
    cinza = luminancia(rgb)
    detalhe = borrar(cinza, sigma_detalhe)
    base = borrar(cinza, sigma_base)
    diferenca = detalhe - base
    amplitude = float(np.abs(diferenca).max())
    if amplitude > 0:
        diferenca = diferenca / (amplitude * 2.0) + 0.5
    else:
        diferenca = np.full_like(diferenca, 0.5)
    salvar_cinza(diferenca, destino)
    return {"operador": "estrutura", "sigma_detalhe": sigma_detalhe,
            "sigma_base": sigma_base, "amplitude": round(amplitude, 5),
            "dimensoes": [int(cinza.shape[1]), int(cinza.shape[0])]}


def limiar_adaptativo(caminho: Path, destino: Path, *, janela: int = 31,
                      offset: float = 0.02) -> dict[str, Any]:
    """Binarização por média local. Serve para planta baixa e documento escaneado,
    onde iluminação desigual arruína um limiar global."""
    rgb = carregar_rgb(caminho)
    cinza = luminancia(rgb)
    sigma = max(1.0, janela / 6.0)
    media_local = borrar(cinza, sigma)
    binario = (cinza < (media_local - offset)).astype(np.float32)
    salvar_cinza(binario, destino)
    return {"operador": "limiar_adaptativo", "janela": janela, "offset": offset,
            "proporcao_de_tinta": round(float(binario.mean()), 5),
            "dimensoes": [int(cinza.shape[1]), int(cinza.shape[0])]}


# ---------------------------------------------------------------- profundidade neural

@dataclass
class ModeloProfundidade:
    """Descreve o peso esperado. O download é feito por script, com hash verificado."""

    id: str
    arquivo: str
    entrada: int
    descricao: str


PROFUNDIDADE_DISPONIVEL: dict[str, ModeloProfundidade] = {
    "depth-anything-v2-small": ModeloProfundidade(
        id="depth-anything-v2-small",
        arquivo="depth_anything_v2_vits.onnx",
        entrada=518,
        descricao="Depth Anything V2 Small em ONNX. Rápido, roda em CPU.",
    ),
}


def profundidade(caminho: Path, destino: Path, *, modelos_dir: Path,
                 modelo: str = "depth-anything-v2-small",
                 inverter: bool = False) -> dict[str, Any]:
    """Profundidade monocular por modelo neural.

    Sem o peso no disco, recusa com a instrução exata. Nunca devolve um mapa
    aproximado fingindo ser profundidade real: um mapa errado guiaria a geração
    para a geometria errada, e isso é pior que não ter mapa nenhum.
    """
    spec = PROFUNDIDADE_DISPONIVEL.get(modelo)
    if not spec:
        raise EngineExecutionError(
            "MODELO_DESCONHECIDO",
            f"Modelo de profundidade {modelo!r} não está no registro.",
        )
    peso = Path(modelos_dir) / "vision" / spec.arquivo
    if not peso.is_file():
        raise EngineExecutionError(
            "PESO_AUSENTE",
            f"O peso {spec.arquivo} não está em {peso.parent}.",
            "Baixe com: python scripts/install_vision_models.py --model " + spec.id,
        )
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise EngineExecutionError(
            "RUNTIME_AUSENTE",
            "onnxruntime não está instalado neste ambiente.",
            hint="Instale com: .runtime\\venv\\Scripts\\pip install onnxruntime",
        ) from exc

    rgb = carregar_rgb(caminho)
    altura_original, largura_original = rgb.shape[:2]

    lado = spec.entrada
    entrada_img = Image.fromarray((rgb * 255).astype(np.uint8)).resize((lado, lado), Image.BICUBIC)
    tensor = np.asarray(entrada_img, dtype=np.float32) / 255.0
    # Normalização ImageNet, exigida pelo modelo.
    media = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    desvio = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    tensor = (tensor - media) / desvio
    tensor = np.transpose(tensor, (2, 0, 1))[None, ...].astype(np.float32)

    sessao = ort.InferenceSession(str(peso), providers=["CPUExecutionProvider"])
    nome_entrada = sessao.get_inputs()[0].name
    saida = sessao.run(None, {nome_entrada: tensor})[0]
    mapa = np.squeeze(saida).astype(np.float32)

    minimo, maximo = float(mapa.min()), float(mapa.max())
    mapa = (mapa - minimo) / (maximo - minimo) if maximo > minimo else np.zeros_like(mapa)
    if inverter:
        mapa = 1.0 - mapa

    redimensionado = np.asarray(
        Image.fromarray((mapa * 255).astype(np.uint8), mode="L")
        .resize((largura_original, altura_original), Image.BICUBIC),
        dtype=np.float32,
    ) / 255.0
    salvar_cinza(redimensionado, destino)
    return {
        "operador": "profundidade", "modelo": spec.id,
        "faixa_bruta": [round(minimo, 5), round(maximo, 5)],
        "invertido": inverter,
        "dimensoes": [int(largura_original), int(altura_original)],
    }
