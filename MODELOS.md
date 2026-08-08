# Modelos — o que foi retirado deste pacote e como recolocar

Este pacote traz **o software inteiro** e nenhum peso. Os pesos somam **49.8 GB** só nos perfis de geração, mais os modelos do Ollama e do MediaPipe. Copiá-los aqui faria um pacote que ninguém consegue mover.

Nada aqui é opcional por preguiça: sem os pesos o app **sobe e funciona**, e cada nó de geração recusa com o código `MODELO_AUSENTE` dizendo exatamente qual arquivo falta e onde ele deveria estar. Isso é desenho, não defeito.


---


## 1. Onde os arquivos precisam ficar

```
data/models/
  z-image-turbo/     flux/     wan21/     wan22/     mediapipe/
```
O caminho é configurável por `CINENODE_MODELS_DIR`; o padrão é `data/models`.


## 2. Perfis de geração


### `z-image-turbo-fast` — image, 5.8 GB, 3 arquivos

| papel | arquivo | tamanho |
|---|---|---|
| `diffusion_model` | `z_image_turbo-Q3_K.gguf` | 3144 MB |
| `llm` | `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` | 2497 MB |
| `vae` | `z_image_vae.safetensors` | 168 MB |

3 de 3 estavam presentes na máquina de origem.


### `flux-fast-quantized` — image, 10.8 GB, 4 arquivos

| papel | arquivo | tamanho |
|---|---|---|
| `diffusion_model` | `flux1-schnell-Q4_K_S.gguf` | 6784 MB |
| `t5xxl` | `t5xxl-Q5_K_M.gguf` | 3387 MB |
| `vae` | `ae.safetensors` | 335 MB |
| `clip_l` | `clip_l.safetensors` | 246 MB |

4 de 4 estavam presentes na máquina de origem.


### `wan21-t2v-1.3b-fast` — video, 7.2 GB, 3 arquivos

| papel | arquivo | tamanho |
|---|---|---|
| `t5xxl` | `umt5-xxl-encoder-Q5_K_M.gguf` | 4146 MB |
| `diffusion_model` | `wan2.1_t2v_1.3B_fp16.safetensors` | 2838 MB |
| `vae` | `wan_2.1_vae.safetensors` | 254 MB |

3 de 3 estavam presentes na máquina de origem.


### `wan22-t2v-a14b-quality` — video, 26.0 GB, 4 arquivos

| papel | arquivo | tamanho |
|---|---|---|
| `diffusion_model` | `Wan2.2-T2V-A14B-LowNoise-Q5_K_M.gguf` | 10790 MB |
| `high_noise_diffusion_model` | `Wan2.2-T2V-A14B-HighNoise-Q5_K_M.gguf` | 10790 MB |
| `t5xxl` | `umt5-xxl-encoder-Q5_K_M.gguf` | 4146 MB |
| `vae` | `wan_2.1_vae.safetensors` | 254 MB |

4 de 4 estavam presentes na máquina de origem.


## 3. MediaPipe — medida facial e corporal

Dois arquivos, ~13 MB no total, e são os **únicos com licença conferida no disco** (Apache-2.0, lido no repositório upstream).

| arquivo | pasta | origem |
|---|---|---|
| `face_landmarker.task` | `data/models/mediapipe/` | storage.googleapis.com/mediapipe-models/face_landmarker |
| `pose_landmarker_full.task` | `data/models/mediapipe/` | storage.googleapis.com/mediapipe-models/pose_landmarker |

Sem eles, as 15 operações de rosto e as de medida corporal recusam com `MODELO_AUSENTE`. Todo o resto da Fase E — malha, rig, tecido, cabelo, exportação — **não depende de modelo nenhum** e roda sem baixar nada.


## 4. Ollama — 29 modelos servidos por HTTP

Não ficam em `data/models`: o Ollama guarda os dele em `~/.ollama`. Baixe com `ollama pull <nome>`.

Os que o gateway procura primeiro, em ordem de preferência:

```
visão      qwen3-vl:4b  ·  qwen2.5vl:3b  ·  moondream  ·  llava:7b
texto      qwen3:8b  ·  qwen2.5-coder  ·  deepseek-r1
embedding  nomic-embed-text
```

Estavam instalados na máquina de origem:

