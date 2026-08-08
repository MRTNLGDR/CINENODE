# Relatório real de testes — Avangard CineNode Local v0.1.0

**Data:** 2026-08-06
**Ambiente do executor:** Windows 11 Pro 26200, Python 3.12.6, Node.js 22, FFmpeg 8.0.1,
Chromium do Playwright, MSVC 14.44, CUDA Toolkit 13.1, rustc 1.97.1.
**GPU:** NVIDIA GeForce RTX 4090 **Laptop** — 16.376 MiB — driver 610.88.

Este relatório registra somente comandos realmente executados nesta máquina. Onde algo
não foi feito, está dito que não foi feito.

> **Correção de escopo.** A revisão anterior deste arquivo descrevia um executor Linux
> sem Windows, sem Rust/Cargo, sem CUDA e sem GPU, e por isso deixava quatro gates
> abertos. Esta revisão foi produzida em uma máquina que tem tudo isso, e três daqueles
> gates foram fechados com evidência. A GPU é de **16 GB**, não 24 GB como se afirmava.

## Resumo

| Gate | Resultado | Evidência |
|---|---:|---|
| Testes Python | **34/34 aprovados** | `.runtime\venv\Scripts\python -m pytest -q` |
| Validador de pacote + smoke | **Aprovado — 494 checks, 0 falhas** | `scripts/validate_package.py --root . --run-smoke` |
| SQLite `integrity_check` | **ok** | `python -m cinenode doctor` |
| E2E Chromium | **Aprovado — 0 erro de console, 0 erro de rede** | `scripts/browser_e2e.py` |
| Geração de imagem local | **Aprovada** | Z-Image Turbo, 1024², 8 steps |
| Geração de vídeo local | **Aprovada** | Wan 2.1 T2V 1.3B, 832×480, 33 frames |
| Upscale AI | **Aprovado** | Real-ESRGAN 4× → 4096² |
| Interpolação | **Aprovada** | RIFE 16 → 32 fps |
| Exportação | **Aprovada** | H.265 CRF 16 |
| Benchmark de GPU | **Aprovado** | `docs/GPU_BENCHMARK.md` |
| Instalador nativo | **Construído, não assinado** | MSI + NSIS, `Get-AuthenticodeSignature` = `NotSigned` |
| Acervo open source | **5 promovidos, 2 em quarentena, 1 por licença** | `Avangard One/opensources/manifest.lock.json` |

## Engines detectados

```
sd_cpp      OK   data\engines\stable-diffusion.cpp\bin\sd-cli.exe (CUDA arch 8.9)
ollama      OK   http://127.0.0.1:11434 — 0.32.5, qwen3:8b-q4_K_M
opencode    OK   npm global
realesrgan  OK   data\engines\realesrgan-ncnn-vulkan\realesrgan-ncnn-vulkan.exe
rife        OK   data\engines\rife-ncnn-vulkan\rife-ncnn-vulkan.exe
ffmpeg      OK   8.0.1-full_build
comfyui     AUSENTE  rejeitado pelo gate de unicode invisível; opcional
wangp       AUSENTE  exige aceite explícito da licença comunitária
```

## Geração real medida

Detalhes e métricas de VRAM, temperatura e potência em [`docs/GPU_BENCHMARK.md`](docs/GPU_BENCHMARK.md).

| Cenário | Tempo | VRAM pico |
|---|---:|---:|
| Imagem 1024² + upscale 4× → 4096² | 36,12 s | 9.507 MiB |
| Vídeo 832×480 · 33 frames · 20 steps + RIFE + H.265 | 400,82 s | 15.752 MiB |

Workflow com os nós portados do Vibe-Workflow, executado de ponta a ponta:
`input.text ×2 → text.concat → video.generate ×2 → video.concat → video.trim → output.preview`
concluiu em 75,3 s e produziu `cut-trimmed.mp4` (h264, 320×192, 11 frames, 0,687 s).

## Suíte automatizada

34 testes, incluindo 6 novos que exercitam os nós portados com FFmpeg real
(`tests/test_vibe_nodes.py`): concatenação com normalização de geometria, recusa de
entrada única, corte por faixa, recusa de início fora do vídeo, extração de áudio,
mixagem e detecção de faixa de áudio ausente.

## Defeitos reais corrigidos nesta sessão

| Onde | Defeito | Correção |
|---|---|---|
| `cinenode/backup.py` | `sqlite3` como context manager não fecha a conexão; no Windows o diretório temporário não podia ser removido | `contextlib.closing` nas três conexões |
| `cinenode/backup.py` | `os.fsync` em handle aberto como `rb` falha no Windows | abre como `rb+` |
| `scripts/sync_opensources.py` | `shutil.rmtree` falha em pack files read-only do git | handler que limpa o atributo e repete |
| `scripts/sync_opensources.py` | submódulos com URL `git@github.com:` sem chave SSH | reescrita para HTTPS via `GIT_CONFIG_*` |
| `scripts/install_portable_engines.py` | `argparse` rejeita o default de lista com `choices`, quebrando a chamada sem argumentos | default removido |
| `scripts/install_portable_engines.py` | release do Real-ESRGAN sem `models/`; engine instalado quebrado | busca release com asset compatível + verificação pós-instalação |
| `cinenode/engines/postprocess.py` | `-m` absoluto é concatenado ao diretório do binário ncnn-vulkan | `cwd` no diretório do binário e caminho relativo |
| `scripts/validate_package.py` | validava os clones upstream de terceiros e nunca passava | escopo restrito ao pacote |
| `scripts/install-engines.ps1` | CMake escolhia Ninja+MinGW e o nvcc recusava | gerador Visual Studio fixado |
| `scripts/install-engines.ps1` | front-end do servidor de exemplo derrubava o build | compila apenas o alvo `sd-cli` |
| `source/desktop/src-tauri` | `icons/icon.ico` ausente impedia o `tauri-build` | conjunto de ícones gerado |
| `scripts/model_manager.py` | VAE do Z-Image vinha de repositório gated | VAE oficial público |
| `tests/test_sd_cpp_adapter.py` | fixture só funcionava em POSIX | equivalente `.cmd` no Windows |

## O que continua em aberto

* **Assinatura dos instaladores.** MSI e NSIS existem e funcionam; ambos `NotSigned`.
  Depende de certificado de code signing do proprietário.
* **ComfyUI e OpenCode.** Barrados pelo gate de unicode invisível do próprio projeto —
  as ocorrências são documentação traduzida (tailandês, árabe, russo, bósnio, dinamarquês)
  e sequências ZWJ de emoji em testes. Promovê-los é decisão do proprietário.
* **WanGP.** Exige aceite explícito da licença comunitária.
* **macOS e Linux.** Não validados nesta máquina.
* **Docker.** Daemon presente, mas a imagem não foi construída nem executada aqui.
