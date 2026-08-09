# CineNode

CineNode is a **local-first, modular node canvas and inference orchestration engine**. It is a separate product from PERZON. The repository contains the reusable workflow core, API, web canvas, durable job runner, portable backup layer, security boundary, engine adapters, plugin SDK, installers, tests and release verification.

## Run on Windows

Double-click `RUN_CINENODE.bat`. It installs Python 3.12 through `winget` when required, creates `.venv`, installs CineNode and opens `http://127.0.0.1:8765`.

## Run on Linux/macOS

```bash
chmod +x run.sh
./run.sh
```

## Manual development

```bash
python -m venv .venv
. .venv/bin/activate             # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
pytest --cov=cinenode
cinenode serve
```

## Local engines

CineNode discovers and controls engines through adapters. Built-in adapters cover Ollama, OpenAI-compatible local servers such as LM Studio/llama.cpp, ComfyUI and a deterministic test engine. Model weights are never committed and each optional runtime is installed separately.

## Product boundary

The local core is complete for projects, workflows, typed nodes, jobs, cache, audit, assets, backup/restore, plugins and local inference adapters. GPU/model quality depends on the installed runtime and hardware. Hosted billing, organization SSO and tenant administration are extension modules rather than falsely simulated features.

See `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md` and `docs/VERIFICATION.md`.
