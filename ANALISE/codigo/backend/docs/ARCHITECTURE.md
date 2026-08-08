# Architecture

## Runtime flow

```text
Browser/Tauri
    │ same-origin HTTP + SSE
    ▼
FastAPI control plane ─── /api/governance/snapshot
    │                         │
    ├── Projects/Settings     ├── tasks/alerts/changelog/logs/docs
    ├── Upload/Assets         └── SQLite source of truth
    ├── Jobs/Queue
    └── Workflow validator/executor
             │ topological order, typed ports, cancellation
             ├── Ollama/OpenCode
             ├── stable-diffusion.cpp
             ├── ComfyUI sidecar
             ├── WanGP sidecar
             ├── Real-ESRGAN NCNN
             ├── RIFE NCNN
             └── FFmpeg
                    │
                    ▼
            checksummed local assets/outputs
```

## Boundaries

- **Control plane:** lightweight Python/FastAPI, always available without GPU models.
- **Inference plane:** external binaries/processes. No model is loaded inside the web server, preventing VRAM leaks and allowing replacement.
- **Data plane:** SQLite WAL plus local filesystem. Database stores metadata and paths; large media stays in files.
- **Desktop shell:** Tauri 2 starts a frozen backend sidecar and opens the local URL.
- **Open-source archive:** immutable upstreams are outside application source; adaptations belong in `forks/` or `integrations/`.

## Workflow contract

A graph contains version, nodes, edges and metadata. Validation rejects duplicate IDs, dangling edges, self-links, unknown node types, incompatible ports and cycles. Execution uses Kahn topological ordering. Each node receives resolved upstream values and returns a typed result. Outputs become assets with SHA-256 and job/project ownership.

## Queue and recovery

One GPU job is active by default. A job moves through `QUEUED → RUNNING → SUCCEEDED|FAILED|CANCELLED`. Cancellation is checked between nodes and while subprocesses run. At startup, abandoned `RUNNING` records become `FAILED/PROCESS_INTERRUPTED`, preserving evidence instead of pretending success.

## 4K/8K strategy

1. Generate at the checkpoint's efficient base resolution.
2. Preserve seed, prompt and source artifacts.
3. Upscale stills/frames with Real-ESRGAN, using tiles when required.
4. Interpolate temporal frames with RIFE where needed.
5. Encode only once into the delivery codec.
6. Keep the intermediate master for repeatable exports.

This avoids allocating native 8K diffusion latents or long 8K video tensors on a 24 GB GPU.
