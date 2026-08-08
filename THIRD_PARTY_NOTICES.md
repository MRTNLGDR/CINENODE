# Third-party notices

The manifest of exact upstream commits is `Avangard One/opensources/manifest.json`. `scripts/bootstrap-opensources.*` clones each exact commit into quarantine, runs the hidden-Unicode/lifecycle/binary audit, promotes only accepted source, copies its license, and creates per-file checksums. Complete upstream copies are generated on a network-enabled target and are not falsely claimed as present in this ZIP.

| Component | Pinned commit | License/status | Integration |
|---|---|---|---|
| anomalyco/opencode | `def7220bfc65b84046e597e9be772eae81f663ff` | MIT | Optional local workflow/prompt/code repair agent, normally using Ollama. |
| SamurAIGPT/Vibe-Workflow | `27059d0a3d88288b8f1fd5b51ce3f27b81a9dd46` | MIT | React Flow workflow-builder upstream for the React variant. |
| Anil-matcha/Open-Generative-AI | `a5b4ca0632129b173714261349943057da350cb7` | MIT | Tool/catalog and local adapter reference. Cloud paths are disabled by default. |
| leejet/stable-diffusion.cpp | `c6beeef35526c6dc94b74a7fb69f9d2e6a2a7a12` | MIT | Primary local CUDA/Vulkan/CPU image/video engine. |
| xinntao/Real-ESRGAN-ncnn-vulkan | `37026f49824c5cf84062e7c6a5dd71445dcf610f` | MIT | Spatial upscale. |
| nihui/rife-ncnn-vulkan | `a7532fc3f9f8f008cd6eecd6f2ffe2a9698e0cf7` | MIT | Temporal interpolation. |
| Comfy-Org/ComfyUI | `2eb609766a749e3104485979615e062e401bab97` | GPL-3.0-or-later | Optional separate local process accessed over its public HTTP API; not bundled. |
| deepbeepmeep/Wan2GP | `82d70aba1fba90f4abb3f410146594ac8aa28e60` | WanGP Community License 2.0 | Optional external installation through official Python API. Not bundled or white-labelled. Explicit acceptance required. |
| FFmpeg | system package | LGPL/GPL depending build | Decode, resize, frame extraction, mux and encoding. Inspect `ffmpeg -version` for the installed build. |
| FastAPI, Uvicorn, Pydantic, HTTPX | package manager | See installed package metadata | Local API runtime. |

## Model weights

Weights are not part of this software license. `scripts/model_manager.py` records the origin and verifies known SHA-256 values. Users must review and accept each model license, including gated repositories. The downloader does not bypass gating or model terms.

## WanGP notice

WanGP's current community license permits many internal/studio uses but restricts selling, white-labelling, embedding in a paid product, or monetizing API/SaaS/OEM access without additional permission. CineNode therefore exposes only an optional user-installed sidecar bridge and does not redistribute WanGP.
