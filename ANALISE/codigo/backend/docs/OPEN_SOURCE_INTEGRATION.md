# Integração open source

## Responsabilidade de cada upstream solicitado

### OpenCode
Agente local de aprimoramento/reparo, não motor de mídia. O adaptador executa `opencode run --model ollama/...` com timeout, cancelamento e captura real de saída. O servidor OpenCode não é exposto pela aplicação.

### Vibe Workflow
Upstream do editor React Flow. A integração React fica em `source/frontend-react`; o runtime validado sem dependências JS externas permite abrir o produto antes de instalar o workspace Node.

### Open Generative AI
Catálogo, referências de UX e adaptadores locais. Rotas MuAPI/cloud não são necessárias e permanecem desativadas por padrão. Nenhum prompt ou arquivo é enviado silenciosamente a provider.

## Engines adicionais necessárias

- `stable-diffusion.cpp`: inferência quantizada local de imagem e vídeo.
- Real-ESRGAN NCNN Vulkan: super-resolução espacial.
- RIFE NCNN Vulkan: interpolação temporal.
- FFmpeg/FFprobe: I/O, frames, mux e codecs.
- Ollama: LLM local.
- ComfyUI: sidecar opcional por API loopback.
- WanGP: sidecar opcional sob licença própria.

## Acervo, quarentena e promoção

```text
Avangard One/opensources/
├── manifest.json
├── manifest.lock.json
├── quarantine/<repo>/        # clone temporário nunca executado automaticamente
├── audits/<repo>.json        # findings de Unicode, lifecycle e binários
├── upstream/<repo>/          # commit exato promovido após gate
├── forks/<repo>/             # patches controlados
├── integrations/<repo>/      # metadados/adaptadores
├── licenses/
└── checksums/<repo>.sha256
```

`scripts/sync_opensources.py`:

1. clona recursivamente em quarentena;
2. faz checkout detached do commit pinado;
3. inicializa submódulos;
4. recusa mismatch de commit;
5. varre caracteres invisíveis e bidirecionais em arquivos rastreados;
6. registra scripts `preinstall/install/postinstall/prepare` e binários para revisão;
7. rejeita findings críticos antes de qualquer instalação de dependência;
8. calcula SHA-256 de todo arquivo rastreado;
9. copia licença;
10. promove atomicamente e preserva rollback do upstream anterior.

WanGP é ignorado sem aceite explícito. A auditoria é um gate adicional, não substitui sandbox, antivírus, revisão humana ou assinatura do fornecedor.

## Limitação desta entrega

O executor usado para produzir o ZIP não resolve DNS externo. Por isso os clones completos não foram materializados aqui e `OSS-SYNC-001` permanece bloqueada. O script, o manifesto, commits, política, testes do scanner e estrutura de destino foram entregues; executar o bootstrap no Alienware produz as evidências reais.

## Atualização e rollback

1. altere somente um commit no manifesto;
2. execute bootstrap com `-Force`/`--force`;
3. revise o audit JSON, licença e changelog;
4. compare checksums e diff;
5. execute a suíte completa e smoke das engines;
6. restaure o manifesto anterior e repita bootstrap para rollback.
