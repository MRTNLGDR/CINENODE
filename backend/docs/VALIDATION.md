# Gates de validação

## Executados neste ambiente

- `28` testes automatizados: banco/migrations/integridade, CRUD, DAG, fila, cancelamento, falha de engine, uploads, path traversal, FFmpeg real, backup/restauração, ZIP malicioso, segurança Host/origin/token, crash recovery, adapter AVI→MP4 e auditoria de upstream.
- Smoke HTTP com banco temporário e governança real.
- Browser E2E em Chromium: dashboard, criação/persistência de projeto, editor, validação, governança e viewport 1024 px; zero erro de console/rede.
- Python compile, JSON parse, JavaScript syntax, shell syntax e scanner de Unicode invisível.
- Wheel Python construído e instalado em diretório limpo.
- Instalação Linux de um clique validada a partir do ZIP: wheel incluído, fallback automático de dependências, `init`, `doctor`, `run.sh` e `/api/health`.
- Pacote ZIP extraído em outra pasta e revalidado.

Saídas e comandos: `TEST_REPORT.md`; capturas: `docs/screenshots/`.

## Gates impossíveis neste executor

| Gate | Limitação real | Validação exata no Alienware |
|---|---|---|
| Materializar upstreams | DNS externo bloqueado | `scripts/bootstrap-opensources.ps1` e revisar `manifest.lock.json`, `audits/`, `checksums/` |
| Build CUDA de sd.cpp | sem toolkit/GPU Windows | `scripts/install-engines.ps1 -Core`; `cinenode doctor` |
| Z-Image real | pesos/GPU ausentes | baixar bundle, rodar workflow, confirmar PNG e logs |
| Wan 2.1 real | pesos/GPU ausentes | rodar 33 frames, verificar AVI nativo→MP4, tempo e VRAM |
| 4K/8K AI real | Real-ESRGAN/RIFE portáteis ausentes | upscale/interpolação e inspeção por FFprobe/dimensões |
| Tauri MSI/Setup.exe | Rust/Cargo/Windows ausentes | `scripts/build-tauri.ps1 -Clean` |
| Assinatura | certificado ausente | assinar MSI/EXE e validar assinatura/SmartScreen |
| Benchmark térmico | RTX 4090 Laptop ausente | registrar VRAM, potência, temperatura, tempo e estabilidade |

Esses gates permanecem abertos na governança; a entrega não os marca como aprovados.
