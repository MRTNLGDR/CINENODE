# ADR-008 — A Fase E é implementada em Python neste repositório

| Campo | Valor |
|---|---|
| Estado | ACEITA |
| Data | 2026-08-07 |
| Substitui | nada |
| Afeta | M-34, M-35, M-36, M-37, M-38, M-39, M-40 |

## Contexto medido

O PERZON declara **1697 microitens** no `registry/feature_catalog.sqlite`. A
consulta por status devolve uma linha só:

```
specified_not_implemented    1697
```

O repositório tem **3459 arquivos** de código em `code/rust`. A varredura por
corpo de função encontrou **1697 de 1697** retornando a mesma coisa:

```rust
pub async fn execute_algorithms_ajuste_multiview(...) -> Result<..., PerzonError> {
    Err(PerzonError::Validation(
        "specified_not_implemented: PZ-25-ajuste-multiview".to_owned(),
    ))
}
```

O contrato é exato. Os schemas existem — **3397 arquivos JSON** em
`contracts/schemas`. O cálculo nunca existiu.

O próprio `00_MASTER_SPEC.md` do PERZON diz isso:

> "O inventário é catálogo-alvo. Esta entrega transforma o catálogo em contratos
> executáveis e navegáveis; não afirma que os algoritmos de produção estejam
> implementados."

## Decisão

Os algoritmos da Fase E são implementados em Python, em
`source/backend/cinenode/perzon/`, casando pelo `feature_id` exato do catálogo do
PERZON. O repositório Rust continua sendo a fonte do contrato; deixa de ser a
fonte prometida da implementação.

## Por quê, com número

**1. A linguagem não é o gargalo.** O teto medido desta máquina é VRAM: 16.376
MiB totais, com pico de 15.752 MiB no job de vídeo. Reescrever geometria em Rust
otimizaria CPU, que não é onde o trabalho para. As operações implementadas medem
de 0,001 s a 0,048 s numa malha de 1.804 faces — o custo já é irrelevante frente
aos 400,82 s de uma geração de vídeo.

**2. O estado já tem dono.** O CineNode tem fila de jobs, registro de assets,
banco com migração versionada, telemetria e UI. Um segundo processo executando
Fase E precisaria de tudo isso de novo, e dois donos do mesmo estado é como se
perde consistência sem ninguém perceber.

**3. A geometria já está escrita e testada por terceiros.** `trimesh`, `scipy`,
`numpy`, `opencv` e `rtree` cobrem decimação quádrica, suavização de Taubin,
consulta de proximidade por R-tree e derivada por Sobel. Reimplementar isso em
Rust seria reescrever, pior, o que funciona.

## Consequências

**Boas.** As operações rodam hoje, pelos mesmos jobs e assets do resto do app.
`/api/perzon/operacoes` lista o que executa; `/api/perzon/executar` roda sobre
asset registrado. Sete nós novos na categoria Personagem chamam o mesmo motor —
um cálculo, dois caminhos até ele.

**Ruins, e assumidas.** O binário Rust continua sem implementação; quem esperar
executar a Fase E por ele continuará recebendo `specified_not_implemented`. Se o
projeto um dia precisar de Fase E fora do CineNode, esta decisão terá de ser
revista — e o ponto de revisão é uma medida, não uma data: quando o perfil
apontar a geometria como gargalo, ou quando houver segundo consumidor.

**Neutra.** O `verify_perzon.py` agora conta as duas coisas separadamente: o que
o PERZON declara e o que executa aqui, com o rótulo `implementado_local`. Somar
os dois num número só esconderia exatamente a diferença que este ADR existe para
tornar visível.

## Estado atual, medido

| Módulo | Workspaces | Microitens | Implementados aqui |
|---|---|---|---|
| M-34 | character, headshot, face | 183 | 0 |
| M-35 | material, mesh, sculpt | 268 | 16 |
| M-36 | rig | 48 | 4 |
| M-37 | motion | 69 | 0 |
| M-38 | hair, garment | 132 | 0 |
| M-39 | voice | 31 | 0 |
| M-40 | formats, connectors, game | 137 | 0 |

20 operações de 728 na Fase E. Os módulos seguem `BLOQUEADO`, e é a leitura
correta: 2,7% não é entrega.

## Regra que não pode ser afrouxada

Operação sem cálculo **recusa com código** (`FEATURE_NAO_IMPLEMENTADA`). Nunca
devolve um dicionário plausível. Foi essa aparência de funcionamento que os 1697
stubs produziram, e é o que este motor existe para não repetir.
