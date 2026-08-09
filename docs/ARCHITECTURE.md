# Arquitetura CineNode

```text
Browser local
    │ HTTP + polling/SSE
    ▼
FastAPI control plane
    ├── projetos/workflows
    ├── assets com SHA-256
    ├── fila de jobs
    ├── validação e execução DAG
    └── SQLite WAL
           │
           ├── FFmpeg/ffprobe (processo local)
           ├── Ollama 127.0.0.1:11434
           └── ComfyUI 127.0.0.1:8188
```

O plano de controle permanece utilizável sem GPU. Engines são sidecars ou binários substituíveis. Um node sem sua engine retorna erro explícito; não existe fallback que finja gerar mídia.

## Estados de job

```text
QUEUED → RUNNING → SUCCEEDED
                 ├→ FAILED
                 ├→ CANCELLED     (ação do usuário)
                 └→ INTERRUPTED   (processo encerrado)
```

`FAILED`, `CANCELLED` e `INTERRUPTED` podem ser retomados. O shutdown não converte uma interrupção operacional em cancelamento do usuário.

## Grafo

Cada workflow possui nós, conexões e metadados. A validação rejeita:

- IDs duplicados;
- tipos de nós desconhecidos;
- endpoints inexistentes;
- portas incompatíveis;
- mais de uma conexão na mesma entrada;
- auto-conexões;
- ciclos.

A execução usa ordenação topológica e persiste eventos por nó.