```
  qwen3:14b                         qwen3-coder:30b                   devstral:24b
  qwen3:1.7b                        qwen3:8b-q4_K_M                   gpt-oss-cad:20b
  qwen3-vl:4b                       qwen3:0.6b                        qwen2.5:latest
  avangard-qwen25-coder:1.5b-q4_k_m  minimax-m2:cloud                  speed-max-context:latest
  dev-power-max-context:latest      dev-power-fast:latest             speed-coder:latest
  qwen2.5-coder:1.5b                qwen2.5-coder:32b                 deepseek-coder-v2:lite
  dev-power:latest                  qwen2.5:0.5b-instruct-q8_0        deepseek-coder:6.7b
  nomic-embed-text:latest           qwen2.5-coder:latest              deepseek-coder-v2:latest
  deepseek-coder:33b                llava:13b                         deepseek-r1:32b
  llama3:latest                     gpt-oss:20b
```

---


## 5. Licença de cada família

Esta é a parte que costuma ser ignorada e é a que traz risco real: o produto é MIT e não pode redistribuir peso com termo desconhecido.

| componente | licença | uso comercial | conferida no disco |
|---|---|---|---|
| `Comfy-Org/ComfyUI` | GPL-3.0 | CONDITIONAL | sim |
| `FFmpeg/FFmpeg` | GPL-3.0 | CONDITIONAL | sim |
| `MiniMax/MiniMax-M2` | PROVIDER_API | CONDITIONAL | não — card upstream |
| `Qwen/Qwen2.5` | Apache-2.0 | YES | não — card upstream |
| `Qwen/Qwen3` | Apache-2.0 | YES | não — card upstream |
| `Qwen/Qwen3-VL` | Apache-2.0 | YES | não — card upstream |
| `Wan-AI/Wan2.1-weights` | Apache-2.0 | YES | não — card upstream |
| `Wan-AI/Wan2.2-weights` | Apache-2.0 | YES | não — card upstream |
| `black-forest-labs/FLUX.1-autoencoder` | Apache-2.0 | YES | não — card upstream |
| `black-forest-labs/FLUX.1-schnell` | Apache-2.0 | YES | não — card upstream |
| `deepseek-ai/DeepSeek-Coder` | LicenseRef-DeepSeek | CONDITIONAL | não — card upstream |
| `deepseek-ai/DeepSeek-R1` | MIT | YES | não — card upstream |
| `google/T5-v1.1-XXL` | Apache-2.0 | YES | não — card upstream |
| `hzwer/Practical-RIFE` | MIT | YES | não — card upstream |
| `leejet/stable-diffusion.cpp` | MIT | YES | não — card upstream |
| `local/derivados-qwen` | Apache-2.0 | YES | não — card upstream |
| `local/gpt-oss-cad` | Apache-2.0 | YES | não — card upstream |
| `mediapipe/face_landmarker` | Apache-2.0 | YES | sim |
| `mediapipe/pose_landmarker_full` | Apache-2.0 | YES | sim |
| `meta-llama/Meta-Llama-3` | LicenseRef-Llama3-Community | CONDITIONAL | não — card upstream |
| `mistralai/Devstral-Small` | Apache-2.0 | YES | não — card upstream |
| `nomic-ai/nomic-embed-text` | Apache-2.0 | YES | não — card upstream |
| `ollama/ollama` | MIT | YES | não — card upstream |
| `openai/CLIP-ViT-L` | MIT | YES | não — card upstream |
| `openai/gpt-oss` | Apache-2.0 | YES | não — card upstream |
| `xinntao/Real-ESRGAN` | BSD-3-Clause | YES | não — card upstream |
| `Tongyi-MAI/Z-Image-Turbo-weights` | **BLOQUEADO** | UNKNOWN | não — card upstream |
| `liuhaotian/LLaVA` | **BLOQUEADO** | UNKNOWN | não — card upstream |
| `tencent/Hunyuan3D-2-weights` | **BLOQUEADO** | UNKNOWN | não — card upstream |

**3 pesos estão `UNKNOWN_BLOCKED`** — ninguém leu a licença deles, e por isso não podem ir a produção:

- `liuhaotian/LLaVA` — ler em https://github.com/haotian-liu/LLaVA
- `Tongyi-MAI/Z-Image-Turbo-weights` — ler em https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
- `tencent/Hunyuan3D-2-weights` — ler em https://huggingface.co/tencent/Hunyuan3D-2

E **25 dos 29 componentes** têm licença vinda do card publicado pelo autor, não de um arquivo lido nesta máquina. O painel distingue as duas coisas em vez de somá-las, porque tratar pesquisa como evidência transformaria o registro de licenças em teatro.


## 6. Como conferir depois de recolocar os pesos

```bash
LIGAR.bat                                                  # sobe tudo
curl http://127.0.0.1:8787/api/model-profiles              # quais estão prontos
.runtime\venv\Scripts\python.exe scripts\verify_licenses.py  # o que falta declarar
```

`/api/model-profiles` responde `ready: false` com a lista exata de arquivos faltando por perfil. É a resposta que diz o que baixar.
