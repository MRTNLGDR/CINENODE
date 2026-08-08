# Relatório real de testes — Avangard CineNode Local v0.1.0

**Data:** 2026-08-06  
**Ambiente do executor:** Linux x86_64, Python 3.13.5, Node.js 22.16.0, npm 10.9.2, FFmpeg/FFprobe 7.1.3, Chromium do sistema.  
**Hardware não disponível neste executor:** Windows, Rust/Cargo, CUDA Toolkit e NVIDIA RTX 4090 Laptop.

Este relatório registra somente comandos realmente executados. Nenhum teste de geração CUDA, peso de modelo, instalador MSI/Setup.exe ou assinatura foi marcado como aprovado.

## Resumo

| Gate | Resultado | Evidência |
|---|---:|---|
| Testes Python | **28/28 aprovados** | `PYTHONPATH=source/backend pytest -q` |
| Smoke HTTP/API | **Aprovado** | saúde, criação de projeto, validação DAG e snapshot real |
| Validador de pacote | **Aprovado — 34 checks** | arquivos, JSON, Python, JS, marcadores proibidos, Unicode invisível e smoke |
| E2E Chromium | **Aprovado** | 4 telas, criação/persistência, editor, governança, viewport 1024 px |
| Console/rede no E2E | **0 erros** | `docs/screenshots/browser-e2e-report.json` |
| Python compile | **68 arquivos aprovados** | `py_compile` |
| JSON parse | **11 arquivos aprovados** | `json.loads` |
| JavaScript syntax | **Aprovado** | `node --check source/frontend/app.js` |
| Shell syntax | **Aprovado** | `bash -n` em todos os `.sh` |
| Wheel Python | **Aprovado** | 44 arquivos, instalação `--target`, `init`, `doctor` e requisitos |
| ZIP extraído em pasta limpa | **Aprovado** | 34 checks, 28/28 testes, 142 hashes, wheel e E2E |

## Comando e saída dos testes automatizados

```bash
PYTHONPATH=source/backend pytest -q
```

```text
............................                                             [100%]
28 passed in 2.41s
```

Cobertura funcional exercitada:

- migrations, `PRAGMA integrity_check`, foreign keys e persistência SQLite;
- contrato e cálculo do snapshot de governança;
- CRUD de projetos e validação do grafo;
- ordenação topológica e rejeição de ciclos;
- fila persistente, cancelamento, retry e falha acionável de engine ausente;
- recuperação de jobs `RUNNING` e retomada de jobs `QUEUED` após queda;
- upload, limite de tamanho, sanitização e path traversal;
- backup consistente, restauração atômica, remoção de WAL/SHM e ZIP Slip;
- Host/origin/Sec-Fetch-Site/token e respostas estruturadas de segurança;
- pós-processamento real por FFmpeg;
- adaptador `stable-diffusion.cpp` de AVI nativo para MP4 H.264;
- scanner de supply chain para Unicode invisível/bidirecional.

## Smoke HTTP/API

```bash
python scripts/smoke_test.py --root .
```

Resultado observado:

```json
{
  "status": "passed",
  "governance_state": "DEGRADED",
  "tasks": 18
}
```

O estado `DEGRADED` é intencional e correto: os gates de upstreams, pesos, GPU e build Tauri continuam abertos.

## Validador do codebase

```bash
python scripts/validate_package.py --root . --run-smoke
```

Resultado observado:

```json
{
  "status": "passed",
  "failures": [],
  "checks": 34
}
```

O validador verificou arquivos obrigatórios, JSON, compilação Python, sintaxe JavaScript, marcadores de implementação falsa, scanner de Unicode invisível e smoke real.

## E2E em navegador real

```bash
python scripts/browser_e2e.py --root . --screenshots docs/screenshots
```

Resultado observado:

```json
{
  "status": "passed",
  "console_errors": [],
  "network_errors": []
}
```

Fluxos exercitados:

1. abertura do dashboard;
2. criação de projeto persistente;
3. entrada no editor nodal;
4. adição de nó de texto;
5. validação do workflow;
6. salvamento do projeto;
7. abertura da governança pela rota/menu;
8. carregamento do snapshot e SSE;
9. renderização responsiva em 1024 × 768.

Capturas:

