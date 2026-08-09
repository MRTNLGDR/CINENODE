# Limite entre CineNode e PERZON

CineNode é o canvas/orquestrador nodal de mídia. PERZON é um sistema de personagem/humano digital separado.

Este repositório não deve receber:

- `cinenode/perzon/`;
- rotas `/api/perzon/*`;
- testes ou métricas de conclusão do PERZON;
- cópias de algoritmos identificados por `PZ-*`;
- backlog do PERZON apresentado como progresso do CineNode.

Uma integração futura deverá usar um contrato explícito, por exemplo:

```text
CineNode node adapter → PERZON API/plugin → asset versionado
```

Cada produto manterá repositório, versão, licença, testes e roadmap próprios.
