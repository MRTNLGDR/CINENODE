# CineNode

Canvas nodal **local-first** para organizar e executar fluxos de cinema, imagem, vídeo, áudio, automação e IA local.

> **Separação obrigatória:** CineNode e PERZON são produtos distintos. Este repositório **não contém** código, rotas, operações, backlog ou métricas do PERZON. Uma integração futura deve acontecer por API/plugin versionado, sem fundir os dois sistemas.

## O que já funciona

- canvas visual sem dependências JavaScript externas;
- projetos e workflows persistidos em SQLite/WAL;
- validação de grafo tipado e detecção de ciclos;
- fila de jobs, cancelamento, interrupção e retomada;
- eventos de execução e acompanhamento pela interface;
- upload e download de assets com SHA-256;
- nós reais de texto, JSON, matemática, condição e utilidades;
- leitura de imagens com Pillow;
- `ffprobe` e transcodificação via FFmpeg;
- chat local via Ollama;
- envio de workflows API JSON ao ComfyUI;
- API FastAPI documentada em `/docs`;
- execução restrita ao computador local por padrão.

CineNode não devolve mídia falsa quando uma engine está ausente. O job falha com um código acionável, como `FFMPEG_MISSING`, `OLLAMA_FAILED` ou `COMFY_WORKFLOW_REQUIRED`.

## Windows — um clique

1. Baixe ou clone o repositório.
2. Execute `RUN_CINENODE.bat`.
3. O script instala Python 3.12 pelo `winget` quando necessário, cria `.venv`, instala o núcleo e abre `http://127.0.0.1:8787`.

Para instalar também FFmpeg, Ollama e o código do ComfyUI:

```powershell
.\INSTALL_CINENODE.bat -WithEngines
```

Também é possível instalar separadamente:

```powershell
.\INSTALL_CINENODE.bat -WithFFmpeg
.\INSTALL_CINENODE.bat -WithOllama
.\INSTALL_CINENODE.bat -WithComfyUI
```

Pesos de modelos não são baixados silenciosamente. Modelos possuem tamanhos, licenças e requisitos de VRAM diferentes e devem ser escolhidos conscientemente no Ollama ou ComfyUI.

## Linux

```bash
chmod +x install.sh run.sh
./install.sh
./run.sh
```

## Desenvolvimento

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[test]"
pytest -q
python -m build
cinenode doctor
cinenode run
```

## Nós incluídos

| Categoria | Nós |
|---|---|
| Entrada | texto, número, JSON e arquivo |
| Texto | template e concatenação |
| Lógica | soma, multiplicação, condição e merge JSON |
| Utilitário | atraso cancelável |
| Mídia | análise de imagem, ffprobe e transcodificação FFmpeg |
| IA local | Ollama Chat e workflow ComfyUI |
| Saída | texto e JSON |

## ComfyUI

Exporte um workflow no formato **API JSON**, coloque-o no parâmetro `workflow` do nó `ComfyUI Workflow` e use `{{prompt}}` em qualquer campo textual que deva receber o prompt conectado.

O ComfyUI continua sendo um sidecar independente em `127.0.0.1:8188`; ele não é incorporado ao servidor CineNode.

## Dados locais

Por padrão, todos os dados ficam em `runtime/`:

```text
runtime/
├── cinenode.sqlite3
├── uploads/
├── outputs/
└── logs/
```

A variável `CINENODE_HOME` muda essa pasta. Caminhos de assets são relativos ao workspace, permitindo mover a instalação sem gravar paths absolutos no banco.

## Segurança

- bind padrão em `127.0.0.1`;
- middleware rejeita clientes e `Host` externos;
- integrações HTTP aceitam somente destinos de loopback;
- upload possui limite configurável;
- subprocessos são executados sem shell;
- segredos, bancos, outputs, modelos e `.env` não são versionados.

Não exponha a porta do CineNode na internet sem autenticação, TLS, proxy reverso e uma revisão de segurança específica.

## Estrutura

```text
src/cinenode/
├── api.py          # API, assets e frontend
├── db.py           # SQLite e persistência relocável
├── workflow.py     # validação e execução DAG
├── jobs.py         # fila, cancelamento e retomada
├── engines.py      # FFmpeg, Ollama e ComfyUI
├── catalog.py      # contrato dos nós
└── static/         # canvas visual
```

Documentação adicional está em `docs/`.
