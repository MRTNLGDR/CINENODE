# Avangard CineNode Local — pacote de software

Software completo, **sem pesos de modelo e sem `node_modules`**. Versão v0.15.0,
493 testes passando na origem.

| | |
|---|---|
| arquivos | 6.350 |
| tamanho | 52,7 MB |
| retirado | 105 GB de pesos, binários de engine, banco e saídas |

## O que tem aqui

| pasta | conteúdo |
|---|---|
| `source/backend/cinenode/` | backend FastAPI, catálogo de nós, motor da Fase E |
| `source/frontend/` | interface, JavaScript sem build |
| `tests/` | 493 testes automatizados |
| `scripts/` | instalação, reset, verificação de licença, autocommit |
| `docs/` | governança, ADRs, arquitetura |
| `ANALISE/` | estado real, pendências medidas, problemas difíceis |

## Leia primeiro

1. **`MODELOS.md`** — o que foi retirado, onde recolocar, e a licença de cada um.
2. **`ANALISE/00_LEIA_PRIMEIRO.md`** — o produto e a questão dos 1697 stubs.
3. **`ANALISE/05_COMO_AUDITAR.md`** — onde procurar defeito e onde não perder tempo.

## Instalar

```
scripts\install.ps1        cria o venv e instala em modo editavel
LIGAR.bat                  sobe CineNode, Ollama e ComfyUI
```

Sem os pesos o app **sobe e funciona**. Cada nó de geração recusa com o código
`MODELO_AUSENTE` dizendo qual arquivo falta. Toda a parte de malha, rig, tecido,
cabelo, movimento e exportação — 56 das 71 operações da Fase E — **não depende de
modelo nenhum** e roda sem baixar nada.

## O que este pacote não esconde

Fase E em **8,2%** (71 de 868 microitens). Módulos M-34 a M-40 seguem
`BLOQUEADO`. Três pesos com licença `UNKNOWN_BLOCKED`. Vídeo no máximo não cabe
na VRAM medida. Os detalhes estão em `ANALISE/02_O_QUE_FALTA.md`.
