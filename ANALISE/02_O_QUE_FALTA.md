# O que falta — 797 pendências, agrupadas por natureza

Os ids exatos de cada pendência estão em `dados/fase_e_pendencias.json`. Este
documento agrupa por **tipo de trabalho**, porque 797 itens numa lista plana não
ajudam ninguém a decidir por onde começar.

---

## 1. Fase E por módulo, medido

| módulo | feito | total | falta | % |
|---|---|---|---|---|
| `material` | 6 | 181 | **175** | 3% |
| `garment` | 8 | 91 | **83** | 9% |
| `character` | 5 | 72 | **67** | 7% |
| `motion` | 8 | 69 | **61** | 12% |
| `game` | 0 | 54 | **54** | 0% |
| `headshot` | 7 | 56 | **49** | 12% |
| `face` | 8 | 55 | **47** | 15% |
| `connectors` | 0 | 45 | **45** | 0% |
| `rig` | 4 | 48 | **44** | 8% |
| `mesh` | 5 | 47 | **42** | 11% |
| `sculpt` | 5 | 40 | **35** | 12% |
| `formats` | 4 | 38 | **34** | 11% |
| `voice` | 0 | 31 | **31** | 0% |
| `hair` | 11 | 41 | **30** | 27% |
| **TOTAL** | **71** | **868** | **797** | **8,2%** |

---

## 2. A distinção que muda o tamanho do problema

Os 1697 microitens do PERZON **não são 1697 algoritmos**. A classificação do
próprio catálogo:

| classe | quantidade | o que é |
|---|---|---|
| `ui_property_or_action` | 695 | propriedade ou botão de interface |
| `command` | 337 | ação que dispara algo |
| `option` | 251 | opção de um seletor |
| `property` | 192 | valor configurável |
| `graph_node` | 67 | nó de grafo |
| `internal_algorithm` | **66** | **cálculo de verdade** |
| `validation_rule` | 41 | regra de validação |
| resto | 48 | diálogo, serviço, layout |

**Só 66 são algoritmo interno.** A maioria esmagadora é superfície de interface
sobre um cálculo que já existe ou que ainda não existe.

Isso reordena a prioridade: implementar os ~66 algoritmos e depois expor as
centenas de propriedades sobre eles é muito mais barato do que tratar cada
microitem como trabalho independente. **O erro caro seria construir 695 controles
de interface antes de existir o que eles controlam** — que é exatamente o que o
PERZON fez ao gerar 1697 stubs.

---

## 3. Agrupamento por natureza do trabalho

### 3.1 Já tem cálculo, falta só expor (barato)

Muitos itens pendentes são parâmetros de operações que **já rodam**. Exemplos:

- `material`: `PZ-08-exposicao`, `PZ-08-saturacao`, `PZ-08-posterizacao`,
  `PZ-08-equalizacao` são transformações de imagem sobre o mesmo pipeline de
  `material_ops` que já mede albedo e gera normal.
- `sculpt`: `PZ-07-inflar`, `PZ-07-achatar`, `PZ-07-relaxar`, `PZ-07-mover` são
  variações de deslocamento de vértice sobre a malha que `mesh_ops` já carrega e
  valida.
- `hair`: `PZ-09-alongar`, `PZ-09-encurtar`, `PZ-09-variar-espessura` operam
  sobre as guias que `hair_ops` já produz e cuja preservação de comprimento já
  está testada.

**Estimativa honesta: ~250 dos 797** caem aqui. São horas, não semanas.

### 3.2 Precisa de algoritmo novo, mas conhecido (médio)

- `mesh`: `PZ-06-morph-targets`, `PZ-06-regioes-anatomicas`, `PZ-06-colisores`.
- `rig`: `PZ-11-criar-ik`, `PZ-11-two-bone-ik`, `PZ-11-criar-twist-bones`,
  `PZ-11-heat-weights`.
- `motion`: `PZ-12-retarget`, `PZ-12-blend`, `PZ-12-crossfade`, `PZ-12-time-warp`.
- `garment`: `PZ-10-converter-mesh-em-molde-aproximado`, `PZ-10-gerar-roupa`.
- `formats`: FBX, USD, Alembic — formatos binários com especificação pública.

**~200 itens.** Cada um tem literatura e biblioteca. O trabalho é integração e
verificação, não pesquisa.

### 3.3 Depende de modelo ou serviço externo (bloqueado ou caro)

- `voice` (31): transcrição e texto-para-voz precisam de Whisper e de um TTS.
  **Nenhum dos dois está instalado.** As partes analíticas (RMS, silêncio, pitch
  por autocorrelação, visema por banda de energia) não dependem de modelo e são
  implementáveis hoje.
- `game` (54): integração com Fyrox — motor externo que não está no acervo.
- `connectors` (45): Blender, Unreal, Unity. Cada um é um bridge próprio.
- `headshot`: `PZ-04-reconstrucao-de-uma-foto` exige modelo 3DMM (FLAME, DECA).
  **Não está no disco e tem licença restritiva.**
- `garment`: `PZ-10-geracao-por-texto` exige modelo generativo.

**~150 itens.** O bloqueio é real e precisa ser declarado como tal, não
contornado com simulação.

### 3.4 Genuinamente difícil (ver `03_PROBLEMAS_DIFICEIS.md`)

**~200 itens.** Autocolisão de tecido, retarget entre esqueletos diferentes,
desdobramento UV automático de qualidade, reconstrução facial a partir de foto
única, simulação de cabelo com colisão.

---

## 4. Fora da Fase E: o backlog de infraestrutura

| id | o que falta | por quê importa |
|---|---|---|
| `GPU-TEST-001` | geração real medida no hardware alvo | 46% de falha em 50 jobs medidos |
| `MODEL-001` | baixar e validar um perfil de imagem e um de vídeo | os 4 perfis estão prontos mas não validados ponta a ponta |
| `SEC-003` | trilha de auditoria à prova de adulteração | log pode ser editado sem deixar rastro |
| `SEC-007` | sandbox dos custom nodes do ComfyUI | código de terceiro roda sem isolamento |
| `CI-001` | pipeline local (`scripts/ci.ps1`) | hoje a suíte só roda por invocação manual |
| `M-11` | SAM2, Depth Anything, DWPose | **os nós não existem**; controle visual está bloqueado |
| licenças | 3 pesos `UNKNOWN_BLOCKED` | LLaVA, Z-Image-Turbo, Hunyuan3D |
| licenças | 25 de 29 não conferidas no disco | vieram do card upstream |

---

## 5. Ordem sugerida, e o motivo

1. **Os ~66 algoritmos internos primeiro.** Cada um destrava dezenas de
   propriedades e opções que dependem dele.
2. **Depois as 695 propriedades de interface**, que passam a ser configuração de
   algo que existe.
3. **Bloqueios externos por último**, e declarados como bloqueio enquanto o
   recurso não estiver na máquina.

Construir na ordem inversa produz exatamente o que já existe: contrato exato
sobre cálculo inexistente.
