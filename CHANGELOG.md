# Changelog

## 0.1.0 — 2026-08-06

### Added
- Núcleo local FastAPI/SQLite com migrations, WAL e integridade.
- CRUD de projetos, assets, jobs, settings, backup/restauração e exportação.
- Editor nodal funcional e executor DAG topológico com detecção de ciclos.
- Fila persistente, cancelamento, retry e recuperação de jobs interrompidos.
- Adaptadores reais: stable-diffusion.cpp, WanGP, ComfyUI, Ollama, OpenCode, Real-ESRGAN, RIFE e FFmpeg.
- Perfis Z-Image Turbo e Wan 2.1 1.3B para hardware de 24 GB.
- Governança única com snapshot, tarefas, alertas, logs, changelog, polling e SSE.
- Scripts multiplataforma, Docker, Tauri 2, download de pesos com SHA-256 e acervo open source pinado.
- Instalador de um clique baseado no wheel incluído, sem upgrade obrigatório de build tools e com fallback automático validado quando o índice de pacotes está indisponível.
- Gate de supply chain com clone em quarentena, scanner de Unicode invisível, inventário de lifecycle/binários, checksums e promoção atômica.
- 28 testes automatizados, smoke HTTP, E2E Chromium, wheel e validação de pacote extraído.

### Security
- Bind loopback, validação de Host/origem/Sec-Fetch-Site, token, upload limitado, sanitização, path containment e subprocessos sem shell.
- Restore atômico remove WAL/SHM antigos; ZIP traversal e DNS rebinding possuem testes negativos.

### Known validation gates
- Compilação/assinatura do instalador Windows não executada no ambiente Linux sem Rust.
- Benchmark/generação CUDA não executados sem RTX 4090 e pesos locais.
- Clones upstream completos não materializados no executor sem DNS; scripts reproduzíveis foram incluídos.
