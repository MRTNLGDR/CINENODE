# Benchmark real — GPU-TEST-001

Medições feitas nesta máquina, com os engines locais compilados aqui. Nenhum número é
estimado: tempo por nó vem do próprio job (`/api/jobs/{id}`) e as métricas de GPU são
amostras de `nvidia-smi` a cada segundo durante a execução.

Dados brutos: [`GPU_BENCHMARK.json`](GPU_BENCHMARK.json) e [`GPU_BENCHMARK_IMAGE.json`](GPU_BENCHMARK_IMAGE.json).

## Hardware medido

```
NVIDIA GeForce RTX 4090 Laptop GPU — 16.376 MiB — driver 610.88
CUDA Toolkit 13.1 · MSVC 14.44 · stable-diffusion.cpp master-813-bfbef5b-1-gc6beeef (CUDA arch 8.9)
```

> A placa é de **16 GB**, não 24 GB. Documentos anteriores do projeto citavam
> "RTX 4090 Laptop 24 GB"; o `nvidia-smi` desta máquina reporta 16.376 MiB.

## Cenário 1 — imagem 1024² + upscale 4×

Grafo: `input.text → image.generate → image.upscale`
Perfil: `z-image-turbo-fast` (Z-Image Turbo Q3_K + VAE oficial + Qwen3 4B Q4_K_M), 8 steps, seed 42.
Upscale: Real-ESRGAN `realesrgan-x4plus`, escala 4, tile 256.

| Nó | Tempo |
| --- | ---: |
| `image.generate` 1024×1024 | 27,23 s |
| `image.upscale` → 4096×4096 | 8,10 s |
| **Total** | **36,12 s** |

| Métrica (34 amostras) | Valor |
| --- | ---: |
| VRAM pico | 9.507 MiB |
| VRAM média | 4.624 MiB |
| GPU pico | 100 % |
| Temperatura pico | 73 °C |
| Potência pico | 171,3 W |
| Clock SM pico | 2.340 MHz |

Saídas: `img.png` 1.676.917 bytes (1024²) e `up-upscaled.png` 15.357.159 bytes (4096²).

## Cenário 2 — vídeo 832×480, 33 frames + RIFE + H.265

Grafo: `input.text → video.generate → video.interpolate → media.export`
Perfil: `wan21-t2v-1.3b-fast` (Wan 2.1 T2V 1.3B FP16 + VAE + UMT5-XXL Q5_K_M), 20 steps, seed 42.
Interpolação: RIFE NCNN Vulkan, 16 → 32 fps. Export: H.265 CRF 16.

| Nó | Tempo |
| --- | ---: |
| `video.generate` 832×480 · 33 frames · 20 steps | 392,49 s |
| `video.interpolate` 16 → 32 fps | 6,02 s |
| `media.export` H.265 CRF 16 | 2,01 s |
| **Total** | **400,82 s** |

| Métrica (378 amostras) | Valor |
| --- | ---: |
| VRAM pico | 15.752 MiB de 16.376 |
| VRAM média | 9.738 MiB |
| GPU pico | 100 % |
| Temperatura pico | 77 °C |
| Potência pico | 171,3 W |
| Clock SM pico | 2.355 MHz |

Saídas: `take.mp4` 322.001 bytes, `fps-interpolated.mp4` 291.238 bytes,
`benchmark-final.mp4` 261.047 bytes.

> O pico de 15.752 MiB em 16.376 MiB deixa ~600 MiB de folga. Aumentar frames ou
> resolução acima deste ponto exige offload para CPU ou um perfil menor.

## Falhas encontradas durante o benchmark

O primeiro cenário de imagem **falhou** com `ENGINE_PROCESS_FAILED` código
`3221226505` (`0xC0000409`). A causa não era VRAM:

```
_wfopen <dir do exe>\D:/.../data/engines/realesrgan-ncnn-vulkan/models/realesrgan-x4plus.param failed
```

1. **O engine estava instalado sem os pesos.** O release `v0.2.0` de
   `xinntao/Real-ESRGAN-ncnn-vulkan` publica um ZIP de 2,1 MB com 6 entradas e
   nenhuma pasta `models/`; o clone do commit pinado também não os contém. Os pesos
   ficam em `xinntao/Real-ESRGAN` v0.2.5.0, no pacote
   `realesrgan-ncnn-vulkan-20220424-windows.zip` (45,5 MB).
   `scripts/install_portable_engines.py` passou a percorrer os releases até achar um
   asset compatível e a **verificar os pesos após instalar**, falhando com erro
   acionável em vez de deixar o engine quebrado.

2. **`-m` absoluto quebra os binários ncnn-vulkan.** Eles concatenam o valor de `-m`
   ao diretório do próprio executável. `PostProcessEngines._ncnn_models_arg` passou a
   rodar com `cwd` na pasta do binário e a passar o caminho relativo, tanto para
   Real-ESRGAN quanto para RIFE.

Depois das duas correções, o upscale 512² → 2048² roda em 6,0 s e o cenário completo
de imagem conclui em 36,12 s.
