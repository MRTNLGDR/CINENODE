# Handoff — duas IAs no mesmo repositório

Documento de coordenação. **Mescle, não sobrescreva.** Antes de editar um arquivo
listado abaixo como "de outro dono", leia o que já está lá e some.

Atualizado em 2026-08-07.

## Divisão atual

| Área | Dono | Arquivos principais |
| --- | --- | --- |
| Agente conversacional | **IA-A** | `cinenode/agent.py`, `POST /api/agent/chat`, schema `AgentChatRequest` |
| Nós de análise e acabamento | **IA-A** | `media.filmlook`, `media.scopes` em `workflow.py` + `postprocess.py` |
| Engines de geração e malha | **IA-B** | `engines/sd_cpp.py`, `engines/comfyui.py`, `engines/mesh.py`, `engines/registry.py` |
| Sidecar ComfyUI e supply chain | **IA-B** | `scripts/install-comfy.ps1`, `run-comfy.ps1`, `start-stack.ps1`, `sync_opensources.py`, `audit_upstream.py` |
| Canvas e visual | **IA-B** | `source/frontend/app.js`, `styles.css`, `glb-viewer.js` |
| Ciclo de vida de dados | **IA-B** | migração 2 em `database.py`, snapshots/coleções/exclusão em `store.py` e `api.py` |

`workflow.py`, `store.py`, `api.py` e `schemas.py` são **compartilhados**. Nós novos
entram no fim do `NODE_CATALOG`; endpoints novos, antes do bloco `/api/events`.

## Contratos que não podem quebrar

1. **Nó novo = entrada no `NODE_CATALOG` + ramo no `_execute_node`.** O agente lê o
   catálogo como fonte da verdade; um nó sem executor faz o agente propor grafo que
   falha em runtime.
2. **Toda operação que pode falhar levanta `EngineExecutionError` com código e ação.**
   Nada de retornar saída vazia como se fosse sucesso.
3. **Migração precisa constar em `MIGRATION_OBJECTS`** se criar tabela. O runner
   confere os objetos, não só o número da versão — sem isso uma migração pela metade
   fica registrada como aplicada e o banco quebra silenciosamente.
4. **Processo longo se sobe por `Win32_Process.Create`** (`start-stack.ps1`).
   `Start-Process` cria filho do console e o job morre quando o terminal fecha.
5. **Nada de rede no caminho de execução** além do que o usuário ligou explicitamente
   (OpenRouter desligado por padrão; ComfyUI é `127.0.0.1`).

## O que a IA-B entregou

- **3D completo**: `model3d.generate` (Hunyuan3D-2 via sidecar), `model3d.retopology`
  (decimação quádrica), `model3d.texture` (xatlas + projeção), `model3d.animate`
  (canais glTF TRS escritos no binário), `model3d.export`. Pipeline medido: **70,9 s**
  de imagem a malha animada texturizada.
- **Sidecar ComfyUI** instalado e versionado, com `extra_model_paths.yaml` apontando
  para `data/models/comfy` — o clone upstream fica imutável.
- **Visualizador GLB** em WebGL puro, sem dependência externa, renderização sob demanda.
- **Ciclo de vida**: snapshots de projeto com restauração não destrutiva, exclusão de
  asset em duas etapas (marcar → purgar) e coleções (biblioteca, referência, galeria).
- **Infra**: `start-stack.ps1`, instalador Tauri (MSI + NSIS), allowlist de unicode por
  repositório no manifesto, benchmark de GPU documentado.

## O que FALTA da parte da IA-B — pegue se estiver livre

Ordem de valor para o usuário, do maior para o menor.

### 1. UI de biblioteca e versionamento — backend pronto, tela não
Os endpoints existem e estão testados, mas **nenhuma tela os usa ainda**:

```
GET/POST  /api/projects/{id}/snapshots      POST /api/snapshots/{id}/restore
DELETE    /api/snapshots/{id}
DELETE    /api/assets/{id}                  POST /api/assets/{id}/restore
POST      /api/assets/{id}/purge            POST /api/assets/purge-deleted
GET/POST  /api/collections                  GET  /api/collections/{id}
POST      /api/collections/{id}/items       DELETE /api/collections/{id}/items/{asset}
GET       /api/assets?kind=&search=&deleted=
```

Falta: painel de versões no canvas (listar, restaurar, rotular), lixeira na galeria,
coleções como abas, filtro por tipo e busca. Padrão visual em `styles.css`, classes
`.float-pill`, `.nf`, `.palette-popover`.

### 2. Gerenciador de libs e modelos na interface
`scripts/model_manager.py` tem 5 bundles com SHA-256 e `verify`, mas só por linha de
comando. Falta tela em Engines para listar bundles, mostrar o que está presente,
baixar com progresso e verificar checksum. O `install_portable_engines.py` e o
`install-comfy.ps1` também deveriam ser acionáveis pela UI.

### 3. Fila com gestão de verdade
Hoje: criar, cancelar, retry. Falta: reordenar, prioridade, pausar a fila, limpar
concluídos, execução em lote e limite configurável de jobs simultâneos
(`runtime.max_parallel_gpu_jobs` existe na config e não é respeitado).

### 4. Textura 360°
`model3d.texture` faz projeção planar de vista única — o verso do objeto recebe cor
espelhada. O correto é `hunyuan3d-paint-v2` no sidecar, que já tem o cano pronto:
basta um JSON em `cinenode/workflows/comfy/` e um campo no nó.

### 5. Rigging esqueletal
`model3d.animate` faz transformação rígida do objeto. Personagem articulado com pesos
por vértice precisa de modelo dedicado. Não prometa isso como feito.

### 6. Restante do Freepik Spaces
Remover fundo (BiRefNet/RMBG), relight (IC-Light), transferência de estilo e inpaint
por ControlNet. Todos entram pelo mesmo cano do ComfyUI: um JSON de workflow mais um
nó no catálogo. Nenhum engine novo é necessário.

### 7. Assinatura dos instaladores
MSI e NSIS são gerados e funcionam, ambos `NotSigned`. Depende de certificado do
proprietário — não há o que fazer em código.

## Estado verificado agora

```
34 testes passando          validate_package: 494 checks, 0 falhas
23 nós no catálogo          engines: sd_cpp, comfyui, realesrgan, rife, ffmpeg, opencode OK
pipeline 3D: 70,9 s         ollama e openrouter dependem de configuração do usuário
```
