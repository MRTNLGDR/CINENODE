# Avangard CineNode Local — estado real para análise externa

Este pacote existe para uma pergunta: **o que ainda falta e quais partes são
difíceis de verdade.** Todo número aqui foi medido na máquina, não estimado. Os
`.json` em `dados/` são gerados do código e do banco, não escritos à mão.

---

## 1. O que é o produto

Estúdio nodal local-first para gerar imagem, vídeo, 3D e personagem. Roda inteiro
em `127.0.0.1`, sem nuvem obrigatória. Backend FastAPI + SQLite (WAL), frontend
JavaScript sem build.

**Hardware alvo, e o gargalo medido:** RTX 4090 Laptop, **16.376 MiB de VRAM**.
O job mais pesado (vídeo 832×480, 33 quadros, RIFE + H.265) marcou **15.752 MiB
de pico**. Com o desktop ocupando ~3 GB, vídeo no máximo **não cabe hoje**. Esse
teto é invariante à linguagem e é a restrição que governa o resto.

| medida | valor |
|---|---|
| versão | 0.14.0 |
| testes automatizados | **493 passando** |
| validação de pacote | 625 checagens, `passed` |
| módulos concluídos | 18 de 32 |
| Fase E (personagem) | **71 de 868 microitens — 8,2%** |

---

## 2. A questão central: os 1697 stubs

O repositório PERZON (`D:\AIIA\01-apps-canonicos\11-pezon`) declara **1697
microitens** e entrega **3.397 schemas JSON** de contrato. A consulta por status
devolve uma linha só:

```
specified_not_implemented    1697
```

E os 3.459 arquivos Rust em `code/rust` são **1697 de 1697** assim:

```rust
pub async fn execute_algorithms_ajuste_multiview(...) -> Result<..., PerzonError> {
    Err(PerzonError::Validation("specified_not_implemented: PZ-25-ajuste-multiview".to_owned()))
}
```

O contrato é exato. O cálculo nunca existiu. O próprio `00_MASTER_SPEC.md` do
PERZON admite isso.

**A decisão (ADR-008):** os algoritmos passaram a ser implementados em Python em
`source/backend/cinenode/perzon/`, casando pelo `feature_id` exato do catálogo do
PERZON. Motivos medidos, não estéticos:

1. O gargalo é VRAM, não CPU — as operações de geometria custam de 0,001 s a
   0,3 s, irrelevantes frente aos 400,82 s de uma geração de vídeo.
2. O CineNode já tem fila de jobs, assets, migrações, telemetria e UI. Dois
   processos donos do mesmo estado é como se perde consistência.
3. `trimesh`, `scipy`, `numpy`, `opencv`, `mediapipe` cobrem a geometria com
   código já testado por terceiros.

**A regra que sustenta o resto:** operação sem cálculo **recusa com código**
(`FEATURE_NAO_IMPLEMENTADA`). Nunca devolve dicionário plausível. Foi essa
aparência de funcionamento que os 1697 stubs produziram.

---

## 3. O que ler, nesta ordem

| arquivo | o que responde |
|---|---|
| `01_O_QUE_FUNCIONA.md` | o que roda hoje, com número medido |
| `02_O_QUE_FALTA.md` | as 797 pendências, agrupadas por natureza |
| `03_PROBLEMAS_DIFICEIS.md` | onde o trabalho é genuinamente difícil, e por quê |
| `04_DEFEITOS_ENCONTRADOS.md` | 20 defeitos reais que a medição pegou — inclui erros meus |
| `dados/*.json` | os dados crus, gerados do código |

---

## 4. Como verificar qualquer afirmação daqui

```bash
cd "D:\AIIA\01-apps-canonicos\18-aiia-visual\BASE TESTE\Avangard-CineNode-Local-v0.1.0\Avangard-CineNode-Local-v0.1.0"
```

| verificar | comando |
|---|---|
| suíte | `.runtime\venv\Scripts\python.exe -m pytest -q` |
| pacote | `.runtime\venv\Scripts\python.exe scripts\validate_package.py --root .` |
| Fase E | `.runtime\venv\Scripts\python.exe scripts\verify_perzon.py M-34` |
| licenças | `.runtime\venv\Scripts\python.exe scripts\verify_licenses.py` |
| subir tudo | `LIGAR.bat` |
| operações no ar | `curl http://127.0.0.1:8787/api/perzon/operacoes` |

---

## 5. O que este pacote NÃO afirma

Não afirma que a Fase E está pronta: **8,2%** não é entrega, e os módulos M-34 a
M-40 seguem `BLOQUEADO` no painel de governança. Não afirma que os modelos de
geração foram validados no hardware alvo — `GPU-TEST-001` continua pendente. E
não afirma licença de peso que ninguém leu: 3 modelos estão `UNKNOWN_BLOCKED`, e
25 dos 29 componentes têm licença vinda do card upstream, não conferida no disco.
