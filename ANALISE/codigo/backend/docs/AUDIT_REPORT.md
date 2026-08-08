# Auditoria final da sessão — Avangard CineNode Local v0.1.0

**Sessão:** `CORE-GENERATOR-001`  
**Data:** 2026-08-06  
**Resultado do gate geral:** **BLOQUEADO PARA APROVAÇÃO TOTAL POR LIMITAÇÕES REAIS DO EXECUTOR**

## Escopo auditado

- arquitetura local e separação de responsabilidades dos upstreams;
- backend, banco, migrations, persistência e recuperação;
- DAG, fila, jobs, cancelamento, retry e registro de assets;
- adaptadores de imagem, vídeo, LLM, upscale, interpolação e exportação;
- interface nodal e rotas operacionais;
- governança, tarefas, alertas, logs, changelog e documentos;
- segurança local, arquivos, subprocessos, backup/restauração e supply chain;
- scripts Windows/macOS/Linux, Docker, sidecar Tauri e wheel Python;
- testes automatizados, smoke, E2E, screenshots e validação de pacote;
- licenças, atribuições, pinagem e estratégia de upstreams.

## Estado anterior

Os links fornecidos não compunham um gerador completo por si só:

- OpenCode é um agente de desenvolvimento, não uma engine de mídia;
- Vibe Workflow fornece uma base de editor nodal, mas não o runtime local completo;
- Open Generative AI reúne integrações e aplicações, incluindo caminhos cloud que não atendem ao requisito offline;
- nenhum dos três resolvia sozinho fila persistente, banco, governança, instalação, 4K/8K, recuperação e engines locais.

## Estado implementado

### Núcleo funcional

- FastAPI local em loopback, SQLite WAL, migrations e integridade;
- editor DAG persistente, validação de ciclos e execução topológica;
- fila real, estados, progresso, cancelamento, retry e crash recovery;
- galeria/assets, uploads protegidos, exportação, backup e restauração;
- snapshot único em `/api/governance/snapshot`, polling, foco, SSE e botão manual;
- frontend completo sem CDN ou dependência de serviço externo;
- wheel Python, scripts multiplataforma e shell Tauri preparado.

### Engines e integração

- `stable-diffusion.cpp` como engine leve principal;
- Z-Image Turbo quantizado para imagens e Wan 2.1 1.3B para vídeo rápido;
- AVI nativo do `sd-cli` convertido por FFmpeg para MP4 H.264;
- Real-ESRGAN NCNN, RIFE NCNN e FFmpeg para pós-processamento 4K/8K;
- Ollama/OpenCode para expansão, planejamento e reparo local de workflows;
- ComfyUI como sidecar opcional;
- WanGP como integração externa opcional, sem redistribuição e com aceite de licença.

### Supply chain

- clone em quarentena;
- checkout exato de commit pinado;
- auditoria de Unicode invisível/bidirecional;
- inventário de scripts de lifecycle e binários;
- checksums de arquivos rastreados;
- promoção atômica para `Avangard One/opensources/upstream/`;
- rollback e `manifest.lock.json`;
- WanGP bloqueado sem aceite explícito.

## Falhas encontradas e corrigidas

| ID | Falha | Causa raiz | Correção |
|---|---|---|---|
| `TEST-REG-001` | fixture quebrada por nova opção | ausência de default | `allow_loopback_proxy=False` no contrato |
| `E2E-TEST-001` | timeout por `networkidle` | SSE permanente por design | `domcontentloaded` + seletores reais |
| `E2E-404-001` | recurso 404 no navegador | favicon ausente | favicon `data:` incluído |
| `PKG-REG-001` | wheel não construía | README fora da raiz Python | README sincronizado no pacote |
| `RESTORE-001` | WAL antigo sobrescrevia restore | troca incompleta do SQLite | replace atômico + remoção `-wal/-shm` |
| `SECURITY-001` | exceção escapava do middleware | lançada antes do handler | resposta JSON 401/403 no middleware |
| `ENGINE-VID-001` | `.mp4` não era saída válida do sd-cli | sd.cpp salva AVI/WebM | AVI nativo + transcode FFmpeg |
| `OSS-SUPPLY-CHAIN-001` | clone direto sem gate | risco de upstream malicioso | quarentena, scanner, inventário e promoção |
| `ENV-DEP-001` | conflito global MoviePy/Pillow | ambiente do executor | extra dev do projeto ajustado para Pillow `<12` |
| `WHEEL-ENV-001` | venv não herdou site-packages customizado | executor usa `/opt/pyvenv` sobre base `/usr/bin` | wheel validado por instalação `--target` e checagem de requisitos |
| `INSTALL-001` | upgrade obrigatório de setuptools falhou | dependência desnecessária do bootstrap | instalador passou a preferir o wheel sem upgrade |
| `INSTALL-002` | índice não forneceu FastAPI | mirror restrito do executor | fallback automático para runtime compatível do Python hospedeiro + validação de imports |

## Evidências executadas

- `28/28` testes automatizados aprovados no source e novamente no ZIP extraído;
- smoke API aprovado com 18 tarefas e estado `DEGRADED` correto;
- validador do source limpo e do ZIP extraído aprovados com 34 checks;
- 142/142 hashes internos aprovados na extração;
- wheel instalado a partir do ZIP, com `init`, `doctor` e integridade SQLite `ok`;
- `install.sh --skip-opensources` e `run.sh --no-browser` aprovados, incluindo fallback automático quando o índice não disponibilizou dependências;
- E2E Chromium aprovado no source e na extração, sem erros de console/rede;
- 4 screenshots reais;
- 68 arquivos Python compilados;
- 11 arquivos JSON parseados;
- JavaScript e shell com sintaxe aprovada.

Detalhes: `TEST_REPORT.md` e `docs/screenshots/browser-e2e-report.json`.

## Auditoria de licenças

- OpenCode, Vibe Workflow, Open Generative AI, stable-diffusion.cpp, Real-ESRGAN NCNN e RIFE NCNN: integração compatível com as atribuições registradas;
- ComfyUI: sidecar opcional sob GPL, separado do núcleo MIT;
- WanGP: licença comunitária própria restringe white-label/embedding/comercialização; não é incluído no pacote e requer aceite explícito;
- pesos e datasets mantêm licenças próprias; o gerenciador não mascara gates ou termos.

## Riscos residuais e bloqueios reais

| ID | Estado | Bloqueio |
|---|---|---|
| `OSS-SYNC-001` | BLOQUEADO | DNS externo indisponível no shell do executor |
| `MODEL-001` | BLOQUEADO | pesos grandes/gated não puderam ser materializados |
| `GPU-TEST-001` | BLOQUEADO | executor sem RTX 4090/CUDA |
| `TAURI-BUILD-001` | BLOQUEADO | executor sem Windows/Rust/Cargo/certificado |

## Resultado

O núcleo local, API, banco, DAG, interface, governança, segurança, wheel e testes estão implementados e validados no ambiente disponível. A sessão **não pode ser aprovada integralmente** porque geração real na RTX 4090, materialização dos upstreams/modelos e instalador Windows assinado dependem do hardware, rede e toolchain ausentes.