- `docs/screenshots/01-dashboard.png`
- `docs/screenshots/02-workflow.png`
- `docs/screenshots/03-governance.png`
- `docs/screenshots/04-responsive-1024.png`

## Verificações estáticas

```text
python_files_compiled: 68
json_files_parsed: 11
javascript: passed
shell_syntax: passed
```

## Dependências do executor

O comando global `python -m pip check` encontrou um conflito **pré-existente no ambiente do executor**, fora das dependências de runtime do CineNode:

```text
moviepy 2.2.1 requires pillow<12.0, but the executor has pillow 12.2.0
```

O CineNode não usa MoviePy. Para evitar reproduzir esse conflito no extra de desenvolvimento, o projeto fixa `pillow>=10,<12`. O wheel de runtime não declara Pillow nem MoviePy.

## Instalação de um clique

O teste inicial encontrou dois problemas reais no índice do executor: indisponibilidade de `setuptools` e de FastAPI. O instalador foi corrigido para:

1. preferir o wheel pré-compilado incluído no ZIP;
2. não exigir atualização de `pip`, `setuptools` ou `wheel`;
3. tentar instalação normal das dependências;
4. quando o índice estiver indisponível, detectar automaticamente `site-packages` compatíveis do Python hospedeiro;
5. instalar o wheel com `--no-deps`, validar imports/versões e falhar com mensagem acionável quando o fallback não for suficiente.

Teste real após a correção:

```text
install.sh --skip-opensources: passed
Runtime dependencies validated
cinenode init: passed
database_integrity: ok
governance tasks: 18
FFmpeg: available
```

No Windows, `install.ps1` implementa a mesma ordem e mantém instalação automática de Python/FFmpeg via Winget quando ausentes. O fluxo Windows continua aguardando validação no sistema-alvo.

## Validação do ZIP candidato extraído

O pacote foi compactado com a pasta raiz `Avangard-CineNode-Local-v0.1.0/`, extraído em `/tmp/Avangard-CineNode-Local-v0.1.0-candidate-extract/` e validado sem usar o diretório de trabalho.

Resultados reais:

```text
validate_package.py --run-smoke: passed, 34 checks
pytest: 28 passed in 2.12s
FILE_MANIFEST.sha256: 142/142 entradas aprovadas
wheel instalado do ZIP: init/doctor aprovados
database_integrity: ok
governance tasks: 18
FFmpeg: disponível
E2E Chromium: passed
console_errors: []
network_errors: []
```

O diretório de trabalho limpo e a extração retornaram 34 checks e lista de falhas vazia.

## Wheel Python

O wheel reconstruído foi inspecionado e instalado a partir do artefato, sem usar o source tree:

```text
avangard_cinenode_local-0.1.0-py3-none-any.whl
44 arquivos internos
SHA-256 final: registrado em `docs/FILE_MANIFEST.sha256`
```

Comandos funcionais após instalação `--target`:

```bash
CINENODE_HOME=/tmp/cinenode-wheel-home python -m cinenode init
CINENODE_HOME=/tmp/cinenode-wheel-home python -m cinenode doctor
```

O diagnóstico retornou integridade SQLite `ok`, 18 tarefas de governança, FFmpeg disponível e mensagens acionáveis para engines não instaladas. FastAPI, Uvicorn, Pydantic, HTTPX e python-multipart satisfizeram os intervalos declarados.

Uma tentativa inicial com `python -m venv --system-site-packages` não herdou `/opt/pyvenv/lib/python3.13/site-packages` devido ao layout customizado deste executor. Isso foi classificado como `WHEEL-ENV-001`; a instalação `--target` validou o wheel contra o interpretador ativo sem depender do source tree.

## Gates ainda não executados

- clone/materialização completa dos upstreams, porque o shell do executor não possui DNS externo;
- compilação CUDA do `stable-diffusion.cpp` e inferência com pesos reais;
- benchmark de VRAM, tempo, potência e temperatura na RTX 4090 Laptop 24 GB;
- geração real com Z-Image/Wan e validação visual 4K/8K;
- compilação e assinatura de MSI/Setup.exe Tauri no Windows;
- validação SmartScreen e instalação limpa no Alienware.

Comandos de validação no hardware-alvo estão em `docs/VALIDATION.md`.
