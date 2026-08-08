# Model matrix — Alienware 18 / RTX 4090 24 GB

## Installed profiles

| Profile ID | Modality | Engine | Files | Default generation | Delivery path |
|---|---|---|---|---|---|
| `z-image-turbo-fast` | image | stable-diffusion.cpp | Z-Image Turbo Q3_K, FLUX AE, Qwen3 4B Q4_K_M | 1024×1024, 8 steps, CFG 1 | 2×/4× Real-ESRGAN then exact resize/crop to 4K or 8K |
| `wan21-t2v-1.3b-fast` | video | stable-diffusion.cpp | Wan 2.1 T2V 1.3B FP16, Wan VAE, UMT5 Q5_K_M | 832×480, 33 frames | RIFE 48/60 fps, tiled upscale, H.265/ProRes master |
| `flux-fast-quantized` | image | stable-diffusion.cpp | user-supplied FLUX GGUF + encoders | 1024 px, 4 steps | same spatial pipeline |
| `wan22-t2v-a14b-quality` | video | stable-diffusion.cpp | user-supplied Wan 2.2 dual GGUF + encoders | 832×480 | quality mode, CPU offload, long timeout |

## Recommended operating modes

### Fast preview
- Z-Image at 768–1024 px.
- Wan 1.3B at 480p and 16 fps base.
- No upscale until composition is approved.

### Final still 4K/8K
- Generate 1024–1536 px when the model allows it.
- Real-ESRGAN 2× or 4× with tiles.
- Lanczos only for the final exact delivery dimensions.
- Export PNG/TIFF/WebP lossless as appropriate.

### Final film
- Generate the shortest coherent shot possible.
- Build longer sequences from shot nodes, not one enormous latent window.
- Interpolate only after the shot is approved.
- Upscale before final codec compression.
- Use ProRes for editing/master, H.265/AV1 for delivery.

## Memory policy

- `max_parallel_gpu_jobs = 1`.
- Close or disable browser GPU acceleration during heavy generation when VRAM is constrained.
- Prefer quantized text encoders and GGUF diffusion weights.
- Use `--offload-to-cpu` and Flash Attention where supported.
- Keep models on NVMe; keep outputs and cache on a drive with sufficient free space.

## Download commands

```bash
python scripts/model_manager.py list
python scripts/model_manager.py install z-image-turbo-fast
python scripts/model_manager.py install wan21-t2v-1.3b-fast
python scripts/model_manager.py verify all
```

Known file hashes are embedded in the model manager. A mismatch aborts installation.

## Advanced optional engine

WanGP can expose larger/newer models with aggressive low-VRAM handling and its own postprocessors. It remains optional because its community license is not equivalent to MIT/Apache and restricts some productization scenarios. Install it separately only after reviewing and accepting its terms.
