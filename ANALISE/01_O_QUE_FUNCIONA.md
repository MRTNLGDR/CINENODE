# O que funciona hoje, com número medido

Tudo aqui foi executado. Onde há número, ele saiu de uma execução real nesta
máquina — não de estimativa.

## 1. Geração de mídia

| pipeline | medida |
|---|---|
| imagem 1024² + upscale 4× | 36,12 s · 9.507 MiB |
| vídeo 832×480, 33 quadros, RIFE + H.265 | 400,82 s · 15.752 MiB |
| malha 3D a partir de imagem | 82,1 s · GLB de 8,9 MB |
| upscale `tile=0` contra `tile=256` | 244,9 s contra 6,0 s — **40×** |

4 perfis de modelo com pesos no disco: `z-image-turbo-fast`,
`flux-fast-quantized`, `wan21-t2v-1.3b-fast`, `wan22-t2v-a14b-quality`.

## 2. Plataforma

Servidor FastAPI em 127.0.0.1:8787, SQLite em WAL com 5 migrações versionadas e
reexecutáveis, fila de jobs com retomada (`INTERRUPTED` distinto de `FAILED`),
cache de resultado por nó com hash de entrada, SSE para atualização ao vivo,
backup e restauração com a chave de provedor removida do pacote.

Sidecars: Ollama (11434) e ComfyUI (8188), ambos por HTTP, nunca redistribuídos.

## 3. Fase E — 71 operações com cálculo real

| módulo | operações | o núcleo |
|---|---|---|
| `mesh` | 5 | diagnóstico topológico (gênero, estanqueidade), UV com distorção medida, escala canônica, simetria |
| `sculpt` | 5 | decimação quádrica com desvio medido, Taubin (2,17% de volume em 5 iterações), subdivisão, reparo, fechar buracos |
| `rig` | 4 | esqueleto de 20 juntas das medidas do corpo, peso de skin somando 1, validação |
| `material` | 6 | normal por Sobel, rugosidade por variância local, oclusão por cavidade, validação PBR, continuidade de tile |
| `motion` | 8 | apoio, deslize, travar pés (2,4 → 0,0 m/s), jitter, drift, loop, reamostragem |
| `formats` | 4 | **glTF com esqueleto, pesos e matrizes de bind**, OBJ, BVH, validador de GLB |
| `face` | 8 | 52 blendshapes ARKit, emoção por combinação FACS declarada, olhos, boca, assimetria |
| `headshot` | 7 | nitidez, exposição, frontalidade, enquadramento, alinhamento pelos olhos |
| `character` | 5 | proporção por interseção de plano, distribuição de massa, regiões, espelhar |
| `garment` | 8 | tecido PBD, molde, costura verificada, colisão, LOD |
| `hair` | 11 | raízes por área, gravidade, vento, mechas, frizz, cachos, cards |

**Pipeline completo que roda hoje:** malha crua → reparo → escala canônica → rig
→ **GLB com skin que abre em motor de jogo**. Travado num teste que executa os
cinco passos em sequência.

## 4. Governança

Fonte única em `/api/governance/snapshot`, com polling de 15 s, refetch no foco,
SSE e evento global. Alertas resolvíveis pela interface, decisões técnicas,
componentes open source e histórico de auditoria no banco.

Estado agora: 17 de 18 tarefas, 94,44%, 29 componentes registrados, 5 alertas
abertos, 1 ADR, última auditoria `APROVADA` com 493/493.

## 5. Qualidade

| medida | valor |
|---|---|
| testes | **493 passando** |
| validação de pacote | 625 checagens |
| autocommit | bloqueia commit com suíte vermelha |
