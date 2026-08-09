# Validação da baseline 0.1.0

Executado em 8 de agosto de 2026:

```text
pytest: 11 passed
wheel: cinenode-0.1.0-py3-none-any.whl
wheel contém backend e frontend: aprovado
importação fora da árvore-fonte: aprovada
servidor real em 127.0.0.1:18787: aprovado
GET /api/health: status ok
GET /: frontend entregue
rotas /api/perzon/*: inexistentes
```

Engines detectadas na máquina de validação: FFmpeg e ffprobe disponíveis; Ollama e ComfyUI não iniciados. A ausência dos sidecars não impede o canvas, banco, projetos, workflows, jobs ou assets de funcionar.
