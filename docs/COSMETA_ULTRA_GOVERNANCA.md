# COSMETA ULTRA — UNIVERSAL NODE ENGINE

## Governança Visual, Catálogo Canônico e Especificação Técnica de Implementação

| Campo | Valor |
| --- | --- |
| Documento | `COSMETA_ULTRA_GOVERNANCA.md` |
| Versão do documento | `1.0.0` |
| Produto | Avangard CineNode Local → COSMETA ULTRA |
| Base implementada hoje | `Avangard-CineNode-Local-v0.1.0` (19 nós, FastAPI + SQLite, frontend zero-build) |
| Idioma da experiência | `pt-BR` — nomes de nós, fluxos, campos e mensagens |
| Idioma da governança | IDs canônicos, manifests e nomes de projeto originais em inglês |
| Regra de nomes | O usuário vê **o que a função faz**. A governança sabe **qual projeto, versão, hash, licença e runtime** executaram. |
| Regra de ícones | **Nenhum emoji em qualquer superfície.** Somente ícones vetoriais do registry e miniaturas geradas. |
| Regra de honestidade | Nada é marcado como pronto sem evidência reproduzível anexada. |

---

## 0. COMO LER ESTE DOCUMENTO

Este arquivo tem duas leituras simultâneas e nenhuma delas é resumo da outra.

**Leitura do usuário.** Tabelas, categorias, nomes amigáveis, painéis, estados, alertas de conclusão. Tudo que aparece na tela está descrito com o nome que aparece na tela.

**Leitura da LLM que vai codar.** IDs canônicos, schemas JSON, contratos YAML, assinaturas TypeScript, diagramas de fluxo, gates de aceite. Cada módulo tem critério de conclusão verificável — não "parece pronto", e sim "o comando X produz a evidência Y".

### 0.1 Convenções de notação

| Notação | Significado |
| --- | --- |
| `icon:nome` | Referência ao registry vetorial. **Nunca** um emoji. Ver §1. |
| `slot://categoria.acao.perfil` | Capability slot. O front pede a capacidade, nunca o fornecedor. |
| `model://vendor/projeto/revisao` | Modelo concreto resolvido pelo registro de modelos. |
| `asset://uuidv7` | Referência imutável a asset versionado. |
| `GATE-XX` | Portão de aceite com evidência obrigatória. |
| `MUST` / `SHOULD` / `MAY` | Força normativa (RFC 2119). |
| `[IMPLEMENTADO]` | Existe e tem teste passando no repositório atual. |
| `[PARCIAL]` | Existe parcialmente; a lacuna está nomeada. |
| `[ESPECIFICADO]` | Só especificação. Não existe código. Não pode aparecer na UI como pronto. |

### 0.2 O que este documento não faz

Não substitui a governança de engenharia já existente. Não declara que qualquer módulo marcado `[ESPECIFICADO]` funciona. Não trata "código público" como sinônimo de "licença comercial irrestrita".

---

## 1. REGISTRY DE ÍCONES — SUBSTITUIÇÃO INTEGRAL DE EMOJI

Emojis são proibidos em nomes de nós, categorias, botões, tooltips, logs, mensagens de erro, notificações e documentação de produto. O motivo é técnico, não estético: emoji renderiza diferente por sistema, quebra alinhamento em grade, não herda `currentColor`, não escala em SVG e não pode ser tematizado por `data-theme`.

Toda representação gráfica vem de um registry único de paths SVG 24×24, `stroke="currentColor"`, `stroke-width="1.6"`, `fill="none"`.

### 1.1 Contrato do registry

```ts
/** Registry único. Adicionar ícone = adicionar entrada aqui, nunca inline no componente. */
export const ICON_PATHS: Record<IconName, string> = {
  // ---- estrutura e fluxo ----
  entrada:        "M4 12h11M11 8l4 4-4 4M15 4h5v16h-5",
  saida:          "M20 12H9M13 8l-4 4 4 4M9 4H4v16h5",
  fluxo:          "M4 7h6a3 3 0 0 1 3 3v4a3 3 0 0 0 3 3h4M17 14l3 3-3 3",
  lote:           "M4 6h10M4 12h10M4 18h10M18 6h2M18 12h2M18 18h2",
  laco:           "M8 5a7 7 0 1 0 7 7M15 2l3 3-3 3",
  cache:          "M4 7c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 7v10c0 1.7 3.6 3 8 3s8-1.3 8-3V7",
  // ---- modalidades ----
  texto:          "M5 5h14M9 5v14M7 19h4",
  imagem:         "M3 5h18v14H3zM3 15l5-5 4 4 3-3 6 6",
  video:          "M3 6h12v12H3zM15 10l6-3v10l-6-3",
  audio:          "M4 10v4h3l4 4V6L7 10zM16 9a4 4 0 0 1 0 6",
  malha3d:        "M12 2l9 5v10l-9 5-9-5V7zM12 2v20M3 7l9 5 9-5",
  nuvem_pontos:   "M6 8h.01M10 6h.01M14 9h.01M8 13h.01M12 12h.01M17 13h.01M7 17h.01M13 17h.01M18 8h.01",
  splat:          "M12 4a8 8 0 1 0 .01 16A8 8 0 0 0 12 4zM9 10h.01M15 10h.01M12 14h.01",
  // ---- controle visual ----
  profundidade:   "M3 20l6-16 6 16M8 14h6M17 8h4v12h-4z",
  normais:        "M12 20V8m0 0l-4 4m4-4l4 4M4 20h16",
  pose:           "M12 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4zM12 8v6M8 11h8M10 20l2-6 2 6",
  mascara:        "M4 6h16v12H4zM9 10a3 3 0 1 0 6 0 3 3 0 0 0-6 0",
  contorno:       "M4 18c4-10 12-10 16 0M4 6h16",
  segmentacao:    "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7",
  fluxo_optico:   "M4 12h5l3-5 3 10 3-5h3",
  // ---- câmera e cor ----
  camera:         "M4 8h4l2-2h4l2 2h4v11H4zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8",
  lente:          "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8",
  luz:            "M12 3v2M5 12H3M21 12h-2M6 6L4.5 4.5M18 6l1.5-1.5M9 17h6M10 21h4M8 14a5 5 0 1 1 8 0c-1 1-1.3 2-1.3 3h-5.4c0-1-.3-2-1.3-3",
  cor:            "M12 3a9 9 0 1 0 0 18c1.7 0 2-1 1.3-1.9-.8-1 .1-2.1 1.2-2.1H18a3 3 0 0 0 3-3c0-5-4-11-9-11zM7.5 11h.01M10 7.5h.01M14.5 7.5h.01",
  lut:            "M4 4h16v16H4zM4 9h16M4 14h16M9 4v16M14 4v16",
  escopo:         "M3 18l4-8 4 5 3-9 4 12M3 4v16h18",
  // ---- domínios ----
  personagem:     "M12 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8zM4 21c0-4.4 3.6-7 8-7s8 2.6 8 7",
  animal:         "M6 8a2 2 0 1 1 0-4 2 2 0 0 1 0 4zM18 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 20c-3 0-6-2-6-5s3-6 6-6 6 3 6 6-3 5-6 5",
  movimento:      "M13 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4zM11 21l1-6-3-3 1-4 4 3 3 1M9 12l-3 2M15 21l3-4",
  arquitetura:    "M3 21h18M5 21V9l7-5 7 5v12M10 21v-6h4v6",
  planta:         "M3 4h18v16H3zM3 12h9M12 4v16M16 12h5",
  mapa:           "M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14",
  natureza:       "M12 21v-6M12 15c-4 0-6-3-6-6a6 6 0 0 1 12 0c0 3-2 6-6 6M9 9l3 3 3-3",
  codigo:         "M8 8l-4 4 4 4M16 8l4 4-4 4M14 5l-4 14",
  conhecimento:   "M4 5a3 3 0 0 1 3-3h11v18H7a3 3 0 0 0-3 3zM7 2v18",
  treinamento:    "M4 12h3l2-6 3 12 2-6h6",
  // ---- sistema ----
  roteador:       "M12 3v6M12 15v6M3 12h6M15 12h6M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6",
  processador:    "M7 7h10v10H7zM4 10h3M4 14h3M17 10h3M17 14h3M10 4v3M14 4v3M10 17v3M14 17v3",
  memoria:        "M4 6h16v12H4zM8 6v12M12 6v12M16 6v12",
  agente:         "M12 3a4 4 0 0 1 4 4v1h1a3 3 0 0 1 0 6h-1v3H8v-3H7a3 3 0 0 1 0-6h1V7a4 4 0 0 1 4-4zM10 11h.01M14 11h.01",
  evidencia:      "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4",
  licenca:        "M7 3h10v14l-5-3-5 3zM9 8h6",
  consentimento:  "M12 3l7 3v6c0 5-3 8-7 9-4-1-7-4-7-9V6zM12 9v4M12 16h.01",
  // ---- estados e alertas ----
  concluido:      "M5 12l5 5 9-11",
  bloqueado:      "M7 11V8a5 5 0 0 1 10 0v3M5 11h14v9H5z",
  atencao:        "M12 4l9 16H3zM12 10v4M12 17h.01",
  erro:           "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9 9l6 6M15 9l-6 6",
  progresso:      "M12 3a9 9 0 1 0 9 9",
  pendente:       "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2",
  local:          "M4 5h16v10H4zM8 19h8M12 15v4",
  remoto:         "M5 12a7 7 0 0 1 14 0M8.5 15a3.5 3.5 0 0 1 7 0M12 18h.01M3 9a12 12 0 0 1 18 0",
  tutorial:       "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v5M12 8h.01",
  avancado:       "M4 6h16M4 12h16M4 18h16M8 4v4M16 10v4M11 16v4",
};

export type IconName = keyof typeof ICON_PATHS;
```

### 1.2 Componente único de ícone

```tsx
export function Icon({ name, size = 16 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth={1.6}
      strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true" focusable="false" className="ico"
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}
```

### 1.3 Lint que impede a volta do emoji

```python
# tests/test_sem_emoji.py — a regra só existe se estiver testada.
import re, pathlib

# Faixas de emoji e pictogramas. Setas e símbolos de desenho de caixa continuam válidos.
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0000FE0F\U0001F1E6-\U0001F1FF]"
)
SUPERFICIES = ["source/frontend", "source/backend/cinenode", "docs"]

def test_nenhuma_superficie_tem_emoji():
    achados = []
    for base in SUPERFICIES:
        for arquivo in pathlib.Path(base).rglob("*"):
            if arquivo.suffix not in {".js", ".ts", ".tsx", ".py", ".css", ".md", ".json", ".yaml"}:
                continue
            texto = arquivo.read_text(encoding="utf-8", errors="ignore")
            for numero, linha in enumerate(texto.splitlines(), 1):
                if EMOJI.search(linha):
                    achados.append(f"{arquivo}:{numero}: {linha.strip()[:80]}")
    assert not achados, "emoji encontrado em superfície de produto:\n" + "\n".join(achados)
```

### 1.4 Miniaturas: como um catálogo com centenas de nós não vira bagunça

Ninguém vai desenhar arte para cada nó. A miniatura é **gerada** do próprio manifesto: fundo da categoria, ícone da categoria ao centro, e as portas do nó como pontos coloridos nas laterais — esquerda entradas, direita saídas. O usuário reconhece o nó pelo formato antes de ler o nome.

```
BIBLIOTECA DE NÓS                                    [buscar...        ]

  IMAGEM                                                   12 nos
  ┌──────────┐  IMAGEM ULTRA RAPIDA
  │ o        │  Geracao rapida para iterar composicao.
  │   [ico] o│  local · ~6 GB
  │ o        │
  └──────────┘
  ┌──────────┐  IMAGEM QUALITY PRO
  │ o        │  Maxima fidelidade, texto legivel na arte.
  │o  [ico] o│  local · ~14 GB
  │ o        │
  └──────────┘
```

```ts
/** Miniatura derivada do manifesto. Escala para N nós sem arte manual. */
export function NodeThumb({ manifest }: { manifest: NodeManifest }) {
  const dots = (ports: PortSpec[]) =>
    ports.slice(0, 5).map(p => (
      <i key={p.id} style={{ background: PORT_COLORS[p.type] }} title={PORT_LABELS[p.type]} />
    ));
  return (
    <span className="node-thumb" data-category={manifest.category}>
      <span className="thumb-in">{dots(manifest.ports.inputs)}</span>
      <Icon name={CATEGORY_ICON[manifest.category]} size={16} />
      <span className="thumb-out">{dots(manifest.ports.outputs)}</span>
    </span>
  );
}
```

---

## 2. ALERTA DE CONCLUSÃO DE MÓDULO

Este é o mecanismo central de governança visual. Um módulo não é declarado pronto por narrativa. Ele é declarado pronto por **gates com evidência**, e o alerta só dispara quando todos os gates passam.

### 2.1 Anatomia do alerta

```
╔════════════════════════════════════════════════════════════════════════════╗
║  [icon:concluido]   MÓDULO CONCLUÍDO                          M-07         ║
║                                                                            ║
║  VÍDEO — GERAÇÃO E CONTINUIDADE                                            ║
║  14 nós entregues · 9 gates aprovados · 0 pendências bloqueantes           ║
║                                                                            ║
║  ████████████████████████████████████████████████████████████  100%       ║
║                                                                            ║
║  ┌────────────────┬────────────────┬────────────────┬────────────────┐    ║
║  │ [icon:concluido]│[icon:concluido]│[icon:concluido]│[icon:concluido]│    ║
║  │ FUNCIONA       │ TESTADO        │ MEDIDO         │ LICENCIADO     │    ║
║  │ 14/14 nós      │ 62 testes      │ 400.8 s @ 4090 │ 6 modelos OK   │    ║
║  └────────────────┴────────────────┴────────────────┴────────────────┘    ║
║                                                                            ║
║  ┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐             ║
║  │ [thumb]  ││ [thumb]  ││ [thumb]  ││ [thumb]  ││ [thumb]  │  + 9        ║
║  │ FILME    ││ IMAGEM   ││ PRIMEIRO ││ ESTENDER ││ MASTER   │             ║
║  │ RAPIDO   ││ P/ VIDEO ││ + ULTIMO ││ CENA     ││ FINAL    │             ║
║  └──────────┘└──────────┘└──────────┘└──────────┘└──────────┘             ║
║                                                                            ║
║  Evidência    docs/evidence/M-07/                                          ║
║  Commit       a1b2c3d · tag v0.7.0 · 2026-08-07T14:22:10Z                  ║
║                                                                            ║
║  [ Ver evidência ]  [ Abrir fluxo de exemplo ]  [ Próximo módulo M-08 ]    ║
╚════════════════════════════════════════════════════════════════════════════╝
```

Variantes do mesmo componente, mesmo layout, ícone e cor diferentes:

| Estado | Ícone | Quando dispara | Ação oferecida |
| --- | --- | --- | --- |
| `CONCLUIDO` | `icon:concluido` | Todos os gates aprovados com evidência anexada | Ver evidência, abrir exemplo, ir ao próximo |
| `EM_PROGRESSO` | `icon:progresso` | Pelo menos um gate aprovado, nenhum reprovado | Ver o que falta |
| `BLOQUEADO` | `icon:bloqueado` | Gate reprovado por dependência externa (licença, hardware, upstream) | Ver o bloqueio e o dono |
| `REGREDIU` | `icon:atencao` | Módulo já concluído voltou a falhar um gate | Ver o commit que quebrou |
| `PARCIAL` | `icon:pendente` | Entregue com escopo reduzido declarado | Ver o que foi deixado de fora |

### 2.2 Contrato do módulo

```yaml
# governance/modules/M-07.yaml
module:
  id: "M-07"
  display_name_ptbr: "VÍDEO — GERAÇÃO E CONTINUIDADE"
  icon: "video"
  depends_on: ["M-01", "M-02", "M-05"]

  deliverables:
    nodes:
      - "video.generate.fast8b"
      - "video.generate.4kpro"
      - "video.i2v"
      - "video.start_end"
      - "video.extend"
      - "video.master"
    flows:
      - "START TO END VIDEO 4K"
      - "PRIMEIRO + ULTIMO FRAME"

  gates:
    - id: "GATE-FUNC"
      label_ptbr: "FUNCIONA"
      rule: "todo nó declarado executa e devolve asset do tipo prometido"
      evidence: "docs/evidence/M-07/execucao.json"
      command: "pytest tests/test_modulo_video.py -q"

    - id: "GATE-TEST"
      label_ptbr: "TESTADO"
      rule: "suite verde, sem skip silencioso"
      evidence: "docs/evidence/M-07/pytest.txt"
      command: "pytest -q"

    - id: "GATE-PERF"
      label_ptbr: "MEDIDO"
      rule: "tempo e VRAM de pico medidos no hardware alvo e registrados"
      evidence: "docs/evidence/M-07/benchmark.json"
      command: "python scripts/benchmark.py --module M-07"

    - id: "GATE-LICENSE"
      label_ptbr: "LICENCIADO"
      rule: "todo modelo usado tem licença resolvida e diferente de UNKNOWN_BLOCKED"
      evidence: "docs/evidence/M-07/licencas.json"
      command: "python scripts/audit_models.py --module M-07"

    - id: "GATE-UI"
      label_ptbr: "VISUAL"
      rule: "todo campo tem controle visual e todo nó tem tutorial preenchido"
      evidence: "docs/evidence/M-07/ui.json"
      command: "pytest tests/test_catalog_visual_rule.py -q"

  completion_alert:
    fire_when: "todos os gates com status=PASS"
    never_fire_when:
      - "qualquer gate com status=UNKNOWN"
      - "qualquer nó do módulo marcado [ESPECIFICADO]"
      - "evidência ausente no caminho declarado"
```

### 2.3 Evidência: formato obrigatório

Um gate sem arquivo de evidência é um gate reprovado. Não existe aprovação por afirmação.

```json
{
  "gate_id": "GATE-PERF",
  "module_id": "M-07",
  "status": "PASS",
  "recorded_at": "2026-08-07T14:22:10Z",
  "host": {
    "gpu": "NVIDIA GeForce RTX 4090 Laptop GPU",
    "vram_total_mib": 16376,
    "driver": "581.15",
    "cuda": "13.1",
    "os": "Windows 11 Pro 10.0.26200"
  },
  "measurements": [
    {
      "case": "video 832x480 33f 20steps + RIFE + H.265",
      "wall_seconds": 400.82,
      "vram_peak_mib": 15752,
      "output_hash": "sha256:9f2c...",
      "output_bytes": 2841193
    }
  ],
  "command": "python scripts/benchmark.py --module M-07",
  "stdout_ref": "docs/evidence/M-07/benchmark.stdout.txt"
}
```

### 2.4 Componente React do alerta

```tsx
type GateStatus = "PASS" | "FAIL" | "BLOCKED" | "UNKNOWN";

interface ModuleReport {
  id: string;
  displayName: string;
  icon: IconName;
  state: "CONCLUIDO" | "EM_PROGRESSO" | "BLOQUEADO" | "REGREDIU" | "PARCIAL";
  gates: { id: string; label: string; status: GateStatus; detail: string; evidence: string }[];
  nodes: NodeManifest[];
  progressPct: number;
  commit: string;
  tag: string | null;
  recordedAt: string;
}

const STATE_ICON: Record<ModuleReport["state"], IconName> = {
  CONCLUIDO: "concluido",
  EM_PROGRESSO: "progresso",
  BLOQUEADO: "bloqueado",
  REGREDIU: "atencao",
  PARCIAL: "pendente",
};

export function ModuleCompletionAlert({ report }: { report: ModuleReport }) {
  const bloqueantes = report.gates.filter(g => g.status !== "PASS");

  return (
    <section className="module-alert" data-state={report.state} role="status" aria-live="polite">
      <header className="module-alert__head">
        <Icon name={STATE_ICON[report.state]} size={22} />
        <div>
          <small>{report.state.replace("_", " ")}</small>
          <h2>{report.displayName}</h2>
          <p>
            {report.nodes.length} nós entregues · {report.gates.filter(g => g.status === "PASS").length}/
            {report.gates.length} gates aprovados · {bloqueantes.length} pendências bloqueantes
          </p>
        </div>
        <span className="module-alert__id">{report.id}</span>
      </header>

      <div className="module-alert__bar" aria-label={`${report.progressPct}% concluído`}>
        <i style={{ width: `${report.progressPct}%` }} />
      </div>

      <ul className="module-alert__gates">
        {report.gates.map(gate => (
          <li key={gate.id} data-status={gate.status}>
            <Icon name={gate.status === "PASS" ? "concluido" : gate.status === "BLOCKED" ? "bloqueado" : "erro"} />
            <strong>{gate.label}</strong>
            <span>{gate.detail}</span>
            <a href={gate.evidence}>evidência</a>
          </li>
        ))}
      </ul>

      <div className="module-alert__thumbs">
        {report.nodes.slice(0, 6).map(node => (
          <figure key={node.id}>
            <NodeThumb manifest={node} />
            <figcaption>{node.display_name_ptbr}</figcaption>
          </figure>
        ))}
        {report.nodes.length > 6 && <span className="more">+{report.nodes.length - 6}</span>}
      </div>

      <footer>
        <code>{report.commit}{report.tag ? ` · ${report.tag}` : ""}</code>
        <time dateTime={report.recordedAt}>{report.recordedAt}</time>
      </footer>
    </section>
  );
}
```

### 2.5 Estilo do alerta (tema duplo, sem cor codificando sozinha o estado)

```css
.module-alert {
  border: 1px solid var(--line);
  border-left: 3px solid var(--state-color);
  border-radius: 14px;
  background: var(--panel);
  padding: 18px 20px;
  display: grid;
  gap: 14px;
}
.module-alert[data-state="CONCLUIDO"]     { --state-color: var(--success); }
.module-alert[data-state="EM_PROGRESSO"]  { --state-color: var(--info); }
.module-alert[data-state="BLOQUEADO"]     { --state-color: var(--danger); }
.module-alert[data-state="REGREDIU"]      { --state-color: var(--warning); }
.module-alert[data-state="PARCIAL"]       { --state-color: var(--subtle); }

.module-alert__head { display: grid; grid-template-columns: auto 1fr auto; gap: 12px; align-items: start; }
.module-alert__head small { color: var(--state-color); font-size: 10px; font-weight: 700; letter-spacing: .14em; }
.module-alert__head h2 { margin: 2px 0 4px; font-size: 16px; letter-spacing: -.01em; }
.module-alert__head p { margin: 0; color: var(--muted); font-size: 12px; }
.module-alert__id { font-family: ui-monospace, monospace; color: var(--subtle); font-size: 11px; }

.module-alert__bar { height: 6px; border-radius: 999px; background: var(--panel-3); overflow: hidden; }
.module-alert__bar i { display: block; height: 100%; background: var(--state-color); }

.module-alert__gates { list-style: none; margin: 0; padding: 0;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px; }
.module-alert__gates li { border: 1px solid var(--line); border-radius: 10px; padding: 9px 10px;
  display: grid; grid-template-columns: auto 1fr; gap: 4px 7px; align-items: center; font-size: 11px; }
.module-alert__gates li[data-status="PASS"]    { color: var(--success); }
.module-alert__gates li[data-status="FAIL"]    { color: var(--danger); }
.module-alert__gates li[data-status="BLOCKED"] { color: var(--warning); }
.module-alert__gates li span { grid-column: 2; color: var(--muted); }
.module-alert__gates li a { grid-column: 1 / -1; color: var(--accent); font-size: 10px; }

.module-alert__thumbs { display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-start; }
.module-alert__thumbs figure { margin: 0; width: 92px; display: grid; gap: 5px; justify-items: center; }
.module-alert__thumbs figcaption { font-size: 9.5px; color: var(--muted); text-align: center; line-height: 1.25; }
.module-alert footer { display: flex; justify-content: space-between; color: var(--subtle); font-size: 10.5px; }
```

---

## 3. PAINEL DE GOVERNANÇA

Uma tela. Todos os módulos. Estado real, não promessa.

```
GOVERNANÇA                                  33 módulos · 8 concluídos · 24%

FUNDAÇÃO
[icon:concluido] M-01  CONTRATOS E GRAFO             ████████████████ 100%  5 gates
[icon:concluido] M-02  CANVAS E PORTAS               ████████████████ 100%  5 gates
[icon:concluido] M-03  REGISTRO DE ASSETS            ████████████████ 100%  4 gates
[icon:progresso] M-04  REGISTRO DE MODELOS           ███████████░░░░░  68%  3/5
[icon:progresso] M-05  MEGA ROTEADOR                 ██████░░░░░░░░░░  40%  2/5

MÍDIA
[icon:concluido] M-06  IMAGEM                        ████████████████ 100%  5 gates
[icon:progresso] M-07  VÍDEO                         ████████████░░░░  76%  4/5
[icon:bloqueado] M-08  RESTAURAÇÃO 4K/8K             ████░░░░░░░░░░░░  22%  licença SUPIR
[icon:pendente]  M-09  COR E VFX                     ░░░░░░░░░░░░░░░░   0%  especificado

ESPACIAL
[icon:progresso] M-10  3D OBJETO                     ████████░░░░░░░░  50%  3/6
[icon:pendente]  M-11  DIGITAL HUMAN                 ░░░░░░░░░░░░░░░░   0%  especificado
...
```

```python
# scripts/governance_report.py — a fonte do painel é o disco, não a memória de ninguém.
"""Lê governance/modules/*.yaml, executa o comando de cada gate e monta o relatório.

Um gate cujo comando falha, cuja evidência não existe ou cuja evidência é mais
antiga que o último commit que tocou o módulo NÃO passa. Isto é intencional:
evidência velha é a forma mais comum de um projeto se declarar pronto sem estar.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
from dataclasses import dataclass, asdict

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MODULOS = RAIZ / "governance" / "modules"


@dataclass
class ResultadoGate:
    id: str
    label: str
    status: str          # PASS | FAIL | BLOCKED | UNKNOWN
    detail: str
    evidence: str


def avaliar_gate(modulo: dict, gate: dict) -> ResultadoGate:
    evidencia = RAIZ / gate["evidence"]
    if not evidencia.exists():
        return ResultadoGate(gate["id"], gate["label_ptbr"], "UNKNOWN",
                             "evidência ausente", gate["evidence"])
    processo = subprocess.run(gate["command"], shell=True, cwd=RAIZ,
                              capture_output=True, text=True)
    if processo.returncode != 0:
        cauda = (processo.stdout + processo.stderr).strip().splitlines()[-1:] or [""]
        return ResultadoGate(gate["id"], gate["label_ptbr"], "FAIL", cauda[0][:120], gate["evidence"])
    dados = json.loads(evidencia.read_text(encoding="utf-8"))
    return ResultadoGate(gate["id"], gate["label_ptbr"], dados.get("status", "UNKNOWN"),
                         dados.get("summary", "ok"), gate["evidence"])


def estado_do_modulo(gates: list[ResultadoGate], tem_especificado: bool) -> str:
    if any(g.status == "BLOCKED" for g in gates):
        return "BLOQUEADO"
    if all(g.status == "PASS" for g in gates) and not tem_especificado:
        return "CONCLUIDO"
    if any(g.status == "PASS" for g in gates):
        return "EM_PROGRESSO"
    return "PARCIAL"
```

---
## 4. DECISÃO DE PRODUTO E ARQUITETURA

O produto não é uma interface para o ComfyUI. É um **Universal Node Engine** com canvas próprio, contratos tipados, execução distribuível e vários backends intercambiáveis. O ComfyUI é um dos motores, não o dono do grafo.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  EXPERIENCE — o que o usuário vê                                             │
│  canvas nodal · nomes pt-BR · ícones · miniaturas · preview · tutorial       │
│  presets profissionais · inspetor dentro do nó · tema claro e escuro         │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │ WorkflowIR tipado
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  TRUSTED CORE — o que ninguém contorna                                       │
│  validação de tipos · roteador de capacidade · agendador de GPU              │
│  motor de política · consentimento · proveniência · orçamento · jobs         │
└───────┬───────────────────┬───────────────────┬──────────────────────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌──────────────────┐  ┌────────────────────────────────────┐
│ MEDIA         │  │ INTELIGÊNCIA     │  │ ESPACIAL / DCC / CAD / GIS         │
│ ComfyUI       │  │ llama.cpp        │  │ Blender headless                    │
│ DiffSynth     │  │ vLLM · SGLang    │  │ OpenCascade · CadQuery              │
│ stable-diff.  │  │ Ollama           │  │ IfcOpenShell · Bonsai               │
│ FFmpeg        │  │ grafo de agentes │  │ GDAL · PROJ · PDAL · MapLibre       │
│ RIFE · ESRGAN │  │ verificadores    │  │ Cesium · 3D Tiles · OSM · Overture  │
└───────────────┘  └──────────────────┘  └────────────────────────────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  TECIDO DE ASSETS, CONHECIMENTO E EVIDÊNCIA                                  │
│  hash de conteúdo · metadata · proveniência de modelo · CRS · DNA · timeline │
│  SQLite/Postgres · armazenamento por conteúdo · índices vetorial/texto/grafo │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 O usuário nunca escolhe "HunyuanVideo-1.5"

No menu ele vê:

```
FILME RÁPIDO ULTRA 8B          IMAGEM MASTER 16K           PLANTA PARA BIM 3D
FILME 4K CINEMA PRO            IMAGENS PARA FILME          ENDEREÇO PARA MUNDO 3D
PRIMEIRO E ÚLTIMO FRAME        OBJETO PARA 3D PRO          TELHADO PARAMÉTRICO
PERSONAGEM 3D QUALITY          DNA HUMANO                  ÁRVORE PROCEDURAL
CLONAR MOVIMENTO               VOZ CONSISTENTE             CÓDIGO A PARTIR DA TELA
PENSAMENTO LOCAL LEVE          VISÃO E RACIOCÍNIO          COSMETA REFINAR
```

A governança registra:

```yaml
display_name_ptbr: "FILME RÁPIDO ULTRA 8B"
capability_slot: "slot://video.generate.fast.consumer_gpu"
binding:
  champion: "model://Tencent-Hunyuan/HunyuanVideo-1.5/<revisao-pinada>"
  technical_profile: "8.3B-class"
  runtime: "ComfyUI | Diffusers | DiffSynth"
  weight_sha256: "<hash>"
  license_tag: "<resolvido-pelo-gate>"
  fallback_chain:
    - "model://Wan-AI/Wan2.2/<revisao>"
    - "model://Lightricks/LTX-Video/<revisao>"
```

Trocar o modelo no futuro não quebra workflow salvo, porque o workflow referencia o slot.

---

## 5. REGRAS NORMATIVAS

1. **Local primeiro.** Toda capacidade declarada como local MUST continuar útil sem internet.
2. **Neutro de fornecedor.** Nó pede `capability_slot`. Nó nunca chama fornecedor direto.
3. **Reusar antes de escrever.** ComfyUI, Blender, IfcOpenShell, GDAL, FFmpeg, MapLibre existem. Reimplementar exige justificativa registrada.
4. **Uma fonte de verdade.** IDs, assets, DNA, metadata, permissões e workflows não vivem em sistemas paralelos.
5. **Proveniência de modelo.** Origem, revisão exata, hash de pesos, licença, runtime, quantização, hardware, avaliação, limitações e fallback. Sem isso o modelo não entra em produção.
6. **Sem falso aprendizado.** Produção não altera pesos continuamente. Conhecimento novo entra como candidato validado. Treino é offline e passa por avaliação.
7. **Metacognição auditável.** Observar, classificar, hipotetizar, buscar contradição, reutilizar, minimizar, modelar ameaça, simular, verificar, orçar, decidir, registrar.
8. **Sem conclusão falsa.** Nó, botão, fluxo ou motor sem implementação testada MUST NOT aparecer como pronto.
9. **Execução longa é job resumível.** Vídeo, treino, reconstrução 3D, bake, CAD, GIS e construção de mundo têm checkpoint, cancel e resume.
10. **Risco e consentimento.** Biometria, rosto, voz, corpo, movimento e identidade real exigem `ConsentManifest` com proveniência.

---

## 6. CANVAS — ANATOMIA DO NÓ

### 6.1 Decisão de front-end

Champion: **XYFlow / React Flow**. Challenger: **Rete.js**. Referência de UX de formulários: **FlowGram.AI**.

O executor não vive no browser. O browser edita `WorkflowIR`; o core valida, compila e executa. LiteGraph não é contrato de produto — o ComfyUI pode usar o dele internamente, o grafo canônico é o nosso.

### 6.2 Cartão do nó

```
╭────────────────────────────────────────────────────────────────────╮
│ [icon:video]  FILME 4K CINEMA PRO         [icon:local] LOCAL  18 GB │
│ Gera ou estende vídeo cinematográfico com áudio opcional.          │
├────────────────────────────────────────────────────────────────────┤
│ o Prompt                                          Vídeo 4K o       │
│ o Referências                                        Áudio o       │
│ o Primeiro frame                                  Metadata o       │
│ o Último frame                                   Evidência o       │
│ o Câmera e lente                                                   │
├────────────────────────────────────────────────────────────────────┤
│ PRESET   [ Cinema 2.39:1 · 30 fps · 15 s              ] [icon:lente]│
│                                                                    │
│ FORMATO  ( 1:1 )( 4:5 )( 9:16 )( 16:9 )(•2.39:1•)( 21:9 )( manual )│
│ DURAÇÃO  [───────────●─────────]  15 s                             │
│ FPS      ( 24 )( 25 )(•30•)( 48 )( 60 )                            │
│ QUALIDADE[──────────────●──────]  cinema                           │
│ MOVIMENTO[────────●────────────]  0.62                             │
│ CONTINU. [──────────────────●──]  0.90                             │
├────────────────────────────────────────────────────────────────────┤
│ [preview de vídeo renderizado aqui, nunca uma URL]                 │
├────────────────────────────────────────────────────────────────────┤
│ [icon:progresso] Preview  [icon:tutorial] Tutorial  [icon:avancado] │
╰────────────────────────────────────────────────────────────────────╯
```

Todo nó MUST exibir: ícone; nome amigável; descrição de uma linha; selo `LOCAL` / `HÍBRIDO` / `PROVIDER`; estimativa de VRAM quando aplicável; estado (`pronto`, `carregando`, `executando`, `cache`, `erro`, `bloqueado`); preview relevante; portas tipadas; presets; controles simples; painel avançado; botão de tutorial; inspeção técnica apenas em modo governança; proveniência do resultado; custo e tempo observados após execução; logs resumidos sem despejar stack trace no usuário comum.

### 6.3 Regra de campo visual — vigente e testada `[IMPLEMENTADO]`

Nenhum campo é lista suspensa crua. A decisão é do catálogo, não do componente, para que a UI e o worker leiam a mesma verdade.

| Natureza do campo | Controle | Regra |
| --- | --- | --- |
| `select` com até 8 opções | `chips` | pílulas clicáveis, seleção visível |
| `select` com mais de 8 opções | `picker` | grade com busca, sem sair do cartão |
| `select` de proporção | `ratio` | retângulos desenhados na proporção real |
| `number` com faixa | `slider` | régua com valor ao lado, digitável |
| `number` sem faixa mas com controle próprio | dedicado | ex.: `seed` usa botão de sortear |
| `boolean` | `switch` | dois estados, rótulo textual |
| `asset` | seletor com miniatura | nunca campo de texto com ID |
| texto livre legítimo | `text` / `textarea` | nome de arquivo, separador, caminho |

```python
# tests/test_catalog_visual_rule.py — regra vigente no repositório, 62 testes verdes.
UI_CONHECIDAS = {"chips", "ratio", "seed", "picker", "slider"}

def test_todo_select_tem_controle_visual():
    cruas = [f"{tipo}.{campo['key']}" for tipo, campo in campos()
             if campo["type"] == "select" and campo.get("ui") not in UI_CONHECIDAS]
    assert not cruas, f"selects sem controle visual: {cruas}"

def test_select_curto_vira_chips_e_longo_vira_picker():
    for tipo, campo in campos():
        if campo["type"] != "select":
            continue
        esperado = "chips" if len(campo.get("options") or []) <= 8 else "picker"
        assert campo.get("ui") in {esperado, "ratio"}, f"{tipo}.{campo['key']}"
```

### 6.4 Visibilidade condicional

Campo irrelevante não fica cinza — some. A condição vive no catálogo:

```python
{"key": "wangp_settings", "label": "Ajustes WanGP", "type": "json",
 "show_if": {"engine": "wangp"}}

{"key": "width", "label": "Largura", "type": "number", "min": 64, "max": 8192, "ui": "slider",
 "show_if": {"any": [{"aspect_ratio": "manual"}, {"resolution": "manual"}]}}
```

Um `show_if` apontando para campo inexistente esconderia o campo para sempre. Isso é erro de teste, não de runtime:

```python
def test_show_if_referencia_campo_que_existe():
    for item in NODE_CATALOG:
        chaves = {c["key"] for c in item.get("fields", [])}
        for campo in item.get("fields", []):
            regra = campo.get("show_if")
            if not regra:
                continue
            for clausula in (regra.get("any") or regra.get("all") or [regra]):
                for chave in clausula:
                    assert chave in chaves, f"{item['type']}.{campo['key']} depende de {chave!r} inexistente"
```

---

## 7. SISTEMA DE PORTAS E CONEXÕES

O canvas não conecta qualquer coisa em qualquer coisa. Toda conexão é tipada, colorida, iconizada e categorizada. Os pontos de conexão ficam **ao lado do nó**, transparentes por padrão, e aparecem por proximidade do cursor.

### 7.1 Comportamento de conexão `[IMPLEMENTADO no núcleo, ESPECIFICADO no restante]`

| Comportamento | Regra |
| --- | --- |
| Aparecer | pontos ficam invisíveis até o cursor entrar num raio de 120 px do nó; opacidade cresce com a proximidade |
| Arrastar | pressionar em uma porta inicia o vínculo; um traço segue o cursor com a cor do tipo de origem |
| Compatibilidade | ao arrastar, só as portas compatíveis acendem; incompatíveis apagam |
| Soltar no vazio | abre o menu de nós que aceitam aquele tipo, já filtrado e ordenado por frequência de uso |
| Luz no fio | o vínculo tem três camadas: brilho, traço e partícula de fluxo que corre durante a execução |
| Desfazer | arrastar a partir de uma porta já conectada desconecta e re-arrasta |
| Ancoragem | portas ancoram a 30 px do topo com espaçamento fixo, para que cartões altos não joguem porta sobre o vizinho |

```js
/** Cor e ícone por tipo de porta. Categorização visível antes de qualquer texto. */
export const PORT_TYPES = {
  text:      { color: "#7a5af8", icon: "texto",         label: "Texto" },
  prompt:    { color: "#9b7bff", icon: "texto",         label: "Prompt estruturado" },
  image:     { color: "#1d6bf3", icon: "imagem",        label: "Imagem" },
  image_set: { color: "#3d84ff", icon: "lote",          label: "Conjunto de imagens" },
  mask:      { color: "#5aa9ff", icon: "mascara",       label: "Máscara" },
  depth:     { color: "#00b4d8", icon: "profundidade",  label: "Profundidade" },
  normal:    { color: "#38b6a0", icon: "normais",       label: "Normais" },
  pose:      { color: "#e0b400", icon: "pose",          label: "Pose" },
  video:     { color: "#f2762e", icon: "video",         label: "Vídeo" },
  audio:     { color: "#0aa06e", icon: "audio",         label: "Áudio" },
  voice:     { color: "#12b981", icon: "audio",         label: "Voz" },
  mesh:      { color: "#c026d3", icon: "malha3d",       label: "Malha 3D" },
  scene:     { color: "#a21caf", icon: "malha3d",       label: "Cena 3D" },
  material:  { color: "#d946ef", icon: "cor",           label: "Material PBR" },
  rig:       { color: "#f43f5e", icon: "personagem",    label: "Rig" },
  motion:    { color: "#fb7185", icon: "movimento",     label: "Movimento" },
  human_dna: { color: "#e11d48", icon: "personagem",    label: "DNA humano" },
  cad:       { color: "#64748b", icon: "planta",        label: "CAD" },
  bim:       { color: "#475569", icon: "arquitetura",   label: "BIM" },
  geo:       { color: "#16a34a", icon: "mapa",          label: "Geo" },
  world:     { color: "#15803d", icon: "mapa",          label: "Mundo" },
  knowledge: { color: "#0891b2", icon: "conhecimento",  label: "Conhecimento" },
  model_ref: { color: "#7c3aed", icon: "processador",   label: "Modelo" },
  evidence:  { color: "#84cc16", icon: "evidencia",     label: "Evidência" },
  media:     { color: "#8a93a6", icon: "fluxo",         label: "Mídia (qualquer)" },
};
```

### 7.2 Catálogo canônico de tipos de porta

| Tipo canônico | Nome no front | Payload | Uso |
| --- | --- | --- | --- |
| `TEXT` | Texto | string UTF-8 | prompt, legenda, roteiro |
| `PROMPT_SPEC` | Prompt estruturado | `PromptIR` | prompt compilado, restrições, câmera |
| `IMAGE` | Imagem | `ImageAsset` | frame único |
| `IMAGE_SET` | Conjunto de imagens | `List<ImageAsset>` | multi-referência, turntable |
| `ALPHA_IMAGE` | Imagem RGBA | `ImageAsset+alpha` | recorte, camada |
| `MASK` | Máscara | `MaskAsset` | segmentação, roto |
| `DEPTH` | Profundidade | `DepthMap` | métrico ou relativo, com calibração |
| `NORMAL` | Normais | `NormalMap` | tangent, world ou object space |
| `EDGE` | Contorno | `EdgeMap` | canny, lineart, HED |
| `POSE_2D` | Pose 2D | `KeypointSet2D` | corpo, mãos, face |
| `POSE_3D` | Pose 3D | `KeypointSet3D` | espaço de esqueleto |
| `SEGMENTATION` | Segmentação | `SemanticMap` | classes e instâncias |
| `OPTICAL_FLOW` | Fluxo óptico | `FlowField` | movimento temporal |
| `CAMERA` | Câmera | `CameraSpec` | intrínsecos e extrínsecos |
| `LENS` | Lente | `LensSpec` | focal, abertura, distorção |
| `LIGHT_RIG` | Rig de luz | `LightRig` | fontes, HDRI, exposição |
| `COLOR_PROFILE` | Perfil de cor | `ColorTransform` | OCIO, ACES, display |
| `LUT` | LUT | `LUTAsset` | grade e look |
| `HDRI` | HDRI/EXR | `EnvironmentMap` | iluminação baseada em imagem |
| `VIDEO` | Vídeo | `VideoAsset` | clipe |
| `FRAME_SEQUENCE` | Sequência | `FrameSequence` | EXR, PNG, stream de frames |
| `TIMELINE` | Timeline | `TimelineSpec` | shots, trilhas, marcadores |
| `AUDIO` | Áudio | `AudioAsset` | forma de onda |
| `VOICE` | Voz | `VoiceTrack` | fala |
| `SPEAKER_PROFILE` | Perfil de voz | `SpeakerProfile` | embedding com consentimento |
| `MUSIC` | Música | `AudioAsset` | estéreo ou multipista |
| `STEMS` | Stems | `StemSet` | voz, bateria, baixo, resto |
| `TRANSCRIPT` | Transcrição | `TimedTranscript` | palavra com timestamp |
| `MESH` | Malha 3D | `MeshAsset` | triângulos ou quads com topologia |
| `POINT_CLOUD` | Nuvem de pontos | `PointCloud` | XYZ, RGB, intensidade |
| `GAUSSIAN_SPLAT` | Gaussian splat | `GaussianScene` | 3DGS |
| `NERF` | NeRF | `NeRFScene` | campo de radiância |
| `UV_SET` | UV | `UVSet` | ilhas e tiles |
| `TEXTURE_SET` | Texturas | `TextureSet` | basecolor, normal, roughness |
| `PBR_MATERIAL` | Material PBR | `PBRMaterial` | OpenPBR, MaterialX |
| `SKELETON` | Esqueleto | `Skeleton` | ossos e juntas |
| `RIG` | Rig | `RigAsset` | esqueleto com restrições |
| `BLENDSHAPES` | Face shapes | `BlendShapeSet` | expressões e visemas |
| `MOTION` | Movimento | `MotionClip` | BVH, FBX, glTF anim |
| `HUMAN_DNA` | DNA humano | `HumanDNA` | identidade paramétrica versionada |
| `ANIMAL_DNA` | DNA animal | `AnimalDNA` | forma, pelo, rig, perfil de movimento |
| `VEHICLE_DNA` | DNA de veículo | `VehicleDNA` | carroceria, rodas, materiais, física |
| `CAD_DOC` | Documento CAD | `CadDocument` | B-Rep, sketch, restrições |
| `DWG_DXF` | DWG/DXF | `CadExchange` | desenho 2D e 3D |
| `BIM_IFC` | BIM/IFC | `IfcModel` | entidades IFC |
| `FLOORPLAN` | Planta | `FloorplanGraph` | paredes, aberturas, cômodos |
| `GIS_LAYER` | Camada GIS | `GeoLayer` | vetorial ou raster |
| `RASTER_GEO` | Raster geo | `GeoRaster` | DEM, ortofoto, imagery |
| `CRS` | Sistema de coordenadas | `CRSSpec` | EPSG, WKT |
| `GEOREF` | Georreferência | `GeoReference` | origem e transformação |
| `TILES_3D` | 3D Tiles | `TilesetRef` | tileset local ou de provider |
| `SCENE` | Cena 3D | `SceneGraph` | nós, assets, materiais |
| `WORLD_STATE` | Estado do mundo | `WorldState` | terreno, vias, edifícios, clima |
| `ASSET` | Asset | `AssetRef` | qualquer recurso versionado |
| `ASSET_SET` | Pacote de assets | `AssetCollection` | coleção |
| `METADATA` | Metadata | `MetadataMap` | EXIF, XMP, custom |
| `GEO_METADATA` | Geo metadata | `GeoMetadata` | GPS, endereço, CRS, proveniência |
| `LLM_MESSAGE` | Mensagem IA | `Message` | chat e tool |
| `EMBEDDING` | Embedding | `Vector` | representação vetorial |
| `KNOWLEDGE_PACK` | Pacote de conhecimento | `KnowledgePack` | fontes verificadas |
| `TOOL` | Ferramenta | `ToolRef` | MCP, CLI, API, comando |
| `MODEL_REF` | Modelo | `ModelRef` | hash, runtime, licença |
| `DEVICE_PROFILE` | Hardware | `DeviceProfile` | GPU, RAM, capacidades |
| `JOB` | Job | `JobRef` | execução longa resumível |
| `EVIDENCE` | Evidência | `EvidenceBundle` | testes e proveniência |
| `EVENT` | Evento | `EventEnvelope` | controle e barramento |
| `BOOLEAN` | Sim/Não | `bool` | condição |
| `NUMBER` | Número | `float`/`int` | parâmetro |
| `SEED` | Seed | `uint64` | reprodutibilidade |
| `JSON` | Dados JSON | `JSONValue` | configuração |
| `TABLE` | Tabela | `TableAsset` | CSV, Arrow, Parquet |

### 7.3 Naturezas de conexão

```yaml
connection_kinds:
  DATA_SINGLE:   "um valor materializado"
  DATA_BATCH:    "lista ou lote; suporta map automático"
  STREAM:        "frames, áudio, tokens ou chunks em fluxo"
  CONTROL:       "ordem de execução sem transportar asset principal"
  EVENT:         "evento assíncrono"
  CONDITIONAL:   "ramo verdadeiro, falso ou multi-caso"
  REFERENCE:     "referência imutável a asset ou modelo"
  STATE:         "estado versionado: continuidade, DNA, estado do mundo"
  TIMELINE:      "sincronização temporal"
  SPATIAL:       "transformação, CRS, espaço de câmera"
  RESOURCE:      "GPU, residência de modelo, cache"
  EVIDENCE:      "proveniência, teste, score, validação"
  ERROR:         "erro tipado e recuperável"
  LOOP_BOUNDED:  "iteração explícita com max_iterations e timeout"
```

Cardinalidades permitidas: 1→1, 1→N (fan-out), N→1 (fan-in), lote `List<T>`, stream, condição, switch/case, merge, zip, join por tempo, join por asset ID, join por espaço do mundo, gatilho de evento, subgrafo, chamada de workflow, map/foreach, retry limitado, feedback apenas por nó `LAÇO LIMITADO`, aresta de cache, aresta somente-preview, aresta de controle, aresta de erro, aresta de evidência.

### 7.4 Regras duras do validador

1. Ciclo livre é bloqueado.
2. Laço exige `max_iterations`, `timeout` e `stop_condition`.
3. Conversão implícita perigosa é proibida.
4. Conversão segura insere adapter automaticamente e **avisa qual inseriu**.
5. `IMAGE → IMAGE_SET` é alargamento seguro.
6. `MESH → SCENE` insere `MeshToSceneAdapter`.
7. `DWG → BIM_IFC` **não é cast**: exige fluxo interpretativo explícito.
8. `GPS → CRS` **não é cast**: exige transformação geodésica declarada.
9. `HUMAN_DNA` e `SPEAKER_PROFILE` carregam consentimento e proveniência; aresta sem eles é recusada.
10. Portas incompatíveis ficam visualmente impossíveis de conectar, não apenas rejeitadas depois.

### 7.5 Auto-inserção de adapter, com explicação

```
IMAGE ──────► nó que exige IMAGE_SET
                   │
                   ▼
        insere [IMAGEM PARA LOTE] e mostra o selo "adapter automático"
```

```
DWG ───X───► BIM

  "DWG é desenho vetorial. BIM exige interpretação semântica de parede,
   abertura e cômodo. Inserir o fluxo DWG PARA BIM INTERPRETADO?"
                       [ Inserir fluxo ]   [ Cancelar ]
```

O sistema educa em vez de esconder complexidade real.

### 7.6 Depuração visual na aresta

Modo normal mostra o essencial. Modo governança mostra tudo: resolução, contagem de frames, fps, espaço de cor, shape do tensor, vértices e faces, CRS, tamanho em disco, acerto de cache, latência, pico de VRAM.

---

## 8. TUTORIAL OBRIGATÓRIO EM TODO NÓ

O tutorial não é documentação separada. É parte do `NodeManifest`, e nó sem tutorial preenchido não passa no `GATE-UI`.

### 8.1 Conteúdo mínimo

O que faz; quando usar; quando **não** usar; entradas; saídas; modo rápido; modo qualidade; modo baixa VRAM; presets; exemplo visual; exemplo de conexão; erros comuns; como corrigir; recursos estimados; licença e limitações em modo governança; modelo e backend efetivamente usados após a execução; link para workflow de exemplo que abre no canvas.

### 8.2 Tipos e componente

```tsx
type TutorialSection = {
  title: string;
  body: string;
  media?: AssetRef[];
  relatedNodeIds?: string[];
};

type NodeTutorial = {
  summary: string;
  bestFor: string[];
  avoidWhen: string[];
  quickStart: TutorialSection[];
  inputs: PortDoc[];
  outputs: PortDoc[];
  presets: PresetDoc[];
  troubleshooting: { symptom: string; cause: string; fix: string }[];
  performance: { profile: string; vramGb: number; secondsEstimate: number }[];
  exampleWorkflowId: string | null;
};

export function NodeTutorialButton({ nodeId, tutorial }: { nodeId: string; tutorial: NodeTutorial }) {
  const [open, setOpen] = React.useState(false);
  return (
    <>
      <button className="node-help" aria-label={`Abrir tutorial de ${nodeId}`} onClick={() => setOpen(true)}>
        <Icon name="tutorial" /> Tutorial
      </button>
      <NodeTutorialDrawer
        open={open}
        onClose={() => setOpen(false)}
        tutorial={tutorial}
        showTechnicalDetails={useGovernanceMode()}
      />
    </>
  );
}

export function NodeTutorialDrawer({ open, onClose, tutorial, showTechnicalDetails }: DrawerProps) {
  if (!open) return null;
  return (
    <aside className="tutorial-drawer" role="dialog" aria-modal="true">
      <header>
        <Icon name="tutorial" size={18} />
        <h3>{tutorial.summary}</h3>
        <button onClick={onClose} aria-label="Fechar"><Icon name="erro" /></button>
      </header>

      <TutorialList icon="concluido" title="Bom para"   items={tutorial.bestFor} />
      <TutorialList icon="atencao"   title="Evite quando" items={tutorial.avoidWhen} />

      <section className="tutorial-ports">
        <PortDocTable title="Entradas" docs={tutorial.inputs} />
        <PortDocTable title="Saídas"   docs={tutorial.outputs} />
      </section>

      <PresetGallery presets={tutorial.presets} />

      <section className="tutorial-perf">
        <h4><Icon name="processador" /> Recursos estimados</h4>
        <table>
          <tbody>
            {tutorial.performance.map(p => (
              <tr key={p.profile}>
                <th>{p.profile}</th>
                <td>{p.vramGb} GB</td>
                <td>~{p.secondsEstimate} s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <TroubleshootingList items={tutorial.troubleshooting} />

      {tutorial.exampleWorkflowId && (
        <button className="btn primary" onClick={() => openExample(tutorial.exampleWorkflowId!)}>
          Abrir fluxo de exemplo no canvas
        </button>
      )}

      {showTechnicalDetails && <TechnicalProvenancePanel />}
    </aside>
  );
}
```

### 8.3 Manifesto de nó — contrato completo

```yaml
node:
  id: "video.generate.cinema_pro"
  display_name_ptbr: "FILME 4K CINEMA PRO"
  short_description_ptbr: "Gera ou estende vídeo cinematográfico com áudio opcional."
  icon: "video"
  category: "VIDEO"
  capability_slot: "slot://video.generate.high_quality"
  version: "1.0.0"
  status: "IMPLEMENTADO"     # IMPLEMENTADO | PARCIAL | ESPECIFICADO

  ports:
    inputs:
      - { id: prompt,      type: PROMPT_SPEC, required: true }
      - { id: references,  type: IMAGE_SET,   required: false }
      - { id: first_frame, type: IMAGE,       required: false }
      - { id: last_frame,  type: IMAGE,       required: false }
      - { id: camera,      type: CAMERA,      required: false }
      - { id: timeline,    type: TIMELINE,    required: false }
    outputs:
      - { id: video,    type: VIDEO }
      - { id: audio,    type: AUDIO, optional: true }
      - { id: metadata, type: METADATA }
      - { id: evidence, type: EVIDENCE }

  fields:
    - { key: aspect_ratio, label: "Formato",     type: select, ui: ratio,  options: ["1:1","4:5","9:16","2:3","3:2","4:3","16:9","1.85:1","2:1","2.39:1","21:9","manual"] }
    - { key: resolution,   label: "Resolução",   type: select, ui: chips,  options: ["base","HD","FHD","2K","4K","manual"] }
    - { key: duration,     label: "Duração",     type: number, ui: slider, min: 1, max: 15, step: 0.5, unit: "s" }
    - { key: fps,          label: "FPS",         type: select, ui: chips,  options: [24,25,30,48,50,60] }
    - { key: quality,      label: "Qualidade",   type: select, ui: chips,  options: ["rascunho","padrão","cinema","ultra"] }
    - { key: camera_motion,label: "Movimento",   type: select, ui: picker, options: ["<25 movimentos>"] }
    - { key: camera_look,  label: "Acabamento",  type: select, ui: picker, options: ["<14 looks>"] }
    - { key: seed,         label: "Seed",        type: number, ui: seed }

  ui:
    preview: "video"
    tutorial_required: true
    advanced_panel: true

  execution:
    router_policy: "QUALITY_FIRST_WITH_RESOURCE_CAP"
    job_kind: "RESUMABLE"
    cancelable: true
    cacheable: true
    estimated_vram_gb: 18

  tutorial:
    summary: "Gera vídeo cinematográfico a partir de texto, imagem ou par de frames."
    bestFor: ["planos de até 15 s", "continuidade entre shots", "master 4K"]
    avoidWhen: ["GPU com menos de 8 GB no perfil cinema", "clipe acima de 30 s em um único nó"]
    troubleshooting:
      - symptom: "Sem memória no meio da geração"
        cause: "perfil cinema em 4K nativo com outro modelo residente"
        fix: "reduzir para FHD e usar MASTER FINAL para subir a 4K, ou derrubar o ComfyUI"
    performance:
      - { profile: "rascunho FHD", vramGb: 9,  secondsEstimate: 70 }
      - { profile: "cinema FHD",   vramGb: 15, secondsEstimate: 400 }
```

---
## 9. CATEGORIAS DO PAINEL

Cada categoria tem ícone próprio, cor de fundo de miniatura e ordem fixa. Nó novo entra numa categoria existente ou justifica a criação de uma nova por ADR.

| Categoria | Ícone | Finalidade |
| --- | --- | --- |
| ESSENCIAL | `icon:fluxo` | entradas, saídas, transformações, lógica, cache, preview |
| DIREÇÃO IA | `icon:agente` | roteiro, prompt, planos, câmera, estilo, continuidade |
| IMAGEM | `icon:imagem` | geração, edição, multi-referência, camadas |
| CONTROLE VISUAL | `icon:profundidade` | depth, normal, pose, máscara, contorno, segmentação |
| VÍDEO E FILME | `icon:video` | T2V, I2V, start/end, extensão, shots, edição |
| PÓS E RESTAURAÇÃO | `icon:progresso` | upscale, denoise, deblur, interpolação, restauro de rosto |
| COR E VFX | `icon:cor` | OCIO/ACES, LUT, relight, keying, composição, escopos |
| 3D E ASSETS | `icon:malha3d` | imagem→3D, texto→3D, malha, UV, PBR, splats |
| PERSONAGEM | `icon:personagem` | DNA humano, corpo, rosto, rig, cabelo, lipsync |
| ANIMAL E CRIATURA | `icon:animal` | forma, pelo, rig, movimento |
| VEÍCULO E OBJETO PARAMÉTRICO | `icon:processador` | carro, moto, mobiliário, produto |
| MOVIMENTO | `icon:movimento` | mocap, retarget, IK, clone de movimento |
| ÁUDIO E VOZ | `icon:audio` | ASR, TTS, voz, SFX, música, stems, mixagem |
| ARQUITETURA | `icon:arquitetura` | planta, CAD, BIM, telhado, cômodos, mobília |
| GIS E MUNDO REAL | `icon:mapa` | OSM, Overture, DEM, Cesium, 3D Tiles, georreferência |
| NATUREZA PROCEDURAL | `icon:natureza` | árvores, plantas, grama, água, terreno, montanhas |
| UI E CÓDIGO | `icon:codigo` | screenshot→UI, agente de código, verificação visual |
| CONHECIMENTO | `icon:conhecimento` | RAG, grafo, embeddings, validação, COSMETA |
| TREINAMENTO | `icon:treinamento` | SFT, LoRA, QLoRA, DPO, avaliação, destilação |
| MODELOS E INFERÊNCIA | `icon:processador` | runtime, quantização, VRAM, serving |
| ROTEAMENTO E SISTEMA | `icon:roteador` | mega-roteador, agendador, recursos, jobs |
| EXPORTAÇÃO | `icon:saida` | GLB/USD/IFC/EXR/vídeo/web/game/film |

---

## 10. CATÁLOGO CANÔNICO DE NÓS

A coluna **Motor técnico** é governança. O usuário nunca a vê no modo normal. A coluna **Comfy** indica reuso: `CORE` = nó nativo do ComfyUI, `CUSTOM` = custom node vendorado com pin, `ADAPTER` = adaptador nosso sobre serviço externo, `WORKFLOW` = subgrafo composto, `OUTSIDE` = executa fora do ComfyUI, `N/A` = não se aplica.

A coluna **Est.** é o status honesto: `IMP` implementado com teste, `PAR` parcial, `ESP` apenas especificado.

### 10.1 ESSENCIAL

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:entrada` | IMPORTAR ARQUIVO | `asset.import` | arquivo → ASSET | core Rust / FastAPI | N/A | IMP |
| `icon:imagem` | IMPORTAR IMAGENS | `image.import` | arquivos → IMAGE_SET | OpenImageIO / Pillow | ADAPTER | IMP |
| `icon:video` | IMPORTAR VÍDEO | `video.import` | arquivo → VIDEO | FFmpeg | ADAPTER | IMP |
| `icon:audio` | IMPORTAR ÁUDIO | `audio.import` | arquivo → AUDIO | FFmpeg / libsndfile | ADAPTER | IMP |
| `icon:malha3d` | IMPORTAR 3D | `spatial.import` | GLB/USD/OBJ → SCENE | Assimp / Blender / OpenUSD | ADAPTER | ESP |
| `icon:planta` | IMPORTAR CAD | `cad.import` | DWG/DXF/STEP → CAD_DOC | LibreDWG / OpenCascade | OUTSIDE | ESP |
| `icon:arquitetura` | IMPORTAR BIM | `bim.import` | IFC → BIM_IFC | IfcOpenShell | OUTSIDE | ESP |
| `icon:mapa` | IMPORTAR GIS | `gis.import` | GeoJSON/GeoParquet → GIS_LAYER | GDAL / OGR | OUTSIDE | ESP |
| `icon:conhecimento` | IMPORTAR DOCUMENTOS | `knowledge.import` | documentos → ASSET_SET | parsers + core | OUTSIDE | ESP |
| `icon:texto` | TEXTO | `input.text` | UI → TEXT | core | N/A | IMP |
| `icon:lote` | VALOR NUMÉRICO | `value.number` | UI → NUMBER | core | N/A | IMP |
| `icon:cache` | SEED CONTROLADA | `value.seed` | UI → SEED | core | N/A | IMP |
| `icon:fluxo` | CONVERTER TIPO | `type.adapter` | T → U | adaptadores tipados | N/A | PAR |
| `icon:fluxo` | ESCOLHER CAMINHO | `flow.switch` | condição → ramo | core Rust | N/A | ESP |
| `icon:fluxo` | MESCLAR | `flow.merge` | N → 1 | core Rust | N/A | ESP |
| `icon:lote` | PROCESSAR EM LOTE | `flow.foreach` | List\<T\> → List\<U\> | core Rust | N/A | ESP |
| `icon:laco` | LAÇO LIMITADO | `flow.loop_bounded` | estado → estado | core Rust | N/A | ESP |
| `icon:laco` | TENTAR NOVAMENTE | `flow.retry_bounded` | erro → nova tentativa | core Rust | N/A | ESP |
| `icon:cache` | CACHE INTELIGENTE | `cache.smart` | T → T | armazenamento por conteúdo | N/A | PAR |
| `icon:imagem` | PREVIEW UNIVERSAL | `output.preview` | ASSET → preview | web workers | N/A | IMP |
| `icon:evidencia` | VALIDAR RESULTADO | `verify.generic` | T → EVIDENCE | runtime de verificadores | N/A | ESP |
| `icon:texto` | ANOTAR METADATA | `metadata.attach` | T + METADATA → T | core | N/A | ESP |
| `icon:consentimento` | MANIFESTO DE CONSENTIMENTO | `consent.manifest` | sujeito → CONSENT | trusted core | N/A | ESP |

### 10.2 DIREÇÃO IA

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:agente` | ENTENDER PEDIDO | `prompt.intent` | TEXT → PROMPT_SPEC | LLM local roteado | ADAPTER | PAR |
| `icon:agente` | MELHORAR PEDIDO | `llm.enhance` | TEXT + refs → PROMPT_SPEC | Prompt Compiler + Ollama | ADAPTER | IMP |
| `icon:video` | DIRETOR DE CENA | `director.scene` | roteiro → plano de shots | slot de raciocínio | ADAPTER | ESP |
| `icon:texto` | ROTEIRO PARA PLANOS | `director.shot_breakdown` | TEXT → TIMELINE | agente LLM/VLM | ADAPTER | ESP |
| `icon:camera` | DIRETOR DE CÂMERA | `director.camera` | cena → CAMERA + LENS | LLM + regras determinísticas | ADAPTER | ESP |
| `icon:luz` | DIRETOR DE LUZ | `director.light` | cena → LIGHT_RIG | regras + VLM | ADAPTER | ESP |
| `icon:cor` | DIRETOR DE LOOK | `director.look` | refs → ColorSpec | VLM + extração de paleta | ADAPTER | ESP |
| `icon:personagem` | BÍBLIA DO PERSONAGEM | `continuity.character_bible` | refs → HUMAN_DNA + estado | VLM + registry | ADAPTER | ESP |
| `icon:arquitetura` | BÍBLIA DO LOCAL | `continuity.location_bible` | refs → WORLD_STATE | VLM + espacial | ADAPTER | ESP |
| `icon:personagem` | TRAVA DE FIGURINO | `continuity.wardrobe` | refs → estado | VLM + embeddings | ADAPTER | ESP |
| `icon:lote` | TRAVA DE OBJETOS | `continuity.props` | refs → estado | VLM + segmentação | ADAPTER | ESP |
| `icon:cor` | TRAVA DE KEY VISUAL | `continuity.keyvisual` | refs → estado | embeddings + mapas | ADAPTER | ESP |
| `icon:personagem` | TRAVA DE IDENTIDADE | `continuity.identity` | HUMAN_DNA → estado | descritores de face e corpo | ADAPTER | ESP |
| `icon:evidencia` | JUIZ VISUAL | `judge.visual` | asset + alvo → EVIDENCE | VLM + métricas determinísticas | ADAPTER | ESP |
| `icon:evidencia` | JUIZ DE CONTINUIDADE | `judge.continuity` | shot + estado → EVIDENCE | conjunto multi-métrica | ADAPTER | ESP |
| `icon:progresso` | REPARO AUTOMÁTICO | `repair.auto` | asset + erros → asset | máscara + regeneração regional | ADAPTER | ESP |
| `icon:roteador` | SELETOR DE MODELO | `router.model` | tarefa → MODEL_REF | Mega Roteador | OUTSIDE | PAR |
| `icon:processador` | PLANEJAR VRAM | `router.vram` | grafo + device → plano | Resource Planner | OUTSIDE | ESP |
| `icon:texto` | COMPILAR PROMPT POR MOTOR | `prompt.adapter` | PROMPT_SPEC → TEXT/JSON | adaptadores por modelo | OUTSIDE | PAR |
| `icon:atencao` | LINT DE PROMPT | `prompt.lint` | PROMPT_SPEC → EVIDENCE | regras determinísticas | OUTSIDE | ESP |

### 10.3 IMAGEM

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:progresso` | IMAGEM ULTRA RÁPIDA | `image.generate.fast` | PROMPT_SPEC → IMAGE | slot: FLUX.2 klein / Z-Image | CORE | IMP |
| `icon:imagem` | IMAGEM QUALITY PRO | `image.generate.quality` | PROMPT_SPEC → IMAGE | slot: Qwen-Image / FLUX / HunyuanImage | CORE | IMP |
| `icon:imagem` | IMAGEM MASTER 4K | `image.workflow.4k` | prompt + refs → IMAGE | geração + restauro + upscale | WORKFLOW | PAR |
| `icon:imagem` | IMAGEM MASTER 8K | `image.workflow.8k` | prompt + refs → IMAGE | multi-estágio com tiles | WORKFLOW | ESP |
| `icon:imagem` | IMAGEM MASTER 16K | `image.workflow.16k` | prompt + refs → IMAGE | tiles hierárquicos + QC | WORKFLOW | ESP |
| `icon:lote` | VÁRIAS REFERÊNCIAS PARA IMAGEM | `image.multi_reference` | IMAGE_SET + prompt → IMAGE | Qwen-Image-Edit / FLUX refs | CORE | ESP |
| `icon:imagem` | EDITAR IMAGEM POR TEXTO | `image.edit` | IMAGE + prompt → IMAGE | Qwen-Image-Edit / FLUX Kontext | CORE | ESP |
| `icon:imagem` | RENDER PARA FOTO REAL | `image.rerender` | IMAGE + mapas → IMAGE | controle estrutural + modelo | WORKFLOW | ESP |
| `icon:arquitetura` | ARQVIZ FOTO REAL | `image.archviz` | CAD/IMAGE + mapas → IMAGE | Qwen/FLUX/Hunyuan + ControlNet | WORKFLOW | ESP |
| `icon:lote` | GERAR CAMADAS EDITÁVEIS | `image.layers` | IMAGE → camadas ALPHA | Qwen-Image-Layered | ADAPTER | ESP |
| `icon:mascara` | PREENCHER ÁREA | `image.inpaint` | IMAGE + MASK → IMAGE | slot de inpainting | CORE | ESP |
| `icon:imagem` | EXPANDIR QUADRO | `image.outpaint` | IMAGE + canvas → IMAGE | slot de outpaint | CORE | ESP |
| `icon:contorno` | MANTER COMPOSIÇÃO | `image.structure_lock` | IMAGE + mapas → IMAGE | ControlNet / T2I-Adapter | ADAPTER | ESP |
| `icon:personagem` | MANTER PESSOA | `image.identity_lock` | IMAGE_SET + DNA → IMAGE | PuLID / PhotoMaker / InstantID | CUSTOM | ESP |
| `icon:cor` | MANTER ESTILO | `image.style_lock` | refs → IMAGE | IP-Adapter / USO | CUSTOM | ESP |
| `icon:malha3d` | MANTER OBJETO | `image.subject_lock` | refs → IMAGE | adaptadores de sujeito / DreamO | CUSTOM | ESP |
| `icon:texto` | TEXTO PERFEITO NA ARTE | `image.text_render` | prompt/layout → IMAGE | família Qwen-Image | ADAPTER | ESP |
| `icon:mascara` | REMOVER FUNDO | `image.remove_bg` | IMAGE → ALPHA_IMAGE | SAM / modelos de matting | ADAPTER | ESP |
| `icon:malha3d` | GERAR VISTAS DO OBJETO | `image.multiview` | IMAGE → IMAGE_SET | síntese multi-vista / Wonder3D | CUSTOM | ESP |
| `icon:malha3d` | TURNTABLE INTELIGENTE | `image.turntable` | IMAGE/MESH → IMAGE_SET | render 3D ou multiview | WORKFLOW | ESP |
| `icon:camera` | MATCH DE CÂMERA | `image.camera_match` | IMAGE → CAMERA + LENS | VGGT / geometria | ADAPTER | ESP |
| `icon:luz` | RELIGHT FOTO | `image.relight` | IMAGE + LIGHT_RIG → IMAGE | IC-Light / LightCtrl | CUSTOM | ESP |
| `icon:cor` | COLORIZAR | `image.colorize` | IMAGE → IMAGE | DDColor / difusão de cor | ADAPTER | ESP |
| `icon:mascara` | REMOVER OBJETO | `image.object_remove` | IMAGE + MASK → IMAGE | inpaint | CORE | ESP |
| `icon:agente` | DESCREVER IMAGEM | `vision.caption` | IMAGE → TEXT/JSON | slot VLM | ADAPTER | ESP |
| `icon:progresso` | AUMENTAR RESOLUÇÃO | `image.upscale` | IMAGE → IMAGE | Real-ESRGAN NCNN Vulkan | CUSTOM | IMP |

### 10.4 CONTROLE VISUAL

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:segmentacao` | SEGMENTAR TUDO | `vision.segment` | IMAGE/VIDEO → SEGMENTATION | SAM 2 / família SAM | CUSTOM | ESP |
| `icon:mascara` | LOCALIZAR POR TEXTO | `vision.ground` | IMAGE + TEXT → MASK/boxes | GroundingDINO | CUSTOM | ESP |
| `icon:profundidade` | MAPA DE PROFUNDIDADE | `vision.depth` | IMAGE/VIDEO → DEPTH | Depth Anything V2 / Video Depth Anything | CUSTOM | ESP |
| `icon:normais` | NORMAIS DA CENA | `vision.normals` | IMAGE → NORMAL | Marigold / DSINE / MoGe | CUSTOM | ESP |
| `icon:pose` | POSE HUMANA 2D | `vision.pose2d` | IMAGE/VIDEO → POSE_2D | DWPose / OpenPose / DensePose | CUSTOM | ESP |
| `icon:pose` | POSE HUMANA 3D | `vision.pose3d` | VIDEO → POSE_3D | GVHMR / SAM 3D Body | CUSTOM | ESP |
| `icon:contorno` | CONTORNO CANNY | `vision.edge.canny` | IMAGE → EDGE | OpenCV | CORE | ESP |
| `icon:contorno` | LINE ART | `vision.lineart` | IMAGE → EDGE | modelos de lineart | CUSTOM | ESP |
| `icon:planta` | LINHAS ARQUITETÔNICAS | `vision.mlsd` | IMAGE → EDGE | M-LSD | CUSTOM | ESP |
| `icon:contorno` | CONTORNO SUAVE | `vision.softedge` | IMAGE → EDGE | HED / PiDiNet / TEED | CUSTOM | ESP |
| `icon:fluxo_optico` | FLUXO ÓPTICO | `vision.flow` | VIDEO → OPTICAL_FLOW | RAFT | CUSTOM | ESP |
| `icon:malha3d` | EXTRAIR GEOMETRIA | `vision.geometry` | IMAGE_SET → depth/câmera/pontos | VGGT / MapAnything / DUSt3R | ADAPTER | ESP |
| `icon:camera` | ESTIMAR INTRÍNSECOS | `vision.intrinsics` | IMAGE_SET → CAMERA | VGGT | OUTSIDE | ESP |
| `icon:camera` | ESTIMAR TRAJETÓRIA DE CÂMERA | `vision.camera_track` | VIDEO → CAMERA/TIMELINE | COLMAP / VGGT / SLAM | OUTSIDE | ESP |
| `icon:luz` | EXTRAIR ILUMINAÇÃO | `vision.light_estimate` | IMAGE → LIGHT_RIG | inverse rendering | ADAPTER | ESP |
| `icon:cor` | EXTRAIR PALETA | `vision.palette` | IMAGE_SET → ColorSpec | determinístico + VLM | OUTSIDE | ESP |
| `icon:texto` | OCR PROFISSIONAL | `vision.ocr` | IMAGE/PDF → TEXT | PaddleOCR / Tesseract / VLM | OUTSIDE | ESP |
| `icon:planta` | DETECTAR LAYOUT | `vision.layout` | IMAGE → JSON | detector + VLM | OUTSIDE | ESP |
| `icon:segmentacao` | RASTREAR PESSOA OU OBJETO | `vision.track` | VIDEO → tracks | SAM 2 / trackers | CUSTOM | ESP |
| `icon:evidencia` | COMPARAR REFERÊNCIA | `vision.compare` | asset + alvo → EVIDENCE | DINO / CLIP / LPIPS | OUTSIDE | ESP |

### 10.5 VÍDEO E FILME

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:progresso` | FILME RÁPIDO ULTRA 8B | `video.generate.fast8b` | prompt/ref → VIDEO | slot: HunyuanVideo-1.5 8.3B | CORE | PAR |
| `icon:video` | FILME 4K CINEMA PRO | `video.generate.4kpro` | prompt/ref → VIDEO | slot: LTX-2.x + mastering | CORE | ESP |
| `icon:video` | FILME QUALITY MAX | `video.generate.max` | prompt/ref → VIDEO | roteador Wan / Hunyuan / LTX / SkyReels | CORE | ESP |
| `icon:imagem` | IMAGEM PARA VÍDEO | `video.i2v` | IMAGE + prompt → VIDEO | Wan / LTX / Hunyuan | CORE | IMP |
| `icon:texto` | TEXTO PARA VÍDEO | `video.t2v` | PROMPT_SPEC → VIDEO | Wan / LTX / Hunyuan | CORE | IMP |
| `icon:video` | PRIMEIRO E ÚLTIMO FRAME | `video.start_end` | 2 IMAGE + prompt → VIDEO | roteador com first/last | WORKFLOW | ESP |
| `icon:lote` | VÁRIAS IMAGENS PARA FILME | `video.multi_reference` | IMAGE_SET + prompt → VIDEO | roteador multi-referência | WORKFLOW | ESP |
| `icon:laco` | ESTENDER CENA | `video.extend` | VIDEO + prompt → VIDEO | SkyReels / LTX / Wan | CUSTOM | ESP |
| `icon:laco` | CONTINUAR DO ÚLTIMO FRAME | `video.continue` | VIDEO → VIDEO | continuação por último frame | WORKFLOW | ESP |
| `icon:personagem` | ANIMAR PERSONAGEM | `video.character_animate` | IMAGE/DNA + motion → VIDEO | slot de avatar/motion video | CUSTOM | ESP |
| `icon:audio` | PERSONAGEM FALANDO | `video.talking_avatar` | IMAGE/DNA + AUDIO → VIDEO | slot de avatar com lipsync | CUSTOM | ESP |
| `icon:camera` | MOVIMENTO DE CÂMERA | `video.camera_control` | VIDEO/spec → VIDEO | geração condicionada por câmera | CUSTOM | PAR |
| `icon:pose` | CONTROLAR POR POSE | `video.pose_control` | POSE + refs → VIDEO | modelos guiados por pose | CUSTOM | ESP |
| `icon:profundidade` | CONTROLAR POR PROFUNDIDADE | `video.depth_control` | DEPTH + refs → VIDEO | adaptadores de controle | CUSTOM | ESP |
| `icon:malha3d` | 3D PARA VÍDEO REALISTA | `video.3d_rerender` | SCENE + câmera → VIDEO | render + difusão de vídeo | WORKFLOW | ESP |
| `icon:arquitetura` | ARQVIZ PARA FILME REAL | `video.archviz` | SCENE/refs → VIDEO | fluxo de continuidade | WORKFLOW | ESP |
| `icon:agente` | PLANEJAR SEQUÊNCIA | `video.sequence_plan` | roteiro + refs → TIMELINE | Director Agent | OUTSIDE | ESP |
| `icon:video` | CORTAR CENA | `video.trim` | VIDEO + tempo → VIDEO | FFmpeg | ADAPTER | IMP |
| `icon:lote` | JUNTAR CENAS | `video.concat` | VIDEOS → VIDEO | FFmpeg / OpenTimelineIO | ADAPTER | IMP |
| `icon:pendente` | AJUSTAR DURAÇÃO | `video.retime` | VIDEO + duração → VIDEO | RIFE + FFmpeg + fluxo | WORKFLOW | ESP |
| `icon:movimento` | AJUSTAR VELOCIDADE | `video.speed` | VIDEO + fator → VIDEO | FFmpeg + interpolação | ADAPTER | ESP |
| `icon:video` | FIXAR 30 FPS | `video.fps30` | VIDEO → VIDEO | RIFE + FFmpeg | WORKFLOW | PAR |
| `icon:video` | FIXAR 24 FPS CINEMA | `video.fps24` | VIDEO → VIDEO | fluxo + FFmpeg | WORKFLOW | PAR |
| `icon:lente` | FORMATO 21:9 PRO | `video.aspect.cinema` | VIDEO → VIDEO | crop / outpaint / master | WORKFLOW | ESP |
| `icon:lente` | FORMATO VERTICAL 9:16 | `video.aspect.vertical` | VIDEO → VIDEO | crop / outpaint / master | WORKFLOW | ESP |
| `icon:mascara` | REPARAR FRAME | `video.frame_repair` | VIDEO + máscara → VIDEO | inpaint temporal | CUSTOM | ESP |
| `icon:evidencia` | TESTAR CONTINUIDADE | `video.continuity_check` | VIDEO + estado → EVIDENCE | métricas + VLM | OUTSIDE | ESP |
| `icon:audio` | CRIAR SFX DO VÍDEO | `video.foley` | VIDEO → AUDIO | HunyuanVideo-Foley / AudioGen | ADAPTER | ESP |
| `icon:audio` | CRIAR TRILHA | `video.score` | VIDEO + briefing → MUSIC | ACE-Step / AudioCraft | ADAPTER | ESP |
| `icon:saida` | MASTER FINAL | `video.master` | VIDEO + AUDIO → VIDEO | FFmpeg + OCIO + QC | OUTSIDE | PAR |

### 10.6 PÓS E RESTAURAÇÃO

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:progresso` | RESTAURAR VÍDEO PRO | `restore.video` | VIDEO → VIDEO | SeedVR2 | CUSTOM | ESP |
| `icon:progresso` | RESTAURAR IMAGEM PRO | `restore.image` | IMAGE → IMAGE | SUPIR (gate de licença) / alternativas | CUSTOM | ESP |
| `icon:progresso` | AUMENTAR RESOLUÇÃO | `upscale.image` | IMAGE → IMAGE | Real-ESRGAN + upscale por difusão | CUSTOM | IMP |
| `icon:video` | AUMENTAR VÍDEO 4K | `upscale.video4k` | VIDEO → VIDEO | SeedVR2 + tiling | WORKFLOW | PAR |
| `icon:video` | MASTER 8K | `upscale.video8k` | VIDEO → VIDEO | upscale multi-estágio | WORKFLOW | ESP |
| `icon:personagem` | RESTAURAR ROSTO | `restore.face` | IMAGE/VIDEO → asset | CodeFormer / GFPGAN | CUSTOM | ESP |
| `icon:mascara` | REDUZIR RUÍDO | `restore.denoise` | asset → asset | temporal + espacial | ADAPTER | ESP |
| `icon:lente` | REMOVER BLUR | `restore.deblur` | asset → asset | slot de restauração | ADAPTER | ESP |
| `icon:video` | INTERPOLAR FRAMES | `video.interpolate` | VIDEO → VIDEO | RIFE NCNN Vulkan / FILM | CUSTOM | IMP |
| `icon:camera` | ESTABILIZAR | `video.stabilize` | VIDEO → VIDEO | fluxo óptico + FFmpeg vidstab | OUTSIDE | ESP |
| `icon:progresso` | REMOVER FLICKER | `video.deflicker` | VIDEO → VIDEO | estatística temporal | OUTSIDE | ESP |
| `icon:cor` | REMOVER BANDING | `video.deband` | VIDEO → VIDEO | filtros FFmpeg | OUTSIDE | ESP |
| `icon:cor` | GRÃO CINEMATOGRÁFICO | `media.filmlook` | asset → asset | FFmpeg + OIIO | OUTSIDE | IMP |
| `icon:evidencia` | QC VISUAL | `post.qc` | asset → EVIDENCE | VMAF + métricas + VLM | OUTSIDE | ESP |

### 10.7 COR E VFX

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:cor` | ACES E OCIO | `color.ocio` | asset + perfil → asset | OpenColorIO | OUTSIDE | ESP |
| `icon:cor` | GRADE PROFISSIONAL | `color.grade` | asset + params → asset | OCIO + OIIO | OUTSIDE | ESP |
| `icon:lut` | APLICAR LUT | `color.lut` | asset + LUT → asset | OCIO / FFmpeg | OUTSIDE | ESP |
| `icon:escopo` | ESCOPOS DE VÍDEO | `media.scopes` | asset → IMAGE | FFmpeg: waveform, vetorscópio, falsa cor, alfa | OUTSIDE | IMP |
| `icon:luz` | RELIGHT CENA | `vfx.relight` | asset + luz → asset | IC-Light / LightCtrl | CUSTOM | ESP |
| `icon:mascara` | CHROMA KEY | `vfx.key` | VIDEO → RGBA | Natron / FFmpeg | OUTSIDE | ESP |
| `icon:mascara` | ROTOSCOPIA IA | `vfx.roto` | VIDEO → MASK | SAM 2 + tracker | CUSTOM | ESP |
| `icon:lote` | COMPOSIÇÃO | `vfx.composite` | camadas → asset | Natron / compositor do Blender | OUTSIDE | ESP |
| `icon:natureza` | NÉVOA E ATMOSFERA | `vfx.atmosphere` | cena/imagem → asset | 3D procedural ou imagem | WORKFLOW | ESP |
| `icon:movimento` | MOTION BLUR | `vfx.motionblur` | asset + fluxo → asset | fluxo óptico / render | OUTSIDE | ESP |
| `icon:lente` | DISTORÇÃO DE LENTE | `vfx.lens` | asset + LENS → asset | OpenCV / OIIO | OUTSIDE | ESP |

### 10.8 3D E ASSETS

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:malha3d` | IMAGEM PARA 3D PRO | `model3d.generate` | IMAGE → MESH | Hunyuan3D-2 via ComfyUI (implementado) | CUSTOM | IMP |
| `icon:malha3d` | OBJETO PARA 3D QUALITY | `3d.object_quality` | IMAGE_SET → MESH + PBR | roteador TRELLIS.2 / Hunyuan3D / SAM 3D / Pixal3D | WORKFLOW | ESP |
| `icon:progresso` | OBJETO PARA 3D RÁPIDO | `3d.object_fast` | IMAGE → MESH | TripoSR / Stable Fast 3D / InstantMesh | CUSTOM | ESP |
| `icon:texto` | TEXTO PARA 3D | `3d.text_to_3d` | TEXT → MESH | Hunyuan3D / TRELLIS | CUSTOM | ESP |
| `icon:lote` | VÁRIAS VISTAS PARA 3D | `3d.multiview` | IMAGE_SET → MESH | VGGT + gerador | WORKFLOW | ESP |
| `icon:camera` | FOTOS PARA 3D REAL | `3d.reconstruct` | IMAGE_SET → POINT_CLOUD/MESH | COLMAP / VGGT / MASt3R / MUSt3R | OUTSIDE | ESP |
| `icon:video` | VÍDEO PARA CENA 3D | `3d.video_reconstruct` | VIDEO → cena/splat | frames + SfM + 3DGS | OUTSIDE | ESP |
| `icon:splat` | FOTOS PARA GAUSSIAN SPLAT | `3d.gaussian` | IMAGE_SET → GAUSSIAN_SPLAT | gsplat / 3DGS | OUTSIDE | ESP |
| `icon:splat` | FOTOS PARA NERF | `3d.nerf` | IMAGE_SET → NERF | Nerfstudio | OUTSIDE | ESP |
| `icon:malha3d` | GERAR MALHA DO SPLAT | `3d.splat_to_mesh` | GAUSSIAN → MESH | pipeline de meshing | OUTSIDE | ESP |
| `icon:malha3d` | REMESH LIMPO | `3d.remesh` | MESH → MESH | Blender / Open3D / CGAL | OUTSIDE | ESP |
| `icon:malha3d` | RETOPOLOGIA AUTOMÁTICA | `model3d.retopology` | MESH → MESH | decimação + quad tools | OUTSIDE | IMP |
| `icon:malha3d` | ABRIR UV | `3d.uv` | MESH → UV_SET | Blender / xatlas | OUTSIDE | ESP |
| `icon:cor` | TEXTURIZAR 3D | `model3d.texture` | MESH + refs → TEXTURE_SET | Hunyuan3D Paint / difusão de textura | CUSTOM | IMP |
| `icon:cor` | GERAR PBR | `3d.pbr` | texturas/imagem → PBR_MATERIAL | extração + síntese PBR | WORKFLOW | ESP |
| `icon:luz` | EXTRAIR MATERIAL REAL | `3d.material_capture` | IMAGE_SET → PBR_MATERIAL | inverse rendering | OUTSIDE | ESP |
| `icon:cor` | MATERIAL PROCEDURAL | `3d.material_procedural` | params → PBR_MATERIAL | MaterialX / OpenPBR / Blender | OUTSIDE | ESP |
| `icon:evidencia` | VALIDAR MALHA | `3d.mesh_qc` | MESH → EVIDENCE | manifold, normais, UV, escala | OUTSIDE | ESP |
| `icon:processador` | OTIMIZAR GAME READY | `3d.game_ready` | MESH → MESH | LOD, decimate, meshoptimizer | OUTSIDE | ESP |
| `icon:video` | OTIMIZAR FILM READY | `3d.film_ready` | MESH → MESH | alta densidade, UDIM, subdivisão | OUTSIDE | ESP |
| `icon:lote` | GERAR LODs | `3d.lod` | MESH → ASSET_SET | Blender / meshoptimizer | OUTSIDE | ESP |
| `icon:lente` | CORRIGIR ESCALA | `3d.scale` | MESH + unidades → MESH | core espacial | OUTSIDE | ESP |
| `icon:mapa` | ALINHAR AO MUNDO | `3d.align_world` | cena + GEOREF → SCENE | core espacial | OUTSIDE | ESP |
| `icon:luz` | REMOVER LUZ DA TEXTURA | `3d.delight` | TEXTURE_SET → TEXTURE_SET | inverse lighting | CUSTOM | ESP |
| `icon:normais` | BAKE NORMAL E AO | `3d.bake` | MESH → TEXTURE_SET | Blender | OUTSIDE | ESP |
| `icon:fluxo` | CONVERTER 3D | `model3d.export` | 3D → 3D | Blender / OpenUSD / glTF | OUTSIDE | IMP |
| `icon:movimento` | ANIMAR MALHA | `model3d.animate` | MESH + motion → SCENE | rig procedural + Blender | OUTSIDE | IMP |

### 10.9 PERSONAGEM

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:personagem` | DNA HUMANO | `human.dna.build` | IMAGE_SET/VIDEO → HUMAN_DNA | MHR + SAM 3D Body + multiview + medidas | WORKFLOW | ESP |
| `icon:lente` | MEDIR CORPO | `human.measure` | refs → medidas | geometria + ajuste de corpo | OUTSIDE | ESP |
| `icon:personagem` | CORPO 3D PARAMÉTRICO | `human.body_fit` | refs → MESH + parâmetros | MHR / SAM 3D Body; SMPL-X opcional | CUSTOM | ESP |
| `icon:personagem` | ROSTO 3D ALTA DEFINIÇÃO | `human.face_3d` | refs → MESH | reconstrução multi-vista de cabeça | WORKFLOW | ESP |
| `icon:personagem` | DETALHE DE OLHOS | `human.eyes` | DNA → MESH/PBR | modelo anatômico procedural | OUTSIDE | ESP |
| `icon:personagem` | BOCA E DENTES | `human.mouth` | DNA → MESH/PBR | procedural + ajuste de asset | OUTSIDE | ESP |
| `icon:personagem` | ORELHAS ALTA DEFINIÇÃO | `human.ears` | DNA → MESH | reconstrução localizada | WORKFLOW | ESP |
| `icon:personagem` | CABELO REALISTA | `human.hair` | refs → asset de cabelo | Blender curves + groom + visão | OUTSIDE | ESP |
| `icon:personagem` | BARBA E PELOS | `human.facial_hair` | refs → asset de cabelo | curves / groom | OUTSIDE | ESP |
| `icon:cor` | TEXTURA DE PELE | `human.skin_texture` | refs + UV → TEXTURE_SET | projeção + inpaint + normalização de cor | WORKFLOW | ESP |
| `icon:cor` | SSS DE PELE | `human.skin_sss` | DNA/material → PBR | shader OpenPBR / MaterialX | OUTSIDE | ESP |
| `icon:normais` | MICRODETALHE DA PELE | `human.skin_micro` | refs → normal/displacement | síntese de detalhe | WORKFLOW | ESP |
| `icon:personagem` | AUTO RIG HUMANO | `human.autorig` | MESH → RIG | esqueleto MHR / retarget Blender | OUTSIDE | ESP |
| `icon:personagem` | FACE SHAPES | `human.blendshapes` | rosto → BLENDSHAPES | pipeline FACS / visemas | OUTSIDE | ESP |
| `icon:audio` | LIPSYNC | `human.lipsync` | AUDIO + RIG → MOTION | modelo fonema/visema | CUSTOM | ESP |
| `icon:personagem` | EXPRESSÕES FACIAIS | `human.expressions` | controles → MOTION | biblioteca FACS | OUTSIDE | ESP |
| `icon:movimento` | ANIMAÇÃO CORPORAL | `human.motion` | RIG + MOTION → SCENE | retarget + IK | OUTSIDE | ESP |
| `icon:personagem` | VESTIR PERSONAGEM | `human.clothing_fit` | corpo + peça → SCENE | fitting + simulação | OUTSIDE | ESP |
| `icon:personagem` | SIMULAR ROUPA | `human.cloth_sim` | cena → cena | física do Blender | OUTSIDE | ESP |
| `icon:processador` | PERSONAGEM GAME READY | `human.game_ready` | DNA → SCENE | LOD + rig + PBR + export | WORKFLOW | ESP |
| `icon:video` | PERSONAGEM FILM READY | `human.film_ready` | DNA → SCENE | alta resolução + UDIM + groom + blendshapes | WORKFLOW | ESP |
| `icon:remoto` | PERSONAGEM WEB READY | `human.web_ready` | DNA → cena GLB | LOD + KTX2 + meshopt | WORKFLOW | ESP |
| `icon:imagem` | TURNAROUND DO HUMANO | `human.turnaround` | DNA → IMAGE_SET | render canônico 3D | WORKFLOW | ESP |
| `icon:consentimento` | IDENTIDADE VERIFICADA | `human.identity_manifest` | DNA + consentimento → estado | trusted core | OUTSIDE | ESP |
| `icon:evidencia` | QC DE SEMELHANÇA | `human.identity_qc` | render + refs → EVIDENCE | métricas de identidade com consentimento | OUTSIDE | ESP |

### 10.10 ANIMAL, CRIATURA, VEÍCULO E OBJETO PARAMÉTRICO

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:animal` | DNA ANIMAL | `animal.dna` | IMAGE_SET/VIDEO → ANIMAL_DNA | SMAL / 3DAnimals / AnimalAvatar + geração 3D | WORKFLOW | ESP |
| `icon:animal` | ANIMAL PARA 3D | `animal.to3d` | refs → MESH | SMALify + roteador de geração 3D | WORKFLOW | ESP |
| `icon:animal` | RIG QUADRÚPEDE | `animal.rig` | MESH → RIG | esqueleto procedural + ajuste | OUTSIDE | ESP |
| `icon:animal` | PELO E FUR | `animal.fur` | refs + malha → cabelo | Blender hair curves | OUTSIDE | ESP |
| `icon:movimento` | MOVIMENTO ANIMAL | `animal.motion` | VIDEO/RIG → MOTION | pose + retarget | WORKFLOW | ESP |
| `icon:movimento` | MOCAP QUADRÚPEDE | `animal.mocap` | VIDEO → MOTION | slot baseado em SMAL | OUTSIDE | ESP |
| `icon:animal` | CRIATURA CUSTOM | `creature.generate` | refs/texto → MESH | gerador 3D + rig customizado | WORKFLOW | ESP |
| `icon:processador` | ANIMAL GAME READY | `animal.game_ready` | DNA → SCENE | LOD + rig + fur cards | WORKFLOW | ESP |
| `icon:video` | ANIMAL FILM READY | `animal.film_ready` | DNA → SCENE | groom de alta resolução + rig | WORKFLOW | ESP |
| `icon:processador` | CARRO PARAMÉTRICO | `vehicle.car` | spec/refs → VEHICLE_DNA + MESH | CadQuery + Blender geometry nodes + gerador 3D | WORKFLOW | ESP |
| `icon:processador` | MOTO PARAMÉTRICA | `vehicle.bike` | spec/refs → MESH | procedural + gerador | WORKFLOW | ESP |
| `icon:processador` | RODAS E PNEUS | `vehicle.wheels` | spec → MESH + PBR | procedural determinístico | OUTSIDE | ESP |
| `icon:processador` | INTERIOR DE VEÍCULO | `vehicle.interior` | spec → SCENE | biblioteca + solver | WORKFLOW | ESP |
| `icon:movimento` | FÍSICA DE VEÍCULO | `vehicle.physics` | VEHICLE_DNA → estado | motor de física | OUTSIDE | ESP |
| `icon:processador` | MOBILIÁRIO PARAMÉTRICO | `product.furniture` | spec → MESH + PBR | CadQuery / geometry nodes | OUTSIDE | ESP |
| `icon:processador` | PRODUTO PARAMÉTRICO | `product.generic` | spec → CAD_DOC + MESH | CadQuery / OpenCascade | OUTSIDE | ESP |

### 10.11 MOVIMENTO

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:camera` | VÍDEO PARA MOCAP | `motion.video_mocap` | VIDEO → MOTION | GVHMR / pipeline 4D humano | CUSTOM | ESP |
| `icon:movimento` | CLONAR MOVIMENTO CONSENTIDO | `motion.clone` | VIDEO + rig alvo → MOTION | pose 3D + retarget | WORKFLOW | ESP |
| `icon:movimento` | RETARGET AUTOMÁTICO | `motion.retarget` | MOTION + RIG → MOTION | Blender / motor de retarget | OUTSIDE | ESP |
| `icon:movimento` | CORRIGIR PÉS | `motion.footlock` | MOTION → MOTION | IK + otimização | OUTSIDE | ESP |
| `icon:movimento` | IK CORPORAL | `motion.ik` | MOTION + RIG → MOTION | solver IK | OUTSIDE | ESP |
| `icon:movimento` | SUAVIZAR MOCAP | `motion.smooth` | MOTION → MOTION | filtros + otimização | OUTSIDE | ESP |
| `icon:movimento` | CORRIGIR FÍSICA | `motion.physics` | MOTION → MOTION | solver com física | OUTSIDE | ESP |
| `icon:texto` | TEXTO PARA MOVIMENTO | `motion.text` | TEXT → MOTION | HY-Motion | ADAPTER | ESP |
| `icon:lote` | BIBLIOTECA DE GESTOS | `motion.library` | consulta → MOTION | banco de assets | OUTSIDE | ESP |
| `icon:personagem` | EXPRESSÃO PARA FACE | `motion.facial` | controles → MOTION | mapeamento FACS / ARKit-like | OUTSIDE | ESP |
| `icon:remoto` | CAPTURA AO VIVO | `motion.live` | webcam/stream → MOTION | pose em tempo real | OUTSIDE | ESP |

### 10.12 ÁUDIO E VOZ

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:texto` | ÁUDIO PARA TEXTO | `audio.asr` | AUDIO → TRANSCRIPT | Qwen3-ASR / faster-whisper / SenseVoice | ADAPTER | ESP |
| `icon:pendente` | ALINHAR PALAVRAS | `audio.align` | AUDIO + TEXT → TRANSCRIPT | forced aligner | OUTSIDE | ESP |
| `icon:audio` | TEXTO PARA VOZ PRO | `audio.tts` | TEXT → VOICE | IndexTTS2 / F5-TTS / CosyVoice / Chatterbox | ADAPTER | ESP |
| `icon:consentimento` | PERFIL DE VOZ CONSENTIDO | `audio.speaker_profile` | amostras + consentimento → SPEAKER_PROFILE | encoder de locutor | OUTSIDE | ESP |
| `icon:audio` | CLONAR VOZ CONSENTIDA | `audio.voice_clone` | TEXT + perfil → VOICE | slot TTS / conversão de voz | ADAPTER | ESP |
| `icon:remoto` | VOZ AO VIVO CONSENTIDA | `audio.voice_live` | stream + perfil → stream | runtime de baixa latência | OUTSIDE | ESP |
| `icon:fluxo` | VOZ PARA VOZ | `audio.voice_convert` | VOICE + perfil → VOICE | RVC / OpenVoice | ADAPTER | ESP |
| `icon:personagem` | EMOÇÃO DA VOZ | `audio.emotion` | VOICE + controle → VOICE | TTS com estilo e prosódia | ADAPTER | ESP |
| `icon:pendente` | FIXAR DURAÇÃO DA FALA | `audio.duration` | TEXT + tempo → VOICE | IndexTTS2 (timing-aware) | ADAPTER | ESP |
| `icon:personagem` | GERAR VISEMAS | `audio.viseme` | VOICE → MOTION | alinhador de fonemas | OUTSIDE | ESP |
| `icon:audio` | GERAR MÚSICA | `audio.music` | prompt → MUSIC | ACE-Step / AudioCraft / YuE | ADAPTER | ESP |
| `icon:audio` | GERAR SFX | `audio.sfx` | prompt → AUDIO | AudioGen / Foley | ADAPTER | ESP |
| `icon:video` | VÍDEO PARA FOLEY | `audio.foley` | VIDEO → AUDIO | HunyuanVideo-Foley | ADAPTER | ESP |
| `icon:lote` | SEPARAR STEMS | `audio.stems` | AUDIO → STEMS | Demucs / MDX / UVR | OUTSIDE | ESP |
| `icon:mascara` | REMOVER RUÍDO | `audio.denoise` | AUDIO → AUDIO | RNNoise / DeepFilterNet | OUTSIDE | ESP |
| `icon:mascara` | REMOVER REVERB | `audio.dereverb` | AUDIO → AUDIO | restauração de áudio | OUTSIDE | ESP |
| `icon:escopo` | NORMALIZAR LOUDNESS | `audio.loudness` | AUDIO → AUDIO | EBU R128 via FFmpeg | OUTSIDE | ESP |
| `icon:escopo` | MIX MASTER | `audio.mixmaster` | STEMS → AUDIO | DSP determinístico + IA opcional | OUTSIDE | ESP |
| `icon:malha3d` | ESPACIALIZAR ÁUDIO | `audio.spatial` | AUDIO + SCENE → AUDIO | HRTF / Ambisonics | OUTSIDE | ESP |
| `icon:evidencia` | QC DE ÁUDIO | `audio.qc` | AUDIO → EVIDENCE | loudness, clipping, consistência STT | OUTSIDE | ESP |
| `icon:audio` | EXTRAIR ÁUDIO DO VÍDEO | `media.extract_audio` | VIDEO → AUDIO | FFmpeg | ADAPTER | IMP |
| `icon:audio` | JUNTAR ÁUDIO AO VÍDEO | `media.mux_audio` | VIDEO + AUDIO → VIDEO | FFmpeg | ADAPTER | IMP |

### 10.13 MIXAGEM NODAL — CADEIA DE DSP

O DSP principal é determinístico. A IA sugere parâmetros; ela não substitui a matemática.

| Ícone | Nome no front | ID técnico | Motor |
| --- | --- | --- | --- |
| `icon:escopo` | GANHO | `dsp.gain` | FFmpeg / DSP nativo |
| `icon:escopo` | EQUALIZADOR | `dsp.eq` | filtros biquad |
| `icon:escopo` | EQ DINÂMICO | `dsp.dyneq` | DSP nativo |
| `icon:escopo` | COMPRESSOR | `dsp.compressor` | DSP nativo |
| `icon:escopo` | COMPRESSOR MULTIBANDA | `dsp.multiband` | DSP nativo |
| `icon:escopo` | LIMITADOR | `dsp.limiter` | DSP nativo |
| `icon:escopo` | DE-ESSER | `dsp.deesser` | DSP nativo |
| `icon:escopo` | EXPANSOR | `dsp.expander` | DSP nativo |
| `icon:escopo` | GATE | `dsp.gate` | DSP nativo |
| `icon:escopo` | SATURAÇÃO | `dsp.saturation` | DSP nativo |
| `icon:escopo` | MODELADOR DE TRANSIENTE | `dsp.transient` | DSP nativo |
| `icon:escopo` | LARGURA ESTÉREO | `dsp.width` | DSP nativo |
| `icon:escopo` | MID/SIDE | `dsp.midside` | DSP nativo |
| `icon:escopo` | REVERB DE CONVOLUÇÃO | `dsp.convreverb` | convolução com IR |
| `icon:escopo` | REVERB ALGORÍTMICO | `dsp.reverb` | DSP nativo |
| `icon:escopo` | DELAY | `dsp.delay` | DSP nativo |
| `icon:escopo` | PITCH | `dsp.pitch` | phase vocoder |
| `icon:pendente` | TIME STRETCH | `dsp.timestretch` | phase vocoder |
| `icon:escopo` | MEDIDOR DE LOUDNESS | `dsp.loudness_meter` | EBU R128 |
| `icon:escopo` | TRUE PEAK | `dsp.truepeak` | oversampling |
| `icon:escopo` | DITHER | `dsp.dither` | DSP nativo |

### 10.14 ARQUITETURA

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:planta` | LER PLANTA | `arch.floorplan_parse` | IMAGE/PDF → FLOORPLAN | RoomFormer / CubiCasa5K / Raster2Seq | OUTSIDE | ESP |
| `icon:arquitetura` | PLANTA PARA CASA 3D | `arch.floorplan_to_3d` | FLOORPLAN → SCENE | extrusão determinística + enriquecimento tipo Plan2Scene | WORKFLOW | ESP |
| `icon:arquitetura` | PLANTA PARA BIM 3D | `arch.floorplan_to_bim` | FLOORPLAN → BIM_IFC | IfcOpenShell + regras | OUTSIDE | ESP |
| `icon:planta` | DWG PARA PLANTA ESTRUTURADA | `arch.dwg_parse` | DWG_DXF → FLOORPLAN/CAD | LibreDWG + regras geométricas | OUTSIDE | ESP |
| `icon:arquitetura` | DWG PARA BIM INTERPRETADO | `arch.dwg_to_bim` | DWG_DXF → BIM_IFC | parser CAD + inferência semântica + IFC | WORKFLOW | ESP |
| `icon:planta` | GERAR CAD PARAMÉTRICO | `cad.generate` | spec → CAD_DOC | CadQuery / OpenCascade | OUTSIDE | ESP |
| `icon:planta` | SKETCH PARAMÉTRICO | `cad.sketch` | params → CAD_DOC | CadQuery / OCCT | OUTSIDE | ESP |
| `icon:arquitetura` | GERAR PAREDES | `arch.walls` | FLOORPLAN → SCENE/BIM | geometria determinística | OUTSIDE | ESP |
| `icon:arquitetura` | GERAR PORTAS E JANELAS | `arch.openings` | FLOORPLAN → SCENE/BIM | geometria por regra | OUTSIDE | ESP |
| `icon:arquitetura` | GERAR TELHADO PARAMÉTRICO | `arch.roof` | footprint + regras → MESH/BIM | straight skeleton + regras de telhado | OUTSIDE | ESP |
| `icon:arquitetura` | GERAR ESCADAS | `arch.stairs` | restrições → MESH/BIM | regras paramétricas | OUTSIDE | ESP |
| `icon:arquitetura` | GERAR PAVIMENTOS | `arch.floors` | FLOORPLAN → BIM | regras | OUTSIDE | ESP |
| `icon:planta` | DETECTAR CÔMODOS | `arch.rooms` | FLOORPLAN → JSON/BIM | RoomFormer + topologia | OUTSIDE | ESP |
| `icon:arquitetura` | MOBILIAR INTELIGENTE | `arch.furnish` | cômodos + assets → SCENE | PhyScene + solver de layout | OUTSIDE | ESP |
| `icon:lente` | VALIDAR CIRCULAÇÃO | `arch.circulation` | SCENE/BIM → EVIDENCE | navmesh + folgas | OUTSIDE | ESP |
| `icon:cor` | MATERIAIS DA PLANTA | `arch.materials` | spec + refs → PBR | roteador de material | WORKFLOW | ESP |
| `icon:luz` | ESTUDO SOLAR | `arch.solar` | BIM + GEOREF + tempo → EVIDENCE | Ladybug / Radiance | OUTSIDE | ESP |
| `icon:luz` | DAYLIGHT | `arch.daylight` | cena + sol → EVIDENCE | Radiance / Honeybee | OUTSIDE | ESP |
| `icon:escopo` | ENERGIA | `arch.energy` | BIM + clima → EVIDENCE | EnergyPlus / OpenStudio | OUTSIDE | ESP |
| `icon:natureza` | VENTILAÇÃO E CLIMA | `arch.environment` | cena + clima → EVIDENCE | Ladybug / Honeybee | OUTSIDE | ESP |
| `icon:planta` | GERAR PRANCHA | `arch.sheet` | BIM/CAD + vistas → documento | renderizador SVG/PDF | OUTSIDE | ESP |
| `icon:planta` | CORTE AUTOMÁTICO | `arch.section` | BIM/SCENE → CAD/imagem | kernel geométrico | OUTSIDE | ESP |
| `icon:arquitetura` | ELEVAÇÃO AUTOMÁTICA | `arch.elevation` | BIM/SCENE → CAD/imagem | kernel geométrico | OUTSIDE | ESP |
| `icon:malha3d` | AXONOMÉTRICA | `arch.axon` | SCENE/BIM → IMAGE | Blender / renderizador CAD | OUTSIDE | ESP |
| `icon:lote` | QUANTITATIVO BIM | `arch.quantity` | BIM → TABLE | IfcOpenShell | OUTSIDE | ESP |
| `icon:evidencia` | VALIDAR IFC | `arch.ifc_qc` | BIM → EVIDENCE | IfcOpenShell + IDS | OUTSIDE | ESP |
| `icon:arquitetura` | AUTORIA BIM | `arch.bonsai` | BIM ↔ SCENE | Bonsai + Blender | OUTSIDE | ESP |
| `icon:agente` | PLANTA PARA CONCEITO | `arch.concept` | planta + briefing → IMAGE/SCENE | VLM + imagem + geometria | WORKFLOW | ESP |
| `icon:camera` | FOTO PARA MEDIDAS AUXILIARES | `arch.photo_measure` | IMAGE_SET → geometria | VGGT + calibração | OUTSIDE | ESP |
| `icon:lote` | CATÁLOGO DE FAMÍLIAS | `arch.asset_catalog` | consulta → ASSET_SET | banco de assets | OUTSIDE | ESP |

### 10.15 GIS E MUNDO REAL

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:mapa` | ENDEREÇO PARA LOCAL | `geo.geocode` | TEXT → GEO_METADATA | Nominatim local / gazetteer / adapter | OUTSIDE | ESP |
| `icon:mapa` | COORDENADAS PARA CENA | `geo.coords` | GEO → WORLD_STATE | core espacial | OUTSIDE | ESP |
| `icon:mapa` | OPENSTREETMAP PARA MUNDO | `geo.osm_world` | bbox → WORLD_STATE | OSM PBF + osmium | OUTSIDE | ESP |
| `icon:mapa` | OVERTURE PARA MUNDO | `geo.overture` | bbox → WORLD_STATE | GeoParquet + DuckDB Spatial | OUTSIDE | ESP |
| `icon:malha3d` | CESIUM E 3D TILES | `geo.tiles3d` | tiles → TILES_3D/SCENE | Cesium Native / CesiumJS | OUTSIDE | ESP |
| `icon:mapa` | MAPA MAPLIBRE | `geo.maplibre` | camadas → preview de mapa | MapLibre GL JS | OUTSIDE | ESP |
| `icon:escopo` | MAPA ANALÍTICO KEPLER | `geo.kepler` | tabela → mapa | kepler.gl | OUTSIDE | ESP |
| `icon:malha3d` | CAMADAS 3D DECK.GL | `geo.deck` | GIS_LAYER → preview | deck.gl | OUTSIDE | ESP |
| `icon:natureza` | DEM PARA TERRENO | `geo.dem` | RASTER_GEO → MESH | GDAL + PROJ | OUTSIDE | ESP |
| `icon:natureza` | TERRENO REAL ALTA DEFINIÇÃO | `geo.terrain_hq` | DEM + imagery → SCENE | terreno multi-resolução | WORKFLOW | ESP |
| `icon:arquitetura` | EDIFÍCIOS DO MAPA | `geo.buildings` | GIS → SCENE | footprints OSM/Overture + alturas | OUTSIDE | ESP |
| `icon:mapa` | RUAS DO MAPA | `geo.roads` | GIS → SCENE | geometria de rede | OUTSIDE | ESP |
| `icon:natureza` | HIDROGRAFIA | `geo.water` | GIS → SCENE | OSM/Overture + procedural | OUTSIDE | ESP |
| `icon:natureza` | VEGETAÇÃO DO MAPA | `geo.vegetation` | GIS → SCENE | landcover + scatter procedural | OUTSIDE | ESP |
| `icon:nuvem_pontos` | POINT CLOUD E LIDAR | `geo.lidar` | LAS/LAZ → POINT_CLOUD | PDAL | OUTSIDE | ESP |
| `icon:imagem` | ORTOFOTO | `geo.ortho` | raster → RASTER_GEO | GDAL | OUTSIDE | ESP |
| `icon:mapa` | REPROJETAR CRS | `geo.reproject` | Geo + CRS → Geo | PROJ / GDAL | OUTSIDE | ESP |
| `icon:fluxo` | CRUZAR GEO, CAD E BIM | `geo.crosslink` | GIS + CAD + BIM → WORLD_STATE | IDs espaciais canônicos | OUTSIDE | ESP |
| `icon:mapa` | METADATA DE GEOLOCALIZAÇÃO | `geo.metadata` | asset → GEO_METADATA | EXIF / XMP + resolver | OUTSIDE | ESP |
| `icon:luz` | SOL REAL POR DATA E HORA | `geo.sun` | GEO + tempo → LIGHT_RIG | efemérides solares | OUTSIDE | ESP |
| `icon:natureza` | CLIMA E WEATHER PROFILE | `geo.weather` | GEO + tempo → JSON | dataset local / adapter | OUTSIDE | ESP |
| `icon:mapa` | MUNDO REAL PARA DIGITAL TWIN | `geo.digital_twin` | multi-fonte → WORLD_STATE | fusão GIS + BIM + 3D | WORKFLOW | ESP |
| `icon:saida` | EXPORTAR 3D TILES | `geo.export_tiles` | SCENE → TILES_3D | toolchain 3D Tiles | OUTSIDE | ESP |
| `icon:saida` | PMTILES E MBTILES | `geo.tilepack` | GIS → ASSET | PMTiles / GDAL | OUTSIDE | ESP |
| `icon:licenca` | CATÁLOGO DE FONTES GEO | `geo.source_registry` | consulta → ASSET_SET | registro de providers governado | OUTSIDE | ESP |

### 10.16 NATUREZA PROCEDURAL

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:natureza` | ÁRVORE PROCEDURAL | `nature.tree` | params/espécie → MESH | Blender Geometry Nodes / L-system | OUTSIDE | ESP |
| `icon:natureza` | FLORESTA PROCEDURAL | `nature.forest` | terreno + regras → SCENE | scatter + biomas | OUTSIDE | ESP |
| `icon:natureza` | PLANTA PROCEDURAL | `nature.plant` | params → MESH | gerador procedural | OUTSIDE | ESP |
| `icon:natureza` | GRAMA PROCEDURAL | `nature.grass` | terreno → SCENE | geometry nodes + instancing | OUTSIDE | ESP |
| `icon:natureza` | MATO E PASTO | `nature.field` | terreno + bioma → SCENE | scatter + vento | OUTSIDE | ESP |
| `icon:natureza` | ÁGUA REALISTA | `nature.water` | geometria + clima → PBR/SCENE | shader + simulação | OUTSIDE | ESP |
| `icon:natureza` | MONTANHAS PROCEDURAIS | `nature.mountain` | params/DEM → MESH | algoritmos de terreno + erosão | OUTSIDE | ESP |
| `icon:natureza` | ROCHAS PROCEDURAIS | `nature.rocks` | params → MESH/PBR | geometria procedural | OUTSIDE | ESP |
| `icon:luz` | CÉU E HDRI | `nature.sky` | tempo/clima → HDRI/LIGHT_RIG | céu procedural + biblioteca HDRI | OUTSIDE | ESP |
| `icon:movimento` | VENTO PROCEDURAL | `nature.wind` | params → estado | física + animação | OUTSIDE | ESP |
| `icon:natureza` | NEVE E CHUVA | `nature.weather_fx` | clima → SCENE | partículas + materiais | OUTSIDE | ESP |
| `icon:natureza` | FOGO E FUMAÇA | `nature.pyro` | params → SCENE | Blender + OpenVDB | OUTSIDE | ESP |

### 10.17 UI E CÓDIGO

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:codigo` | TELA PARA UI | `code.screenshot_ui` | IMAGE → projeto de código | VLM + padrão screenshot-to-code | OUTSIDE | ESP |
| `icon:cor` | REFERÊNCIAS PARA DESIGN SYSTEM | `code.design_system` | IMAGE_SET → tokens + componentes | VLM + extração visual | OUTSIDE | ESP |
| `icon:segmentacao` | DETECTAR COMPONENTES | `code.component_detect` | IMAGE → JSON | segmentação + layout + VLM | OUTSIDE | ESP |
| `icon:cor` | EXTRAIR DESIGN TOKENS | `code.tokens` | IMAGE_SET → JSON | visão + regras | OUTSIDE | ESP |
| `icon:codigo` | UI PARA REACT | `code.react` | spec → código | Qwen3-Coder / agente de código | OUTSIDE | ESP |
| `icon:codigo` | UI PARA VUE | `code.vue` | spec → código | agente de código | OUTSIDE | ESP |
| `icon:codigo` | UI PARA SVELTE | `code.svelte` | spec → código | agente de código | OUTSIDE | ESP |
| `icon:codigo` | UI PARA GODOT | `code.godot_ui` | spec → cena + código | agente de código | OUTSIDE | ESP |
| `icon:malha3d` | UI PARA BABYLON 3D | `code.babylon` | spec → código | agente de código | OUTSIDE | ESP |
| `icon:agente` | AGENTE PROGRAMADOR | `code.agent` | tarefa + repo → patch | OpenHands / Aider / Kimi Code | OUTSIDE | ESP |
| `icon:conhecimento` | LER REPOSITÓRIO | `code.repo_understand` | repo → KNOWLEDGE_PACK | parser + LLM de código | OUTSIDE | ESP |
| `icon:evidencia` | TESTAR CÓDIGO | `code.test` | repo → EVIDENCE | runners nativos | OUTSIDE | ESP |
| `icon:imagem` | COMPARAR TELA PIXEL | `code.visual_regression` | browser + alvo → EVIDENCE | Playwright + métricas de screenshot | OUTSIDE | ESP |
| `icon:progresso` | CORRIGIR UI AUTOMÁTICO | `code.ui_fix` | evidência → patch | laço de agente limitado | OUTSIDE | ESP |
| `icon:remoto` | AGENTE DE INTERFACE | `code.gui_agent` | tela + tarefa → ações | UI-TARS | OUTSIDE | ESP |
| `icon:fluxo` | FERRAMENTA MCP | `code.mcp_tool` | schema → TOOL | adapter MCP | OUTSIDE | ESP |
| `icon:processador` | TERMINAL CONTROLADO | `code.shell` | comando → saída | sandbox runner | OUTSIDE | ESP |
| `icon:remoto` | BROWSER CONTROLADO | `code.browser` | tarefa → evidência | Playwright | OUTSIDE | ESP |

### 10.18 CONHECIMENTO

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:conhecimento` | COSMETA REFINAR CONHECIMENTO | `cosmeta.refine` | fontes → KNOWLEDGE_PACK | pipeline COSMETA | OUTSIDE | ESP |
| `icon:entrada` | INGERIR CONHECIMENTO | `knowledge.ingest` | ASSET_SET → chunks | parsers | OUTSIDE | ESP |
| `icon:mascara` | LIMPAR CONHECIMENTO | `knowledge.clean` | chunks → chunks | determinístico + LLM opcional | OUTSIDE | ESP |
| `icon:lote` | CHUNK SEMÂNTICO | `knowledge.chunk` | documentos → chunks | parser ciente de estrutura | OUTSIDE | ESP |
| `icon:memoria` | VETORIZAR | `knowledge.embed` | chunks → EMBEDDING | slot de embeddings | OUTSIDE | ESP |
| `icon:conhecimento` | BUSCA VETORIAL | `knowledge.vector_search` | consulta → chunks | índice vetorial local | OUTSIDE | ESP |
| `icon:texto` | BUSCA TEXTO | `knowledge.fulltext` | consulta → chunks | SQLite FTS / Tantivy | OUTSIDE | ESP |
| `icon:fluxo` | CRIAR GRAFO DE CONHECIMENTO | `knowledge.graph` | chunks → grafo | Kuzu + extrator | OUTSIDE | ESP |
| `icon:fluxo` | GRAPH RAG | `knowledge.graph_rag` | consulta + grafo → contexto | Kuzu + RAG híbrido | OUTSIDE | ESP |
| `icon:evidencia` | REORDENAR RESULTADOS | `knowledge.rerank` | consulta + hits → hits | slot de reranker | OUTSIDE | ESP |
| `icon:texto` | EXTRAIR FATOS | `knowledge.claims` | fontes → afirmações | extração estruturada | OUTSIDE | ESP |
| `icon:atencao` | BUSCAR CONTRADIÇÕES | `knowledge.contradict` | afirmações → EVIDENCE | recuperação + verificador | OUTSIDE | ESP |
| `icon:evidencia` | VALIDAR FONTE | `knowledge.source_verify` | fonte → EVIDENCE | política + hash + proveniência | OUTSIDE | ESP |
| `icon:agente` | GERAR HIPÓTESES | `knowledge.hypothesis` | contexto verificado → afirmações | slot de raciocínio | OUTSIDE | ESP |
| `icon:evidencia` | TESTAR HIPÓTESE | `knowledge.test_hypothesis` | afirmação + ferramentas → EVIDENCE | grafo de verificadores | OUTSIDE | ESP |
| `icon:concluido` | APROVAR CONHECIMENTO | `knowledge.promote` | candidato + aprovação → conhecimento | trusted core | OUTSIDE | ESP |
| `icon:erro` | REJEITAR CONHECIMENTO | `knowledge.reject` | candidato → auditoria | trusted core | OUTSIDE | ESP |
| `icon:pendente` | VERSÃO TEMPORAL | `knowledge.temporal` | item + tempo → item | store temporal | OUTSIDE | ESP |
| `icon:laco` | SUBSTITUIR SEM APAGAR HISTÓRIA | `knowledge.supersede` | antigo + novo → novo | ledger de proveniência | OUTSIDE | ESP |
| `icon:laco` | SÍNTESE OFFLINE LIMITADA | `cosmeta.synthesis_job` | pacote aprovado → candidatos | grafo de agentes limitado | OUTSIDE | ESP |
| `icon:memoria` | MEMÓRIA DE PROJETO | `memory.project` | eventos → memória | memória com escopo | OUTSIDE | ESP |
| `icon:memoria` | MEMÓRIA PROCEDURAL | `memory.procedural` | workflow verificado → memória | registro de workflows | OUTSIDE | ESP |
| `icon:escopo` | MÉTRICAS DO PRÓPRIO SISTEMA | `memory.self_metrics` | execuções → métricas | telemetria | OUTSIDE | ESP |
| `icon:saida` | EMPACOTAR CONHECIMENTO | `knowledge.pack` | itens verificados → KNOWLEDGE_PACK | core | OUTSIDE | ESP |
| `icon:saida` | EXPORTAR DATASET CURADO | `knowledge.dataset` | itens verificados → dataset | dataset builder | OUTSIDE | ESP |

### 10.19 TREINAMENTO

| Ícone | Nome no front | ID técnico | Entrada → Saída | Motor técnico | Comfy | Est. |
| --- | --- | --- | --- | --- | --- | --- |
| `icon:treinamento` | TREINAR LoRA | `train.lora` | dataset + modelo → adapter | PEFT / LLaMA-Factory / Unsloth | OUTSIDE | ESP |
| `icon:treinamento` | TREINAR QLoRA | `train.qlora` | dataset + modelo → adapter | PEFT / Unsloth | OUTSIDE | ESP |
| `icon:treinamento` | SFT SUPERVISIONADO | `train.sft` | dataset + modelo → modelo/adapter | TRL / LLaMA-Factory | OUTSIDE | ESP |
| `icon:treinamento` | DPO PREFERÊNCIAS | `train.dpo` | preferências → modelo/adapter | TRL / LLaMA-Factory | OUTSIDE | ESP |
| `icon:treinamento` | REWARD MODEL | `train.reward` | dataset → modelo | TRL | OUTSIDE | ESP |
| `icon:evidencia` | AVALIAR CHALLENGER | `train.eval` | modelo + suíte → EVIDENCE | harness de avaliação | OUTSIDE | ESP |
| `icon:atencao` | RED TEAM | `train.redteam` | modelo + suíte → EVIDENCE | avaliação de segurança | OUTSIDE | ESP |
| `icon:treinamento` | DESTILAR ESPECIALISTA | `train.distill` | teacher + dataset → modelo | destilação offline | OUTSIDE | ESP |
| `icon:imagem` | TREINAR LoRA DE IMAGEM | `train.image_lora` | dataset → adapter | DiffSynth / trainers do Comfy | ADAPTER | ESP |
| `icon:video` | TREINAR LoRA DE VÍDEO | `train.video_lora` | dataset → adapter | DiffSynth / musubi | OUTSIDE | ESP |
| `icon:audio` | TREINAR VOZ | `train.voice` | dataset consentido → adapter | específico do modelo | OUTSIDE | ESP |
| `icon:conhecimento` | CURAR DATASET | `train.curate` | fontes → dataset | COSMETA + aprovação humana | OUTSIDE | ESP |
| `icon:mascara` | DEDUPLICAR DATASET | `train.dedupe` | dataset → dataset | hash + embedding | OUTSIDE | ESP |
| `icon:texto` | ROTULAR DATASET | `train.label` | assets → dataset | VLM + validação humana | OUTSIDE | ESP |
| `icon:concluido` | CHAMPION CONTRA CHALLENGER | `train.promote` | modelos + avaliação → MODEL_REF | portão de governança | OUTSIDE | ESP |

### 10.20 MODELOS E INFERÊNCIA

| Ícone | Nome no front | ID técnico | Motor técnico | Est. |
| --- | --- | --- | --- | --- |
| `icon:local` | LLM LOCAL UNIVERSAL | `infer.llm.local` | llama.cpp | PAR |
| `icon:processador` | LLM SERVER RÁPIDO | `infer.llm.server` | vLLM | ESP |
| `icon:processador` | MULTIMODAL SERVER RÁPIDO | `infer.mm.server` | SGLang | ESP |
| `icon:remoto` | OMNI SERVER | `infer.omni` | vLLM-Omni | ESP |
| `icon:agente` | PENSAMENTO LOCAL LEVE | `infer.reason.light` | slot: LiquidAI LFM2.5-8B-A1B | ESP |
| `icon:imagem` | VISÃO E RACIOCÍNIO | `infer.vlm` | slot: Qwen3-VL / Gemma / Kimi | ESP |
| `icon:codigo` | CÓDIGO PROFUNDO | `infer.code` | slot: Qwen3-Coder / Kimi Code | ESP |
| `icon:roteador` | RACIOCÍNIO FRONTIER SERVER | `infer.frontier` | slot: Kimi K3 distribuído | ESP |
| `icon:local` | MODELO EDGE | `infer.edge` | Liquid / Gemma pequenos | ESP |
| `icon:memoria` | QUANTIZAR GGUF | `infer.quant.gguf` | ferramentas do llama.cpp | ESP |
| `icon:memoria` | DIFFUSION 4-BIT | `infer.quant.diffusion` | Nunchaku / SVDQuant | ESP |
| `icon:processador` | ONNX RUNTIME | `infer.onnx` | ONNX Runtime | ESP |
| `icon:processador` | TENSORRT | `infer.tensorrt` | TensorRT / TensorRT-LLM | ESP |
| `icon:processador` | APPLE MLX | `infer.mlx` | MLX | ESP |
| `icon:processador` | INTEL OPENVINO | `infer.openvino` | OpenVINO | ESP |
| `icon:processador` | AMD ROCm | `infer.rocm` | ROCm | ESP |
| `icon:memoria` | CARREGAR MODELO | `infer.load` | agendador | PAR |
| `icon:memoria` | DESCARREGAR MODELO | `infer.unload` | agendador | PAR |
| `icon:memoria` | FIXAR MODELO NA VRAM | `infer.pin` | agendador | ESP |
| `icon:memoria` | OFFLOAD PARA CPU | `infer.offload` | específico do runtime | ESP |
| `icon:lote` | INFERÊNCIA EM TILES | `infer.tile` | workers de imagem e vídeo | IMP |
| `icon:processador` | ATTENTION OTIMIZADA | `infer.attention` | Flash / Sage / xFormers | ESP |
| `icon:cache` | CACHE DE CONTEXTO | `infer.kv_cache` | runtime | ESP |
| `icon:cache` | CACHE DE DIFFUSION | `infer.diffusion_cache` | TeaCache e similares | ESP |

### 10.21 ROTEAMENTO E SISTEMA

| Ícone | Nome no front | ID técnico | Motor técnico | Est. |
| --- | --- | --- | --- | --- |
| `icon:roteador` | MEGA ROTEADOR INTELIGENTE | `system.router` | roteador de capacidade em Rust | PAR |
| `icon:processador` | ANTI-GARGALO GPU | `system.gpu_scheduler` | agendador Rust | ESP |
| `icon:escopo` | BALANCEAR QUALIDADE E VELOCIDADE | `system.quality_router` | roteador multiobjetivo | ESP |
| `icon:escopo` | ORÇAR EXECUÇÃO | `system.budget` | estimador de custo e recurso | ESP |
| `icon:escopo` | PROFILER | `system.profile` | telemetria | PAR |
| `icon:atencao` | FALLBACK AUTOMÁTICO | `system.fallback` | roteador | ESP |
| `icon:lote` | FILA DE JOBS | `system.queue` | fila resumível | PAR |
| `icon:pendente` | CHECKPOINT | `system.checkpoint` | runtime de jobs | ESP |
| `icon:progresso` | RETOMAR JOB | `system.resume` | runtime de jobs | ESP |
| `icon:erro` | CANCELAR JOB | `system.cancel` | runtime de jobs | PAR |
| `icon:licenca` | POLÍTICA DE PROVIDER | `system.provider_policy` | trusted core | ESP |
| `icon:licenca` | REGISTRO DE LICENÇAS | `system.license` | SBOM + registro de modelos | PAR |
| `icon:evidencia` | PROVENIÊNCIA | `system.provenance` | ledger de evidência | ESP |
| `icon:concluido` | HEALTH CHECK | `system.health` | registro de saúde | IMP |
| `icon:escopo` | BENCHMARK AUTOMÁTICO | `system.benchmark` | harness de benchmark | PAR |
| `icon:entrada` | IMPORTAR WORKFLOW COMFY | `system.comfy_import` | compilador de adapter | ESP |
| `icon:saida` | EXPORTAR WORKFLOW COMFY | `system.comfy_export` | compilador de adapter | ESP |
| `icon:fluxo` | SUBGRAFO | `system.subgraph` | core | ESP |
| `icon:lote` | MACRO PRESET | `system.macro` | core | ESP |
| `icon:cache` | VERSIONAR WORKFLOW | `system.version` | git + hash de conteúdo | PAR |

### 10.22 EXPORTAÇÃO

| Ícone | Nome no front | ID técnico | Motor técnico | Est. |
| --- | --- | --- | --- | --- |
| `icon:imagem` | EXPORTAR IMAGEM | `export.image` | OIIO: PNG, JPEG, TIFF, EXR | IMP |
| `icon:video` | EXPORTAR VÍDEO | `media.export` | FFmpeg | IMP |
| `icon:video` | EXPORTAR PRORES, DNx OU AV1 | `export.mezzanine` | FFmpeg conforme encoder disponível | ESP |
| `icon:malha3d` | EXPORTAR GLB E GLTF | `export.gltf` | Blender / glTF | PAR |
| `icon:malha3d` | EXPORTAR USD | `export.usd` | OpenUSD / Blender | ESP |
| `icon:arquitetura` | EXPORTAR IFC | `export.ifc` | IfcOpenShell | ESP |
| `icon:planta` | EXPORTAR DXF | `export.dxf` | LibreDWG / kernel CAD | ESP |
| `icon:processador` | EXPORTAR GAME READY | `export.game` | adapters Godot / Bevy / O3DE | ESP |
| `icon:remoto` | EXPORTAR WEB 3D | `export.web3d` | glTF + Babylon / Three | ESP |
| `icon:mapa` | EXPORTAR 3D TILES | `export.3dtiles` | pipeline 3D Tiles | ESP |
| `icon:saida` | EMPACOTAR PROJETO | `export.project` | manifesto + hashes | PAR |
| `icon:evidencia` | RELATÓRIO DE PROVENIÊNCIA | `export.provenance` | trusted core | ESP |
| `icon:conhecimento` | EXPORTAR KNOWLEDGE PACK | `export.knowledge` | core | ESP |

> **Nota de licença.** SUPIR, MHR / SAM 3D, SMPL-X, modelos Stability, checkpoints de reconhecimento facial e vários pesos de pesquisa precisam passar por `GATE-LICENSE`. Código público não implica licença comercial irrestrita.

---
## 11. REGISTRO DE MODELOS — NOMES ORIGINAIS SÓ EM GOVERNANÇA

O front trabalha com capability slots. O registro técnico conhece os projetos originais, com revisão exata e hash.

| Nome no front | Projeto original | Slot | Observação técnica | Runtime |
| --- | --- | --- | --- | --- |
| IMAGEM ULTRA RÁPIDA | Black Forest Labs FLUX.2 [klein] | `image.generate.fast` | muito rápido; confirmar variante e licença | ComfyUI / Diffusers |
| IMAGEM QUALITY PRO | Qwen-Image / Qwen-Image-2512 | `image.generate.quality` | texto, layout e multimodal fortes | ComfyUI / Diffusers |
| EDITAR IMAGEM PRO | Qwen-Image-Edit-2509 | `image.edit.multi_ref` | multi-imagem e edição precisa | ComfyUI / Diffusers |
| CAMADAS EDITÁVEIS | Qwen-Image-Layered | `image.layers` | camadas RGBA independentes | Diffusers / adapter Comfy |
| IMAGEM 2K QUALITY | HunyuanImage-2.1 | `image.generate.hq` | classe 17B, T2I em 2K | ComfyUI / Diffusers |
| IMAGEM LEVE 6B | família Z-Image | `image.generate.efficient` | família eficiente 6B; expor só release validada | Diffusers / ComfyUI |
| OMNI VISUAL 3B | ByteDance Lance | `multimodal.image_video` | 3B unificado: compreensão, geração e edição | custom |
| FILME RÁPIDO ULTRA 8B | HunyuanVideo-1.5 | `video.generate.fast.consumer` | classe 8.3B, viável em GPU de consumidor | ComfyUI / Diffusers |
| FILME 4K CINEMA PRO | LTX-2 / LTX-2.3 validado | `video.generate.4k` | alta resolução; áudio sincronizado em variantes | ComfyUI / runtime LTX |
| FILME QUALITY | Wan2.2 | `video.generate.quality` | T2V e I2V, variantes MoE | ComfyUI / Diffusers |
| FILME LONGO E EXTENSÃO | SkyReels V2 / V3 | `video.long`, `video.extend` | long-form, extensão, referência | custom / adapter Comfy |
| MEMÓRIA DE VÍDEO EFICIENTE | FramePack | `video.context.optimization` | técnica de geração progressiva | custom |
| RESTAURAR VÍDEO PRO | SeedVR2 | `video.restore` | restauração de vídeo em um passo | custom / Comfy |
| INTERPOLAÇÃO | Practical-RIFE / FILM | `video.interpolate` | interpolação de frames | custom (NCNN Vulkan já integrado) |
| 3D QUALITY PRO | TRELLIS.2 | `3d.generate.hq` | geração 3D classe 4B | custom / adapter Comfy |
| 3D PBR PRO | Hunyuan3D-2.1 | `3d.generate.pbr` | geometria e ecossistema PBR | custom / Comfy |
| 3D CONTROLADO | Hunyuan3D-Omni | `3d.generate.controlled` | condições por ponto, voxel, esqueleto, bbox | custom |
| 3D PIXEL-ALIGNED | Pixal3D | `3d.generate.hq.experimental` | SIGGRAPH 2026; licença exige gate | custom |
| 3D OBJETO REAL | SAM 3D Objects | `3d.reconstruct.object` | forma, geometria, textura, layout | custom |
| 3D RÁPIDO | TripoSR | `3d.generate.fast` | feed-forward de imagem única | custom |
| 3D SHAPE | TripoSG | `3d.shape` | síntese de forma de alta fidelidade | custom |
| 3D GAUSSIAN | TripoSplat | `3d.gaussian.single_image` | imagem única para 3D Gaussian | Comfy / custom |
| 3D VELOZ COM UV | Stable Fast 3D | `3d.generate.fast_uv` | UV, material, delighting; licença Stability Community | custom |
| 3D OCLUSO | SPAR3D | `3d.generate.occluded` | reconstrói o lado não visível com point cloud | custom |
| 3D APACHE | InstantMesh | `3d.generate.permissive` | imagem única para malha, Apache 2.0 | custom |
| 3D MULTIVIEW | Wonder3D | `3d.multiview_synthesis` | RGB e normais multi-vista consistentes | custom |
| CORPO HUMANO 3D | SAM 3D Body + Momentum Human Rig (MHR) | `human.body_fit` | HMR de corpo inteiro a partir de uma imagem | custom / wrapper Comfy |
| MOCAP HUMANO | GVHMR | `motion.human.video` | movimento humano ancorado no mundo | custom / wrapper Comfy |
| CORPO PARAMÉTRICO CLÁSSICO | SMPL-X | `human.body_fit.legacy` | corpo, mãos, rosto, expressão; termos próprios | outside |
| AJUSTE DE CORPO POR IMAGEM | SMPLer-X / SMPLest-X | `human.body_fit.image` | imagem para parâmetros SMPL-X | outside |
| HUMANO VESTIDO | ECON / SiTH / CharacterGen / StdGEN | `human.clothed_reconstruct` | digitalização de humano vestido | outside |
| AVATAR NEURAL | GaussianAvatar / GaussianAvatars / HumanSplat | `human.neural_avatar` | avatar 3D animável a partir de vídeo | outside |
| ANIMAL PARAMÉTRICO | SMAL / SMALify | `animal.body_fit` | quadrúpede paramétrico, pesquisa | outside |
| ANIMAL ANIMÁVEL | AnimalAvatar / 3DAnimals | `animal.avatar` | vídeo casual para animal animável | outside |
| GEOMETRIA DE FOTOS | VGGT | `vision.geometry` | câmera, depth, point maps, tracks | outside |
| GEOMETRIA UNIFICADA | MapAnything | `vision.geometry.unified` | interface unificada sobre VGGT, DUSt3R, MASt3R, MUSt3R | outside |
| PAR DE FOTOS PARA 3D | DUSt3R / MASt3R / MUSt3R | `vision.geometry.pairwise` | geometria direta de pares e múltiplas imagens | outside |
| FOTOGRAMETRIA CLÁSSICA | COLMAP | `3d.sfm` | SfM e MVS, infraestrutura essencial | outside |
| CAMPO NEURAL | Nerfstudio | `3d.nerf` | framework de NeRF e reconstrução | outside |
| SPLATTING RÁPIDO | gsplat | `3d.gaussian.backend` | backend CUDA para Gaussian Splatting | outside |
| MUNDO GERADO | HunyuanWorld / HunyuanWorld-Voyager | `world.generate` | ambientes 3D navegáveis | outside |
| MOTOR DE MUNDO MODULAR | EmbodiedGen | `world.engine` | image/text→3D, texturização, objetos articulados, layout | outside |
| PROFUNDIDADE | Depth Anything V2 / Video Depth Anything | `vision.depth` | profundidade estável, inclusive temporal | custom |
| NORMAIS | Marigold / DSINE / MoGe / Metric3D | `vision.normals` | normais e geometria métrica | custom |
| POSE | DWPose / OpenPose / DensePose | `vision.pose2d` | keypoints de corpo, mãos e rosto | custom |
| SEGMENTAÇÃO | SAM 2 | `vision.segment` | segmentação em imagem e vídeo | custom |
| DETECÇÃO ABERTA | Grounding DINO / Grounded SAM | `vision.ground` | detecção condicionada por linguagem | custom |
| FLUXO ÓPTICO | RAFT | `vision.flow` | fluxo para tracking e consistência | custom |
| IDENTIDADE FACIAL | PuLID | `image.identity.pulid` | preservação de ID em FLUX e SDXL | custom |
| IDENTIDADE POR FOTO | InstantID | `image.identity.instantid` | embedding facial para nova pose e cena | custom |
| IDENTIDADE MULTI-FOTO | PhotoMaker V2 | `image.identity.photomaker` | várias fotos da mesma pessoa | custom |
| REFERÊNCIA UNIFICADA | DreamO / USO / IC-Custom | `image.reference.unified` | sujeito, ID, estilo, try-on, customização | custom |
| CONDICIONAMENTO POR REFERÊNCIA | IP-Adapter | `image.reference.ipadapter` | roupa, cenário, estilo, personagem, objeto | custom |
| CONTROLE ESTRUTURAL | ControlNet / T2I-Adapter / ControlLoRA | `image.control` | mapas viram restrição estrutural | custom |
| RELIGHT | IC-Light / LightCtrl | `vfx.relight` | relighting de imagem e vídeo | custom |
| RESTAURO DE IMAGEM | SUPIR | `restore.image` | recuperação de detalhe em alta resolução | custom |
| RESTAURO DE ROSTO | CodeFormer / GFPGAN | `restore.face` | restauração facial e colorização | custom |
| UPSCALE CLÁSSICO | Real-ESRGAN | `upscale.image` | rápido, já integrado via NCNN Vulkan | custom |
| COLORIZAÇÃO | DDColor | `image.colorize` | colorização de material P&B | custom |
| RECONHECIMENTO FACIAL | InsightFace / SCRFD / ArcFace / AdaFace / CVLFace / DeepFace | `biometrics.face` | detecção, alinhamento, embeddings, reidentificação | outside |
| VOZ ZERO-SHOT | F5-TTS | `audio.tts.zeroshot` | código MIT; pesos com termos próprios | outside |
| VOZ COM TEMPO PRECISO | IndexTTS2 | `audio.tts.timed` | controle temporal preciso para dublagem | outside |
| VOZ MULTILÍNGUE | CosyVoice | `audio.tts.multilingual` | multilíngue e zero-shot | outside |
| VOZ RESEMBLE | Chatterbox | `audio.tts.chatterbox` | TTS multilíngue com boa preservação de locutor | outside |
| CLONE INSTANTÂNEO | OpenVoice V2 | `audio.tts.openvoice` | MIT, clonagem instantânea | outside |
| VOZ COM POUCOS DADOS | GPT-SoVITS | `audio.tts.fewshot` | few-shot TTS | outside |
| CONVERSÃO DE VOZ | RVC | `audio.voice_convert` | conversão de locutor | outside |
| ÁUDIO LOCAL LEVE | LFM2-Audio-1.5B | `audio.speech2speech` | fala para fala de baixa latência | outside |
| TRANSCRIÇÃO | Qwen3-ASR / faster-whisper / Whisper / SenseVoice | `audio.asr` | transcrição, tradução, timestamps, emoção | outside |
| MÚSICA | ACE-Step | `audio.music` | música completa, letra, stems, remix | outside |
| ÁUDIO GENERATIVO | AudioCraft (MusicGen, AudioGen, EnCodec, MAGNeT, JASCO) | `audio.generate` | música e efeitos | outside |
| MÚSICA COMPLETA | YuE | `audio.music.fullsong` | geração de música completa | outside |
| TREINO DE ÁUDIO | Stable Audio Tools | `audio.train` | treino e inferência de áudio generativo | outside |
| FOLEY DE VÍDEO | HunyuanVideo-Foley | `audio.foley` | vídeo para efeitos sonoros sincronizados | outside |
| SEPARAÇÃO | Demucs / MDX / UVR | `audio.stems` | voz, bateria, baixo, acompanhamento | outside |
| LLM LOCAL UNIVERSAL | llama.cpp | `runtime.llm.local` | GGUF, CPU e GPU, hardware amplo | serviço |
| LLM SERVER | vLLM | `runtime.llm.server` | serving de alto throughput | serviço |
| MULTIMODAL SERVER | SGLang | `runtime.multimodal.server` | baixa latência, cargas estruturadas de agente | serviço |
| OMNI SERVER | vLLM-Omni | `runtime.omni.server` | TTS, fala, difusão, imagem, vídeo, política de robô | serviço |
| PENSAMENTO LOCAL LEVE | LiquidAI LFM2.5-8B-A1B | `reasoning.edge.moe` | 8.3B totais, ~1.5B ativos por token, 128K contexto | llama.cpp / vLLM / SGLang / ONNX |
| EDGE ULTRA LEVE | família LFM2.5 pequena (230M, 350M, 2.6B) | `router.edge` | classificar, escolher tool, tarefas pequenas | local |
| VISÃO E RACIOCÍNIO | Qwen3-VL | `vision.reason` | visão, vídeo, raciocínio, interação de agente | vLLM / SGLang |
| CÓDIGO PROFUNDO | família Qwen3-Coder / Qwen Code | `code.reason` | codificação agêntica | vLLM / SGLang / llama.cpp |
| RACIOCÍNIO FRONTIER SERVER | Kimi K3 | `reason.frontier` | open-weight, multimodal, 2.8T, contexto 1M; servidor/distribuído | vLLM / SGLang |
| CÓDIGO FRONTIER | Kimi Code | `code.frontier` | agente de código long-horizon | serviço |
| GEMMA LOCAL | família Gemma (release validada) | `reason.local` | família open-weight; fixar release exata | llama.cpp / JAX |
| DIFFUSION 4-BIT | Nunchaku / SVDQuant | `runtime.diffusion.quant` | inferência 4-bit de difusão | Comfy / plugin |
| TREINO LLM | LLaMA-Factory | `train.llm` | SFT, DPO, QLoRA | serviço de treino |
| TREINO EFICIENTE | Unsloth | `train.local` | texto, áudio, embeddings, visão | serviço de treino |
| PÓS-TREINO | Hugging Face TRL + PEFT | `train.post` | SFT, DPO, GRPO, adapters PEFT | serviço de treino |
| MOTOR DE DIFUSÃO | Hugging Face Diffusers | `runtime.diffusion` | blocos modulares de inferência e treino | Python |
| CHALLENGER DE DIFUSÃO | DiffSynth-Studio | `runtime.diffusion.challenger` | treino e inferência; recursos de baixa VRAM | Python |
| MEDIA GRAPH | ComfyUI | `runtime.media_graph` | backend canônico reutilizável de execução de mídia | serviço |
| GERENTE OPCIONAL | SwarmUI | `runtime.media.manager` | gerente de backends opcional; não é o grafo canônico | serviço |
| NODAL CRIATIVO OPCIONAL | InvokeAI | `runtime.creative` | motor nodal alternativo, challenger | serviço |
| COMPOSITOR NODAL | Natron | `vfx.composite` | compositor node-graph, OpenFX, EXR multi-camada | outside |
| DCC UNIVERSAL | Blender | `dcc.universal` | modelagem, rig, animação, simulação, Cycles, compositor | outside |
| CAD KERNEL | OpenCascade / CadQuery | `cad.kernel` | B-Rep e paramétrico | outside |
| BIM | IfcOpenShell / Bonsai | `bim.authoring` | leitura, autoria e validação IFC | outside |
| DWG | LibreDWG | `cad.dwg` | leitura e escrita DWG quando compatível | outside |
| GIS CORE | GDAL, PROJ, PDAL, DuckDB Spatial, PostGIS | `gis.core` | vetorial, raster, nuvem de pontos, CRS | outside |
| MAPA WEB | MapLibre GL JS, deck.gl, kepler.gl | `gis.web` | visualização de mapas e camadas 3D | outside |
| GLOBO 3D | CesiumJS / Cesium Native / 3D Tiles | `gis.globe` | terreno e tiles 3D em escala planetária | outside |
| COR INDUSTRIAL | OpenColorIO, OpenImageIO, OpenEXR | `color.core` | gerenciamento de cor e imagem de produção | outside |
| MATERIAL INDUSTRIAL | MaterialX, OpenPBR | `material.core` | intercâmbio aberto de materiais e lookdev | outside |
| VOLUME | OpenVDB | `volume.core` | volumes esparsos para pyro e nuvens | outside |
| TIMELINE | OpenTimelineIO | `edit.timeline` | intercâmbio de edição | outside |
| ENGINE GAME | Godot, O3DE, Bevy | `game.engine` | runtime de jogo e simulação | outside |
| ENGINE WEB 3D | Babylon.js, Three.js, PlayCanvas | `web3d.engine` | 3D em navegador com WebGPU e WebGL | outside |
| GRAFO EMBUTIDO | Kuzu | `knowledge.graph.db` | property graph embutido para GraphRAG | outside |
| AGENTE DE CÓDIGO | OpenHands, Aider, Cline, Continue, SWE-agent | `code.agent` | modificar repositório, shell, testes | outside |
| AGENTE DE GUI | UI-TARS / UI-TARS Desktop | `gui.agent` | agente multimodal que enxerga e opera interfaces | outside |
| TELA PARA CÓDIGO | screenshot-to-code, Design2Code | `code.screenshot` | screenshot para HTML, Tailwind, React, Vue | outside |
| ORQUESTRAÇÃO DE AGENTES | LangGraph, Flowise, LangChain, LlamaIndex, Haystack, AutoGen, CrewAI, smolagents, PydanticAI, MCP | `agent.orchestration` | grafos de estado, tools, aprovação humana | outside |

---

## 12. COMFYUI — REUSAR SEM FICAR PRESO

```
COSMETA WorkflowIR
       │
       ├── compila → ComfyGraphAdapter ──→ ComfyUI HTTP 127.0.0.1:8188
       ├── compila → DiffSynthAdapter
       ├── compila → vLLM-Omni Adapter
       ├── compila → BlenderJobAdapter
       ├── compila → FFmpegJobAdapter
       ├── compila → CadBimJobAdapter
       └── compila → GisJobAdapter
```

### 12.1 Regras de vendoragem `[IMPLEMENTADO como política]`

Se o Comfy já tem nó validado, reusar. Não copiar código só para trocar o nome visível. Criar adapter de contrato. Pin de commit ou release. Hash do pacote. Teste de I/O. Teste de workflow mínimo. Licença registrada. Sandbox para custom node. Allowlist por projeto. Probe de saúde da capacidade. Fallback para segundo backend quando existir.

O ComfyUI é **GPL-3.0** e por isso **não é redistribuído** no pacote. Ele é instalado na máquina do usuário por script a partir de commit pinado, e a conversa é apenas HTTP local.

```powershell
# scripts/install-comfy.ps1 — vigente e testado.
# venv próprio, PyTorch com CUDA por fallback de canal, extra_model_paths apontando
# para data/models/comfy. O clone upstream nunca recebe escrita.
$channels = if ($CudaChannel) { @($CudaChannel) } else { @("cu128", "cu126", "cu121") }
foreach ($channel in $channels) {
  & $VenvPython -m pip install torch torchvision torchaudio --index-url "https://download.pytorch.org/whl/$channel"
  if ($LASTEXITCODE -eq 0 -and (Test-TorchCuda)) { $installed = $true; break }
  Write-Warning "$channel instalou mas não enxergou a GPU; tentando o próximo canal."
}
if (-not $installed) { throw "Não foi possível instalar um PyTorch com CUDA funcional." }
```

### 12.2 O que fica fora do Comfy, sempre

Estado de projeto. Autorização. Consentimento. DNA canônico. Registro de assets. Roteamento global. Gestão de GPU. Estado autoritativo de CAD e BIM. Estado autoritativo de GIS. Conhecimento validado. CI e release. Auditoria e evidência.

### 12.3 Famílias de packs a vendorar

Loaders e samplers core; ControlNet; IP-Adapter; PuLID; adaptadores de identidade; SAM e SAM 2; GroundingDINO; depth; normals; pose; Wan; LTX; HunyuanVideo; Hunyuan3D; TRELLIS; wrappers de SAM 3D Body; wrappers de GVHMR; Nunchaku; SeedVR2; RIFE; áudio e TTS; controle avançado; utilitários de vídeo.

**Regra:** 1 champion + 1 challenger por capacidade. Não 30 packs redundantes.

---

## 13. BACKENDS ALTERNATIVOS AO COMFY

Não existe escolha binária "Comfy ou outra coisa". Existem backends especializados sob o mesmo compilador.

| Backend | Papel | Quando é a escolha certa |
| --- | --- | --- |
| **ComfyUI** | media graph | ecossistema enorme de workflows e nós de imagem, vídeo, áudio e parte de 3D |
| **DiffSynth-Studio** | motor de pesquisa e treino de difusão | integração rápida de modelos novos, treino, LoRA, offload e baixa VRAM |
| **vLLM-Omni** | serving multimodal e omni | consolidar TTS, fala, difusão, imagem e vídeo em um servidor |
| **vLLM / SGLang** | server de LLM e VLM | modelos grandes, batching, cache, throughput |
| **llama.cpp** | edge local universal | GGUF e hardware heterogêneo |
| **stable-diffusion.cpp** | imagem local sem Python | já compilado com CUDA arch 8.9 no repositório atual |
| **Blender / FFmpeg / CAD / GIS** | execução determinística | não tente substituir engine madura por difusão |

---

## 14. MEGA ROTEADOR INTELIGENTE ANTI-GARGALO

O roteador decide capacidade. Ele não tem marca favorita.

```
TAREFA
 ↓
classificador de modalidade e intenção
 ↓
capacidades requeridas
 ↓
PORTÕES DUROS
 ├─ precisa ser local?
 ├─ licença resolvida?
 ├─ consentimento presente?
 ├─ formato de arquivo suportado?
 ├─ resolução de saída exigida?
 ├─ duração temporal exigida?
 └─ exige exatidão determinística?
 ↓
candidatos (modelos e engines)
 ↓
ENCAIXE DE HARDWARE
 ├─ VRAM
 ├─ RAM
 ├─ fabricante da GPU
 ├─ quantização disponível
 ├─ modelos já residentes
 └─ custo esperado de load e unload
 ↓
fronteira qualidade × latência × recurso
 ↓
CHAMPION
 ↓
cadeia de fallback
 ↓
EXECUTA
 ↓
verificador independente
 ↓
EVIDÊNCIA
```

### 14.1 Score

```
score =
    w_quality      * qualidade_prevista
  + w_consistency  * consistencia_prevista
  + w_latency      * inverso_da_latencia
  + w_vram         * inverso_da_vram
  + w_reuse        * bonus_de_modelo_residente
  + w_local        * preferencia_local
  + w_license      * aderencia_de_licenca
  + w_stability    * saude_do_runtime
  - w_load         * custo_de_carregar_modelo
  - w_conversion   * custo_de_adapter
  - w_risk         * risco
```

Portões duros são aplicados **antes** do score. Um modelo com licença `UNKNOWN_BLOCKED` nunca chega à etapa de pontuação.

### 14.2 Política do roteador

```yaml
router:
  policy_id: "LOCAL_FIRST_QUALITY_BALANCED"

  hard_gates:
    require_license_approved: true
    require_model_hash: true
    require_runtime_health: true
    require_consent_for_identity: true
    deny_unbounded_jobs: true

  objectives:
    quality: 0.34
    consistency: 0.20
    latency: 0.12
    vram: 0.10
    model_residency: 0.08
    local_preference: 0.08
    stability: 0.08

  fallback:
    on_oom:
      - reduce_batch
      - enable_tiling
      - enable_offload
      - select_quantized_variant
      - select_smaller_challenger
    on_quality_fail:
      - increase_quality_profile
      - switch_champion
      - repair_failed_regions
    on_runtime_down:
      - switch_backend
      - degrade_to_deterministic_path
      - report_blocked_with_reason
```

### 14.3 Técnicas anti-gargalo

Pool de memória de GPU. Residência de modelo. LRU ponderado por tamanho e custo de recarga. Batches compatíveis. Prefetch do próximo modelo. Modelo fixado para laços. Offload para RAM da CPU. Offload para NVMe apenas quando medido. Quantização automática por perfil. Inferência em tiles ou patches. Streaming de frames. Backpressure. Prioridades. Preempção segura. Checkpoint. Cancelamento. Multi-GPU opcional. Workers isolados. Probes de saúde. Circuit breakers.

E a regra que mais economiza na prática: **nunca carregar um LLM gigante para classificar uma string simples.**

### 14.4 Aviso real medido neste hardware

```
Atencao: 16376 MiB de VRAM com ComfyUI e Ollama carregados ao mesmo tempo.
Antes de uma geracao pesada, derrube o que nao for usar: start.bat --parar
```

Isto não é hipótese. Com ComfyUI e Ollama residentes em 16 GB, uma chamada ao worker que levava 41 s passou de 280 s e até `nvidia-smi` travou. O agendador existe por causa desse fato medido.

### 14.5 "Automático" não pode ser caixa preta

Ao passar o cursor sobre a escolha:

```
Escolhido   FILME RÁPIDO ULTRA 8B
Motivo      cabe em 16 GB · local · perfil de 15 s · modelo já residente
            qualidade mínima aprovada no benchmark do módulo
Fallback    FILME QUALITY MAX
Custo obs.  ~70 s no último uso neste hardware
```

---

## 15. PERFIS DE HARDWARE

```yaml
hardware_profiles:

  CONSUMER_8GB:
    strategy:
      - small_models
      - GGUF_Q4
      - diffusion_4bit_where_validated
      - aggressive_tiling
      - sequential_model_residency

  CONSUMER_16GB:            # perfil medido neste projeto: RTX 4090 Laptop
    strategy:
      - medium_models
      - Nunchaku_when_supported
      - CPU_offload
      - generate_at_720p_or_1080p_then_master
      - never_two_heavy_services_resident
    measured:
      image_1024_plus_4x_upscale: { seconds: 36.12, vram_peak_mib: 9507 }
      video_832x480_33f_20steps_rife_h265: { seconds: 400.82, vram_peak_mib: 15752 }
      hunyuan3d_image_to_mesh: { seconds: 82.1, output_bytes: 8900000 }

  CONSUMER_24GB:
    strategy:
      - high_quality_image
      - 8B_video_profiles
      - TRELLIS_and_Hunyuan3D_profiles_when_fit
      - larger_VLM_quantized
      - 4K_mastering_not_necessarily_native_generation

  MULTI_GPU_WORKSTATION:
    strategy:
      - larger_models
      - distributed_serving
      - parallel_shots
      - 3D_reconstruction
      - high_res_video_restoration

  SERVER_CLUSTER:
    strategy:
      - Kimi_K3_class_frontier_specialists
      - vLLM_SGLang_distributed
      - training
      - massive_batch
```

---

## 16. DESIGN DO SELETOR DE MODELO

**Modo normal:**

```
Motor
  (•) Automático — recomendado
  ( ) Mais rápido
  ( ) Mais qualidade
  ( ) Menor VRAM
  ( ) Somente local
```

**Modo avançado:** nomes técnicos dos modelos disponíveis, com VRAM estimada e tempo observado.

**Modo governança:** repositório, commit, hash dos pesos, licença, runtime, benchmark, SBOM, CVEs conhecidas, status.

---
## 17. FLUXOS PRONTOS NO MENU

Cada fluxo é um macro-nó que abre em subgrafo com duplo clique. O iniciante usa um nó. O avançado abre tudo.

| Fluxo no menu | I/O | Pipeline resumido | Est. |
| --- | --- | --- | --- |
| START TO END VIDEO 4K | roteiro/refs → filme 4K final | direção → keyframes → I2V/T2V → continuidade → restauro → fps → grade → áudio → master | ESP |
| PRIMEIRO E ÚLTIMO FRAME | 2 frames → clipe | restrição de frames → geração → QC temporal → reparo | ESP |
| IMAGENS PARA FILME INTELIGENTE | várias refs → shot | classificar refs → travas de cena e identidade → planejar → vídeo | ESP |
| ROTEIRO PARA FILME | texto → timeline → shots | diretor → shot builder → geração em lote → edição | ESP |
| 3D PARA FILME REAL | cena → filme | guias de render de câmera → re-render de vídeo → pós | ESP |
| ARQVIZ PARA FILME CINEMA | CAD/BIM/3D → filme | travas geométricas → luz → keyframes → vídeo | ESP |
| IMAGEM MASTER 4K | prompt/ref → 4K | gerar → restaurar detalhe → upscale → QC | PAR |
| IMAGEM MASTER 8K | prompt/ref → 8K | gerar → tiles → restaurar → merge → QC | ESP |
| IMAGEM MASTER 16K | prompt/ref → 16K | tiles hierárquicos → guardas de detalhe → merge → QC | ESP |
| RENDER PARA FOTO REAL | render → foto | depth/normal/seg → trava estrutural → re-render | ESP |
| VÁRIAS REFS PARA KEY VISUAL | refs → imagem mestre | analisar → travar → compor → julgar → reparar | ESP |
| OBJETO PARA 3D PRO | multi-ref → asset 3D | segmentar → câmera/geometria → roteador → retopo → UV → PBR → QC | PAR |
| PERSONAGEM 3D QUALITY | refs → humano digital | consentimento → DNA → corpo/cabeça → pele → cabelo → rig → face → LOD → QC | ESP |
| VÍDEO PARA MOCAP | vídeo → BVH/FBX | track → pose 3D → movimento no mundo → suavizar → footlock → retarget | ESP |
| ANIMAL PARA 3D ANIMÁVEL | refs/vídeo → animal | segmentar → forma → pelo → rig → movimento → QC | ESP |
| CARRO PARAMÉTRICO | spec/refs → veículo | carroceria → rodas → interior → materiais → física → LOD | ESP |
| PLANTA PARA BIM 3D | PDF/imagem → IFC | OCR/linhas → cômodos/aberturas → topologia → autoria BIM → validação | ESP |
| DWG PARA BIM | DWG → IFC | ler entidades → inferência semântica → BIM → IDS/QC | ESP |
| PLANTA PARA CASA MOBILIADA | planta → cena | parse → paredes/aberturas/telhado → mobília → materiais → luz | ESP |
| ENDEREÇO PARA MUNDO 3D | endereço → digital twin | geocode → OSM/Overture → DEM → edifícios/ruas → vegetação → tiles | ESP |
| GEO + CAD + BIM PARA CENA | fontes mistas → mundo | normalizar CRS → alinhar → resolver conflitos → cena | ESP |
| TELA PARA UI REACT | imagem → UI de app | layout/OCR/tokens → plano de componentes → código → browser → regressão visual | ESP |
| REFERÊNCIAS PARA DESIGN SYSTEM | imagens → tokens/componentes | agrupar → extrair → normalizar → biblioteca | ESP |
| DOCUMENTOS PARA COSMETA | documentos → knowledge pack | ingerir → parsear → afirmações → embed → grafo → contradizer → validar → promover | ESP |
| CONHECIMENTO PARA LoRA | pacote verificado → adapter | exportar dataset → treinar → avaliar → red team → champion/challenger | ESP |
| VOZ CONSENTIDA PARA PERSONAGEM | voz + DNA → personagem falando | perfil de locutor → TTS → visema → movimento facial → vídeo | ESP |

---

## 18. START TO END VIDEO 4K — ESPECIFICAÇÃO COMPLETA

### 18.1 Parâmetros simples

```yaml
display_name_ptbr: "START TO END VIDEO 4K"
icon: "video"

controls:
  duration_seconds:
    min: 1
    max_default: 15
    step: 0.5
    extensible_by_shots: true      # 15 s é o limite de um nó, não do filme
    ui: "slider"

  speed:
    label_ptbr: "Velocidade"
    min: 0.25
    max: 4.0
    default: 1.0
    ui: "slider"
    note: "reamostra com interpolação, mantendo o fps de saída"

  fps:
    presets: [24, 25, 30, 48, 50, 60]
    default: 30
    ui: "chips"

  aspect_ratio:
    ui: "ratio"
    presets:
      - "1:1"
      - "4:5"
      - "9:16"
      - "2:3"
      - "3:2"
      - "4:3"
      - "16:9"
      - "1.85:1"
      - "2:1"
      - "2.39:1"
      - "21:9"
      - "manual"

  output:
    master_resolution: "3840x2160 ou equivalente ao aspecto"
    hdr: false
    audio: true
```

Para 15 s a 30 fps o master tem **450 frames**.

"21:9" não é uma resolução única. Ele aceita `2.39:1` cinema, `3840×1600`, `3440×1440` ou custom. O resolvedor abaixo é o que já roda no repositório:

```python
def resolve_dimensions(config: dict, *, kind: str, multiple: int) -> tuple[int, int]:
    """Converte aspecto e classe de resolução em largura e altura válidas.

    Só age quando o usuário escolheu um preset; largura e altura manuais continuam
    valendo, para não sequestrar o controle de quem quer números exatos.
    """
    aspect_key = str(config.get("aspect_ratio", "manual"))
    resolution_key = str(config.get("resolution", "manual"))
    if aspect_key == "manual" or resolution_key == "manual":
        return int(config.get("width", 0) or 0), int(config.get("height", 0) or 0)
    table = IMAGE_RESOLUTIONS if kind == "image" else VIDEO_RESOLUTIONS
    if aspect_key not in ASPECT_RATIOS or resolution_key not in table:
        raise EngineExecutionError(
            "INVALID_FORMAT_PRESET",
            f"Combinação inválida: aspecto {aspect_key}, resolução {resolution_key}",
        )
    height = table[resolution_key]
    width = round(height * ASPECT_RATIOS[aspect_key])
    snap = lambda value: max(multiple, int(round(value / multiple)) * multiple)
    return snap(width), snap(height)
```

### 18.2 Grafo interno

```
ROTEIRO / PROMPT / PACOTE DE REFERÊNCIAS
          │
          ▼
   [ENTENDER PEDIDO]
          │
          ▼
   [DIRETOR DE CENA] ─────────────────────► TIMELINE
          │
          ├──► [TRAVA DE IDENTIDADE]
          ├──► [TRAVA DE LOCAL]
          ├──► [TRAVA DE FIGURINO]
          ├──► [TRAVA DE OBJETOS]
          └──► [DIRETOR DE CÂMERA E LUZ]
                         │
                         ▼
                 [KEYFRAME MESTRE]
                         │
                         ▼
              [MEGA ROTEADOR DE VÍDEO]
                  │              │
              geração         extensão
                  │              │
                  └──────┬───────┘
                         ▼
                [JUIZ DE CONTINUIDADE]
                  │ passa      │ falha
                  │            ▼
                  │      [REPARO AUTOMÁTICO]
                  │            │
                  └──────┬─────┘
                         ▼
                 [RESTAURAR VÍDEO]
                         ▼
                [FIXAR 30 FPS · RIFE]
                         ▼
                [MASTER 4K · TILES]
                         ▼
                   [OCIO · GRADE]
                         ▼
        [FOLEY] + [MÚSICA] + [VOZ]
                         ▼
                    [MIX MASTER]
                         ▼
                     [FFMPEG MUX]
                         ▼
                        [QC]
                         ▼
             MASTER + EVIDÊNCIA
```

### 18.3 Regra honesta de resolução

Gerar em 4K, 8K ou 16K significa **master de saída**, não que o modelo de difusão gerou cada pixel nativamente nessa resolução. O pipeline profissional é:

```
geração em resolução eficiente para o modelo
  → restauração temporal
  → upscale espacial
  → reconstrução seletiva de detalhe
  → interpolação temporal
  → pipeline de cor
  → master de saída
```

Isso economiza VRAM e costuma ser mais robusto. LTX-2.x é a exceção que anuncia alta resolução nativa; mesmo assim o mastering posterior continua no fluxo.

---

## 19. IMAGENS 4K ATÉ 16K

```
PROMPT + PACOTE DE REFERÊNCIAS
  ↓
travas de geometria, segmentação e identidade
  ↓
geração em resolução eficiente para o modelo
  ↓
juiz de qualidade
  ↓
reparo regional
  ↓
upscale base
  ↓
planejador semântico de tiles
  ↓
difusão e detalhe por tile
  ↓
merge com consciência de emenda
  ↓
consistência global de cor
  ↓
QC de rosto, texto e objeto
  ↓
MASTER 4K / 8K / 16K
```

### 19.1 Planejador semântico de tiles

Nunca dividir rosto, mão, texto ou objeto crítico de forma arbitrária.

```yaml
tile_planner:
  detect:
    - faces
    - hands
    - text
    - architecture_edges
    - subject_boundaries
  overlap_px: "adaptive"
  global_context_thumbnail: true
  preserve_seed_family: true
  final_global_pass: true
  never_split_across:
    - face_bbox
    - hand_bbox
    - text_line_bbox
```

### 19.2 Lição medida sobre tiles

```
image.upscale com tile=0   →  244.9 s
image.upscale com tile=256 →    6.0 s   (40x mais rápido)
```

Por isso o padrão do nó é `tile = 256`. Isto foi medido, não estimado.

---

## 20. OMNI FLOW — VÁRIAS IMAGENS PARA IMAGEM, VÍDEO OU 3D

```
CONJUNTO DE IMAGENS
 ↓
deduplicar
 ↓
ranquear qualidade
 ↓
agrupar por sujeito, local e tempo
 ↓
extrair:
   identidade
   objetos
   figurino
   câmera
   profundidade
   segmentação
   paleta
   metadata geográfica
 ↓
montar ReferenceGraph
 ↓
usuário escolhe:
   IMAGEM · VÍDEO · 3D · DNA HUMANO · MUNDO
 ↓
o roteador compila o workflow correto
```

```json
{
  "subjects": [],
  "locations": [],
  "objects": [],
  "wardrobe": [],
  "camera_hypotheses": [],
  "geospatial_links": [],
  "timeline_hypotheses": [],
  "source_assets": [],
  "confidence": {},
  "provenance": {}
}
```

O agente pode definir a lógica das referências — qual é primeiro frame, qual é último, qual é identidade, qual é ambiente — e **deve respeitá-la** depois de decidida, registrando a decisão no `ReferenceGraph`.

---

## 21. PRESETS PROFISSIONAIS DE CÂMERA E CINEMA

O produto usa presets técnicos, não filtros de rede social.

### 21.1 Sensor e lente

```yaml
camera_presets:
  CINEMA_S35:
    sensor: "Super 35"
    focal_lengths_mm: [18, 24, 28, 32, 35, 40, 50, 65, 75, 85]

  CINEMA_FULL_FRAME:
    sensor: "Full Frame"
    focal_lengths_mm: [20, 24, 28, 35, 50, 65, 85, 100, 135]

  ARCHITECTURE:
    lens_behavior:
      preserve_verticals: true
      low_distortion: true
    focal_lengths_mm: [24, 28, 35, 45, 50]

  PORTRAIT:
    focal_lengths_mm: [50, 65, 85, 105, 135]

  MACRO_PRODUCT:
    focal_lengths_mm: [60, 90, 100, 105]
    min_focus_ratio: "1:1"
```

Controles expostos: focal; sensor; abertura ou proxy de T-stop; distância de foco; ângulo de obturador; altura de câmera; pitch, yaw e roll; dolly, pan, tilt, orbit, crane e handheld; distorção de lente; aberração cromática opcional; breathing opcional; profundidade de campo; motion blur; áreas seguras.

### 21.2 Movimentos de câmera `[IMPLEMENTADO — 25 movimentos]`

São engenharia de prompt determinística e local: a descrição é anexada ao prompt do usuário. Nenhum modelo proprietário de controle de câmera é usado ou imitado.

```python
CAMERA_MOTIONS: dict[str, str] = {
    "nenhum": "",
    "estática": "static locked-off camera, no camera movement",
    "dolly in": "slow dolly in, camera pushes forward toward the subject",
    "dolly out": "slow dolly out, camera pulls back away from the subject",
    "crash zoom in": "fast crash zoom in, abrupt aggressive push toward the subject",
    "crash zoom out": "fast crash zoom out, abrupt pull away from the subject",
    "zoom in": "smooth optical zoom in on the subject",
    "zoom out": "smooth optical zoom out revealing the surroundings",
    "pan esquerda": "camera pans left horizontally at a steady speed",
    "pan direita": "camera pans right horizontally at a steady speed",
    "whip pan": "fast whip pan with motion blur",
    "tilt up": "camera tilts upward revealing height",
    "tilt down": "camera tilts downward revealing the ground",
    "órbita 360": "camera orbits 360 degrees around the subject, smooth circular arc",
    "arco esquerda": "camera arcs to the left around the subject",
    "arco direita": "camera arcs to the right around the subject",
    "crane up": "crane shot rising upward, camera lifts high above the scene",
    "crane down": "crane shot descending, camera lowers toward the ground",
    "drone fpv": "fpv drone flight, fast sweeping aerial move through the scene",
    "handheld": "handheld camera, subtle organic shake, documentary feel",
    "bullet time": "bullet time, camera orbits while action is frozen in slow motion",
    "dutch angle": "dutch angle, tilted horizon, unsettling framing",
    "hyperlapse": "hyperlapse, fast forward motion through space",
    "foco puxado": "rack focus, focus shifts from foreground to background",
    "parallax": "parallax sweep, foreground and background move at different speeds",
}
```

Como são 25 opções, a regra visual manda: controle `picker` com busca, não lista suspensa.

### 21.3 Acabamento de câmera `[IMPLEMENTADO — 14 looks]`

Grão e motion blur também existem como pós real por FFmpeg no nó `media.filmlook`. Aqui é a intenção de imagem.

```python
CAMERA_LOOKS: dict[str, str] = {
    "nenhum": "",
    "anamórfico": "anamorphic lens, oval bokeh, horizontal flares, cinemascope",
    "profundidade rasa": "shallow depth of field, subject in focus, creamy background bokeh",
    "foco profundo": "deep focus, everything sharp from foreground to background",
    "grande angular": "wide angle lens, 24mm, expansive perspective",
    "teleobjetiva": "telephoto lens, 135mm, compressed perspective, isolated subject",
    "macro": "macro lens, extreme close-up, fine detail",
    "35mm película": "shot on 35mm film, natural grain, halation, filmic color response",
    "16mm película": "shot on 16mm film, pronounced grain, vintage texture",
    "luz natural": "natural available light, soft falloff, motivated sources",
    "contraluz": "backlit, rim light separating subject from background, atmospheric haze",
    "chiaroscuro": "chiaroscuro lighting, deep shadows, single hard key light",
    "hora dourada": "golden hour, warm low sun, long shadows",
    "noite neon": "neon night, wet reflective streets, cyan and magenta practicals",
}
```

### 21.4 Perfis de qualidade `[IMPLEMENTADO]`

```python
QUALITY_PRESETS: dict[str, dict] = {
    "rascunho":  {"steps_image": 4,  "steps_video": 8,  "cfg_scale": 1.0},
    "padrão":    {"steps_image": 8,  "steps_video": 20, "cfg_scale": 6.0},
    "cinema":    {"steps_image": 20, "steps_video": 32, "cfg_scale": 6.5},
    "ultra":     {"steps_image": 40, "steps_video": 50, "cfg_scale": 7.0},
}
```

`cinema` e `ultra` custam tempo real de GPU. O nó mostra a estimativa antes de rodar.

### 21.5 Aspectos `[IMPLEMENTADO — 11 proporções]`

```python
ASPECT_RATIOS: dict[str, float] = {
    "1:1": 1.0, "4:5": 0.8, "9:16": 0.5625, "2:3": 0.6667,
    "3:2": 1.5, "4:3": 1.3333, "16:9": 1.7778, "1.85:1": 1.85,
    "2:1": 2.0, "2.39:1": 2.39, "21:9": 2.3333,
}
IMAGE_RESOLUTIONS: dict[str, int] = {"base": 1024, "2K": 1440, "4K": 2160, "6K": 3384, "8K": 4320}
VIDEO_RESOLUTIONS: dict[str, int] = {"base": 480, "HD": 720, "FHD": 1080, "2K": 1440, "4K": 2160}
```

O controle `ratio` desenha retângulos na proporção real, não texto:

```
FORMATO   ▢ 1:1   ▯ 4:5   ▯ 9:16   ▭ 3:2   ▭ 16:9   ▭▭ 2.39:1   ▭▭ 21:9
```

### 21.6 Cor de produção

OpenColorIO. ACES e ACEScg quando apropriado e versionado. Scene-linear. EXR float. Display transforms. Rec.709. Rec.2020. HDR PQ e HLG quando o pipeline suportar. LUT do usuário. LUT licenciado. CDL. Grão. Halation como look opcional.

**Não embutir LUT proprietário de fabricante sem licença.** A UI pode oferecer um perfil "look semelhante" ou consumir LUT fornecido pelo usuário. Perfis de câmera de fabricante (log curves, gamuts) entram somente por transformada declarada e licenciada.

### 21.7 Escopos DaVinci-like `[IMPLEMENTADO]`

```python
SCOPE_FILTERS = {
    "forma de onda": "waveform=intensity=0.7:mode=column:display=overlay,scale=1024:-2",
    "vetorscópio":   "vectorscope=mode=color3:intensity=0.5,scale=1024:-2",
    "histograma":    "histogram=display_mode=stack,scale=1024:-2",
    "falsa cor":     "pseudocolor=preset=turbo,scale=1024:-2",
    "alfa":          "alphaextract,scale=1024:-2",
    "preto e branco": "format=gray,scale=1024:-2",
}
```

> **Correção registrada.** A falsa cor saía cinza porque `format=gray` vinha antes de `pseudocolor`, zerando a crominância. Medido: 0% de pixels coloridos antes, 100% depois da correção. A cadeia agora não converte para cinza antes de colorir.

### 21.8 Presets de produção

**Filme.** Narrative Cinema; Commercial Product; Architectural Film; Documentary Natural; Controlled Studio; Slow Motion; Dialogue; Aerial; Macro Product; Night Exterior; Golden Hour; Blue Hour.

**Imagem.** Architectural Exterior; Architectural Interior; Product Studio; Fashion Editorial; Portrait Natural; Automotive; Packshot; Concept Art; UI Mock Presentation; PBR Texture Capture.

**3D.** Object Scan; Product Asset; Game Prop; Film Prop; Human Game; Human Film; Web GLB; Building; Terrain; Vegetation.

---

## 22. CONTINUITY ENGINE — NÃO DEPENDER DE PROMPT

O estado do filme vive fora do prompt. Essa é a única forma de conseguir continuísmo real quando o ângulo muda.

```yaml
ContinuityState:
  character_ids: []
  human_dna_refs: []
  wardrobe_ids: []
  prop_ids: []
  location_id: ""
  world_state_ref: ""
  camera_profile:
    lens_mm: null
    sensor: null
    height_m: null
  lighting_profile: {}
  palette_profile: {}
  seed_family: []
  reference_assets: []
  prior_shots: []
  identity_thresholds: {}
  geometry_thresholds: {}
  temporal_constraints: {}
```

### 22.1 Scores de continuidade

Similaridade de identidade; similaridade de proporção corporal; similaridade de figurino; presença de objeto; contagem de objeto; consistência de geometria e profundidade; deriva de paleta; deriva de câmera; descontinuidade de fluxo óptico; flicker temporal; deriva de texto; continuidade na borda do quadro.

Falha gera uma **região reparável**, não necessariamente a regeneração do shot inteiro.

### 22.2 Nós inteligentes que quase nenhum sistema tem

| Nó | Função |
| --- | --- |
| `AutoModelSelector` | analisa a tarefa e escolhe entre Qwen, FLUX, Wan, LTX, TRELLIS, Hunyuan |
| `VRAMPlanner` | prevê VRAM e ativa quantização, offload, tiling e cache |
| `ReferenceLocker` | transforma referência em embedding facial, embedding CLIP, depth, normals, paleta, segmentação e geometria |
| `ContinuityChecker` | compara frame novo contra o estado: rosto, figurino, contagem de objetos, geometria, cor, câmera |
| `AutoRepair` | mascara o erro e regenera apenas a região |
| `QualityJudge` | VLM combinado com métricas tradicionais |
| `3DQualityJudge` | buracos, normais invertidas, manifold, topologia, UV, esticamento de textura, escala |
| `ShotDirector` | transforma roteiro em shots |
| `VisualRegression` | compara tela renderizada com o alvo |
| `ToolAgent` | permite ao LLM controlar Blender, Godot, FFmpeg, git, terminal, browser e Comfy |

---

## 23. PROMPT COMPILER — ENGENHARIA DE PROMPT PROFISSIONAL

Linguagem natural nunca vai direto ao modelo. Um prompt gigante não é a resposta; um IR estruturado é.

### 23.1 Entrada humana

```
garota entra no restaurante preocupada
```

### 23.2 O compilador produz

```
[IDENTITY]
CHARACTER_002

[ACTION]
walking slowly through entrance

[EXPRESSION]
subtle concern

[WARDROBE]
WARDROBE_002_LOCKED

[ENVIRONMENT]
LOCATION_RESTAURANT_01

[CAMERA]
35mm
1.5m height
slow dolly back

[LIGHT]
3200K practical interior
5600K exterior spill

[COMPOSITION]
medium full shot

[MOTION]
natural walking
hair secondary motion

[CONTINUITY]
preserve exact face
preserve clothes
preserve restaurant geometry

[NEGATIVE]
face drift
wardrobe mutation
geometry mutation
extra limbs
camera discontinuity
```

### 23.3 PromptIR

```yaml
PromptIR:
  objective: ""
  subject:
    ids: []
    constraints: []
  environment:
    id: null
    constraints: []
  action: []
  camera:
    camera_profile_ref: null
  lighting:
    light_profile_ref: null
  composition: {}
  materiality: {}
  continuity:
    state_ref: null
  output:
    modality: "image|video|3d|audio|code"
    width: null
    height: null
    fps: null
    duration_seconds: null
  negative_constraints: []
  safety_and_rights: {}
  evidence_requirements: []
```

### 23.4 Adaptadores por backend

```
PromptIR
 ├─ QwenImagePromptAdapter
 ├─ FluxPromptAdapter
 ├─ WanPromptAdapter
 ├─ LTXPromptAdapter
 ├─ HunyuanVideoPromptAdapter
 ├─ ThreeDPromptAdapter
 ├─ BlenderTaskAdapter
 ├─ CadTaskAdapter
 └─ CodeAgentTaskAdapter
```

### 23.5 Otimização de prompt — só com avaliador objetivo

Grid ou random search limitado; otimização bayesiana; beam search; busca evolutiva; mutações de prompt; varredura de seed; comparação com challenger.

Nunca "melhore 100 vezes" sem critério. Cada tentativa precisa de score, orçamento e condição de parada.

---

## 24. WORKER LOCAL — O CÉREBRO DO ESTÚDIO `[IMPLEMENTADO]`

O worker conhece todos os nós porque a fonte da verdade é o próprio `NODE_CATALOG` e o validador real. Toda proposta passa por `validate_workflow` antes de chegar ao usuário; se não passar, o erro volta para o modelo corrigir.

```python
MAX_TOOL_ROUNDS = 6

# Ferramentas expostas ao modelo
#   listar_nos       — tipos de nó com portas e campos
#   detalhar_no      — campos, padrões e opções de um tipo
#   listar_perfis    — perfis de modelo instalados e arquivos presentes
#   listar_assets    — mídias do projeto para usar como referência
#   validar_grafo    — o MESMO validador da aplicação
#   propor_grafo     — entrega ao usuário só depois de validar
```

### 24.1 Regras do sistema

```
- Só use tipos de nó que vierem de `listar_nos`. Nunca invente um tipo.
- Antes de responder com um grafo, chame `validar_grafo`. Se voltar inválido, corrija
  e valide de novo.
- Conecte respeitando os tipos de porta: a saída de um nó precisa casar com a entrada
  do próximo. `media` aceita qualquer coisa.
- Todo gerador deve terminar em um `output.preview`, para o resultado aparecer.
- Prefira poucos nós bem configurados a grafos enormes.
```

### 24.2 Duas correções que valem regra permanente

```python
@staticmethod
def _fold(value: str) -> str:
    """Compara sem acento e sem caixa: o modelo escreve 'video', o catálogo diz 'Vídeo'."""
    return "".join(
        ch for ch in unicodedata.normalize("NFD", str(value).strip().lower())
        if unicodedata.category(ch) != "Mn"
    )
```

```python
if not items:
    # Devolver lista vazia fazia o modelo concluir que o nó não existe.
    return {
        "aviso": f"Nenhuma categoria corresponde a {categoria!r}.",
        "categorias_disponiveis": sorted({item["category"] for item in NODE_CATALOG}),
        "itens": [],
    }
```

Uma lista vazia leva o modelo a **afirmar com confiança que a capacidade não existe**. Devolver as categorias disponíveis corrige o comportamento na origem.

### 24.3 Provider plugável

Ollama local por padrão (`qwen3:8b-q4_K_M` com tool calling). OpenRouter opcional, no formato de tools da OpenAI, para qualquer outro fornecedor. O nó pede o slot; ele não conhece o fornecedor.

### 24.4 Evidência de funcionamento

O worker produziu um grafo válido de 3 nós e 2 arestas com `camera_motion: dolly in`, aspecto 21:9, resolução 4K, terminando em `output.preview` — e o validador **rejeitou a primeira tentativa dele**, que foi corrigida na rodada seguinte. Esse ciclo é a prova de que o validador está no caminho, não decorando.

---
## 25. 3D QUALITY — PIPELINE MODULAR

Não faça `Imagem → Tripo → pronto`. O segredo é o seletor e o avaliador, não um único modelo.

```
REFERÊNCIAS
 ↓
SEGMENTAR OBJETO            GroundingDINO + SAM 2
 ↓
REMOVER FUNDO / MÁSCARAS
 ↓
ENTENDER CÂMERA E GEOMETRIA VGGT / MapAnything
 ↓
CONDICIONAMENTO MULTI-VISTA
 ↓
┌──────────────────────────────────────┐
│ ROTEADOR AUTOMÁTICO DE GERADOR 3D    │
│  TRELLIS.2                           │
│  Hunyuan3D-2.1                       │
│  Hunyuan3D-Omni                      │
│  SAM 3D Objects                      │
│  TripoSG · TripoSR · TripoSplat      │
│  Stable Fast 3D · SPAR3D             │
│  InstantMesh · Wonder3D              │
│  Pixal3D (gate de licença/release)   │
└──────────────────────────────────────┘
 ↓
JUIZ DE GEOMETRIA
 ↓
REPARO OU SEGUNDO CHALLENGER
 ↓
REMESH
 ↓
RETOPOLOGIA
 ↓
UV
 ↓
TEXTURA
 ↓
PBR
 ↓
NORMAL · ROUGHNESS · METALLIC · AO · DISPLACEMENT · OPACITY
 ↓
MaterialX / OpenPBR
 ↓
LOD
 ↓
GLB · USD · GAME · FILM
```

### 25.1 Juiz de qualidade 3D

```yaml
checks:
  geometry:
    - watertight_when_required
    - self_intersections
    - inverted_normals
    - non_manifold
    - scale_in_si_units
    - silhouette_similarity_to_reference
    - multi_view_consistency

  topology:
    - triangle_density
    - deformation_readiness
    - edge_flow_when_required

  uv:
    - overlap_policy
    - texel_density
    - stretching
    - padding

  pbr:
    - basecolor_lighting_leak
    - normal_map_validity
    - roughness_range
    - metallic_semantics
    - seam_visibility
```

### 25.2 Cadeia de texturização

```
GERAR GEOMETRIA
↓
REMESH
↓
RETOPO
↓
UV
↓
SÍNTESE DE TEXTURA        Hunyuan3D Paint · difusão de textura · ControlNet UV
↓
DECOMPOSIÇÃO DE MATERIAL  delighting · separação de basecolor
↓
NORMAL · ROUGHNESS · METALLIC · AO · DISPLACEMENT · OPACITY
↓
MaterialX / OpenPBR
```

### 25.3 Estado real hoje

`model3d.generate` **funciona de verdade** via ComfyUI com nós nativos Hunyuan3D-2:

```
ImageOnlyCheckpointLoader → CLIPVisionEncode → Hunyuan3Dv2Conditioning
  → EmptyLatentHunyuan3Dv2 → KSampler → VAEDecodeHunyuan3D
  → VoxelToMesh → SaveGLB
```

Evidência: malha 3D gerada pelo app em **82.1 s**, GLB de **8.9 MB**, `Content-Type: model/gltf-binary`. `model3d.retopology`, `model3d.texture`, `model3d.animate` e `model3d.export` também estão implementados. O restante da cadeia acima é `[ESPECIFICADO]`.

---

## 26. DIGITAL HUMAN — DNA HUMANO

O objetivo é um `HumanDNA` versionado, não um render parecido. Depois de criada, a identidade não muda mais: filme, game, avatar corporativo, web e AR/VR usam o mesmo ID humano com representações diferentes.

### 26.1 Entradas

Várias fotos. Vídeo. Metadados de câmera quando disponíveis. Medidas reais opcionais. Altura real. Referências de rosto, corpo, cabelo e pele. **Consentimento do titular quando identidade real for processada.**

### 26.2 Pipeline completo

```
ConsentManifest
 ↓
Ranqueamento de qualidade das referências
 ↓
Segmentação de rosto, corpo e cabelo
 ↓
Estimativa de câmera                       VGGT / calibração
 ↓
Ajuste de corpo paramétrico                MHR / SAM 3D Body
 ↓
Refinamento de geometria multi-vista
 ↓
Medidas e proporções corporais
 ↓
Reconstrução de cabeça
 ↓
Malha canônica em pose neutra
 ↓
Canonicalização de UV
 ↓
Projeção de textura das referências aprovadas
 ↓
Delighting                                 remove a luz da captura
 ↓
Extração PBR:
   BaseColor
   Roughness
   Normal
   MicroNormal
   Displacement
   Specular / IOR
   Perfil SSS
 ↓
Olhos · dentes · boca
 ↓
Groom de cabelo
 ↓
Esqueleto e rig
 ↓
Blendshapes faciais · FACS · visemas
 ↓
Retarget de movimento
 ↓
LODs
 ↓
Perfis Game · Web · Film
 ↓
HumanDNA.json
```

### 26.3 Sobre o MHR

`Momentum Human Rig (MHR)` entra como representação candidata com licença e versionamento registrados. Ele interessa porque o **SAM 3D Body** o usa como representação paramétrica de corpo humano. O repositório `facebookresearch/MHR` documenta **45 parâmetros de identidade, 204 de pose, 72 de expressão** e múltiplos LODs.

Não confundir com **MetaHuman/Epic**, que é ecossistema proprietário e só entra por adapter opcional licenciado.

### 26.4 Schema do HumanDNA

```json
{
  "human_dna_id": "uuidv7",
  "version": 1,
  "subject": {
    "kind": "real_consented|synthetic|licensed_scan",
    "consent_manifest_id": "uuidv7-or-null"
  },
  "canonical_body": {
    "representation": "MHR|SMPLX_OPTIONAL|CUSTOM_PARAMETRIC",
    "parameters_ref": "asset://...",
    "measurements_si": {
      "height_m": null,
      "shoulder_width_m": null,
      "chest_circumference_m": null,
      "waist_circumference_m": null,
      "hip_circumference_m": null,
      "inseam_m": null,
      "arm_length_m": null,
      "head_circumference_m": null
    }
  },
  "head": {
    "mesh_ref": "asset://...",
    "landmarks_ref": "asset://...",
    "blendshape_set_ref": "asset://..."
  },
  "surface": {
    "uv_ref": "asset://...",
    "pbr_material_ref": "asset://...",
    "sss_profile_ref": "asset://...",
    "micro_detail_ref": "asset://..."
  },
  "hair": {
    "groom_ref": "asset://...",
    "lod_refs": []
  },
  "rig": {
    "skeleton_ref": "asset://...",
    "control_rig_ref": "asset://...",
    "viseme_map_ref": "asset://..."
  },
  "identity_evidence": [],
  "source_assets": [],
  "provenance": {},
  "license": {},
  "created_at": "",
  "supersedes": null
}
```

### 26.5 Corpo anatômico neutro

Para digitalização e reconstrução corporal, o sistema oferece o perfil técnico **CORPO ANATÔMICO NEUTRO** (`slot://human.anatomy.reconstruct`). Ele produz forma, UV, material e rig a partir de referências aprovadas, inclusive sem roupa quando houver base legítima e consentida — é o mesmo requisito de qualquer pipeline sério de personagem digital: sem a superfície corporal completa não há UV canônico, não há extração de PBR e SSS coerente, e a roupa simulada não assenta.

A cadeia é:

```
referências aprovadas
 ↓
segmentação de pele, cabelo e adereços
 ↓
ajuste do corpo base paramétrico às medidas do DNA
 ↓
render canônico multi-vista do corpo base (turnaround)
 ↓
projeção da textura das referências sobre a UV do corpo base
 ↓
delighting: a cor da captura sai, a forma fica
 ↓
extração de BaseColor, Roughness, Normal, MicroNormal, Displacement e SSS
 ↓
ajuste fino dos mapas
 ↓
modelo pronto: rigado, com face shapes, morphs e lipsync
```

O produto separa **criação sintética** de **identidade real**. Identidade real exige `ConsentManifest` com base de direitos, escopo de saídas permitidas e revogação. O que o sistema não faz, e não fará: colocar uma pessoa real, sem consentimento, em conteúdo sexual falso, ou clonar identidade e voz para enganar terceiros. Isso não é uma limitação de capacidade técnica — é a linha entre uma ferramenta de produção e uma ferramenta de fraude.

### 26.6 Perfis de entrega

**Game Ready.** Malha otimizada; LOD0 a LODn; bake de normal; PBR comprimido; esqueleto estável; blendshapes mínimos; mapa de retarget de animação; colisão; KTX2/Basis; meshopt ou Draco; adapters GLB, Godot e O3DE.

**Film Ready.** Malha de alta densidade; subdivisão; UDIM; displacement; micro normal; curvas de groom; SSS de alta qualidade; conjunto FACS estendido; olhos e dentes em alta resolução; USD e MaterialX; workflow de render ciente de ACES.

**Web Ready.** GLB; LOD; KTX2; MeshOpt; avatar gaussiano opcional; runtime Babylon.js ou Three.js.

### 26.7 Banco de animação e expressões

```
BIBLIOTECA DE MOVIMENTO
 ├─ locomoção: andar, correr, virar, parar, sentar, levantar
 ├─ gestos: apontar, acenar, negar, concordar, encolher ombros
 ├─ manipulação: pegar, soltar, carregar, empurrar
 ├─ expressão corporal: postura confiante, cansada, tensa, relaxada
 └─ facial FACS: 52 shapes ARKit-like + visemas por idioma
```

Cada clipe carrega: rig de origem, taxa de amostragem, unidades, direitos, e um mapa de retarget para o esqueleto canônico.

---

## 27. MOVIMENTO — MOCAP E CLONE

```
VÍDEO
 ↓
rastreamento de pessoa
 ↓
pose 2D
 ↓
recuperação de humano 3D
 ↓
movimento ancorado no mundo
 ↓
suavização temporal
 ↓
trava de pé no chão
 ↓
plausibilidade física
 ↓
mapeamento de esqueleto
 ↓
retarget
 ↓
BVH / FBX / glTF anim
```

Backends candidatos: GVHMR; SAM 3D Body com wrapper temporal; modelos de HMR e pose; retarget do Blender; IK determinístico.

**Face:** landmarks faciais; coeficientes de expressão; visemas; mapeamento FACS; suavização; piscada e olhar; lipsync.

**Clone ao vivo:** captura por webcam ou stream, pose em tempo real, retarget contínuo. Exige consentimento quando a fonte é pessoa real identificável.

---

## 28. ANIMAL, CRIATURA E VEÍCULO

### 28.1 Animal — maturidade honesta

O ecossistema animal é menos padronizado que o humano. O produto marca isso.

```yaml
animal_pipeline:
  maturity: "MIXED_PRODUCTION_AND_RESEARCH"
  stages:
    - segmentation
    - species_and_body_classification
    - SMAL_style_fit_when_compatible
    - freeform_3d_refinement
    - texture_and_fur_reconstruction
    - procedural_quadruped_rig
    - motion_recovery
    - retarget
    - game_or_film_packaging
```

Tecnologias: SMAL e SMALify; 3DAnimals; AnimalAvatar; geradores 3D genéricos; Blender hair curves; movimento com consciência física; templates de esqueleto customizados.

**Pelo por parametrização:** densidade, comprimento, curvatura, aglomeração, direção por região do corpo, variação de cor por raiz e ponta, cards para game e curvas para film.

### 28.2 Veículo paramétrico

```
ESPECIFICAÇÃO OU REFERÊNCIAS
 ↓
classe do veículo (sedã, SUV, esportivo, caminhão, moto)
 ↓
proporções: entre-eixos, bitola, altura, balanços
 ↓
superfície de carroceria paramétrica       CadQuery + geometry nodes
 ↓
aberturas: portas, capô, porta-malas, vidros
 ↓
rodas e pneus paramétricos
 ↓
interior: bancos, painel, volante, console
 ↓
materiais: pintura multicamada, vidro, borracha, cromo, tecido
 ↓
física: massa, centro de gravidade, suspensão, atrito
 ↓
LOD e export
```

O gerador 3D pode entrar como referência de forma; a geometria final que precisa ser exata sai do kernel paramétrico. É a mesma regra do telhado: **IA escolhe parâmetros, geometria determinística produz o resultado.**

---

## 29. ARQUITETURA — PLANTA, CAD E BIM

### 29.1 Raster ou PDF para grafo de planta

```
PDF / scan / imagem
 ↓
deskew e calibração de escala
 ↓
OCR                                  cotas, textos, nomes de cômodo
 ↓
detecção de linhas de parede
 ↓
modelo de cômodos e aberturas
 ↓
reconstrução de topologia
 ↓
rótulos semânticos
 ↓
solver de restrições
 ↓
FloorplanGraph
```

Backends candidatos: CubiCasa5K; RoomFormer; Raster2Seq; Raster-to-Graph; geometria CAD determinística.

### 29.2 FloorplanGraph

```json
{
  "units": "m",
  "levels": [],
  "walls": [],
  "doors": [],
  "windows": [],
  "rooms": [],
  "columns": [],
  "stairs": [],
  "fixtures": [],
  "dimensions": [],
  "source_evidence": []
}
```

### 29.3 DWG — expectativa honesta

Núcleo aberto: `LibreDWG` para leitura e escrita de DWG quando compatível; DXF; OpenCascade e CadQuery para B-Rep e paramétrico; Blender para visual; IfcOpenShell e Bonsai para BIM.

**Não prometer interpretação semântica perfeita de todo DWG.** A ordem é:

1. ler entidades;
2. detectar layers e blocos;
3. aplicar regras CAD;
4. usar VLM/LLM **apenas** para ambiguidade;
5. gerar `FloorplanGraph`;
6. validar;
7. só então fazer autoria BIM.

### 29.4 Telhado paramétrico

Algoritmos: limpeza do polígono de footprint; straight skeleton; eixo medial quando aplicável; restrições de inclinação; geração de cumeeira e água-furtada; beirais; calhas opcionais; templates de tipo de telhado; colisão com volumes superiores; autoria BIM.

IA pode escolher os parâmetros. **A geometria final é determinística.**

### 29.5 Mobiliário automático

```
RoomGraph
 ↓
classificação de função do cômodo
 ↓
portas, janelas e zonas de folga
 ↓
grafo de circulação
 ↓
candidatos de asset
 ↓
solver de restrições
 ↓
colisão física
 ↓
pontuação de layout
 ↓
cena
```

Pontuação: passagem; acesso a portas; distância funcional; colisão; ergonomia; linha de visão; iluminação; estética opcional.

`PhyScene` e pesquisas semelhantes entram como challenger. O core mantém um solver determinístico.

### 29.6 Sol, daylight, clima e energia

Posição solar determinística; geolocalização; data e hora; timezone; norte; sombreamento; daylight; arquivos climáticos quando aplicável; adapters Radiance, Honeybee e Ladybug; adapters EnergyPlus e OpenStudio.

**Difusão não calcula insolação.**

```
BIM + GEOREF + TEMPO
 ↓
posição solar
 ↓
modelo de céu
 ↓
Radiance / daylight
 ↓
métricas
 ↓
EVIDÊNCIA
```

### 29.7 Pranchas arquitetônicas e continuísmo

`arch.sheet`, `arch.section`, `arch.elevation` e `arch.axon` derivam do mesmo BIM. Continuísmo em arquitetura não é prompt: é a mesma geometria projetada de ângulos diferentes. A imagem fotorrealista entra por cima como re-render controlado por depth, normal e segmentação da geometria real.

---

## 30. GIS E MUNDO REAL

### 30.1 Núcleo aberto

OpenStreetMap; Overture Maps; GeoParquet; GDAL/OGR; PROJ; PDAL; DuckDB Spatial; PostGIS; MapLibre GL JS; deck.gl; kepler.gl; PMTiles; MBTiles; CesiumJS; Cesium Native; 3D Tiles; glTF.

### 30.2 Providers opcionais

Cesium ion; Esri/ArcGIS; Google Photorealistic 3D Tiles; provedores de DEM e imagery; serviços comerciais de geocode.

**Provider não vira contrato de nó.**

```yaml
capability_slot: "geo.photorealistic_3d_tiles"
providers:
  - id: "local_3d_tiles"
    priority: 100
  - id: "cesium_ion"
    priority: 50
  - id: "google_photorealistic_tiles_via_allowed_adapter"
    priority: 40
```

Dados e produtos proprietários **não** são chamados de open source. O core continua funcionando com fontes abertas e locais.

### 30.3 Endereço para mundo

```
ENDEREÇO
 ↓
geocoder local ou provider permitido
 ↓
coordenadas canônicas
 ↓
seleção de CRS
 ↓
Overture + OSM
 ↓
DEM
 ↓
imagery se licenciada e disponível
 ↓
edifícios
 ↓
ruas
 ↓
água
 ↓
cobertura do solo
 ↓
vegetação procedural
 ↓
overlay de CAD e BIM
 ↓
WorldState
 ↓
3D Tiles / SceneGraph
```

### 30.4 Metadata, geolocalização, planta e fotos

O `AssetGraph` liga as fontes sem perder proveniência.

```
EXIF DA FOTO
 ├─ GPS
 ├─ focal
 ├─ hora de captura
 ├─ orientação
 └─ metadata do dispositivo
      │
      ▼
 GeoReference
      │
CAD ──┤
BIM ──┤
OSM ──┤
Overture ┤
DEM ──┤
LiDAR ┤
drone ┤
fotos ┤
      ▼
  WorldState canônico
```

Cada alinhamento guarda:

```yaml
SpatialAlignment:
  source_asset_id: ""
  target_world_id: ""
  source_crs: ""
  target_crs: ""
  transform_4x4: []
  method: "EXIF|CONTROL_POINTS|ICP|VGGT|COLMAP|MANUAL"
  estimated_error_m: null
  verified: false
  evidence_refs: []
```

Perder CRS ou unidade é defeito, não detalhe.

---

## 31. NATUREZA PROCEDURAL

IA descreve intenção. Engines procedurais geram milhões de elementos com reprodutibilidade por seed.

### 31.1 Árvore

```
perfil de espécie
→ grafo do tronco
→ gramática de ramificação
→ afinamento
→ níveis de galho
→ aglomerados de ramos finos
→ folhas (cards ou malha)
→ UV e PBR de casca
→ pesos de vento
→ LOD
```

```yaml
TreeSpec:
  species_id: ""
  age_years: null
  height_m: null
  crown_radius_m: null
  trunk_radius_m: null
  branch_density: null
  phototropism: null
  gravitropism: null
  asymmetry: null
  seed: 0
  season: "summer"
  wind_profile_ref: null
  lod_profile: "GAME|WEB|FILM"
```

Backends: Blender Geometry Nodes; curvas; algoritmos tipo L-system e space colonization; bibliotecas próprias de espécies parametrizadas.

### 31.2 Grama, mato e pasto

```
terreno
→ máscara de bioma
→ declividade
→ umidade
→ exclusões de via e edificação
→ campo de densidade
→ mistura de espécies
→ scatter
→ LOD perto, médio e longe
→ vento
```

### 31.3 Água

Superfície analítica ou procedural; Fresnel; IOR; absorção; espalhamento; espectro de ondas e normais; máscara de margem; espuma; reflexão; refração; caustics opcional; simulação de fluido apenas quando a cena exigir.

### 31.4 Montanhas e terreno

**Mundo real:** DEM; DSM/DTM quando disponível; reprojeção; clipmap multi-resolução; passo de erosão opcional.

**Fictício:** base fractal; erosão hidráulica; erosão térmica; máscaras de cume; máscaras de rocha, solo, neve e vegetação.

### 31.5 Céu, vento e clima

Céu procedural por data, hora e condição; biblioteca HDRI; vento como campo animado que alimenta árvore, grama, tecido e cabelo; neve e chuva por partículas e materiais; fogo e fumaça por Blender e OpenVDB.

---

## 32. UI PARA CÓDIGO

Não usar difusão para desenhar a interface inteira. Usar visão, VLM e agente de código com laço de regressão visual.

```
SCREENSHOT / REFERÊNCIAS
 ↓
OCR
 ↓
detecção de layout
 ↓
segmentação semântica
 ↓
extração de design tokens
 ↓
grafo de componentes
 ↓
recuperar design system existente
 ↓
plano do VLM
 ↓
agente de código
 ↓
React / Vue / Svelte / Godot / Babylon
 ↓
render no browser ou runtime
 ↓
screenshot
 ↓
regressão visual
 ↓
laço de correção limitado
```

O nó `TELA PARA UI` **não** gera uma parede de `<div>` e chama isso de resultado.

### 32.1 ComponentGraph

```json
{
  "viewport": {"width": 1440, "height": 900},
  "tokens": {
    "colors": {},
    "spacing": {},
    "radius": {},
    "typography": {}
  },
  "components": [
    {
      "id": "c1",
      "semantic_type": "button",
      "bbox": [0, 0, 0, 0],
      "text": "",
      "states": ["default", "hover", "pressed", "disabled"],
      "children": []
    }
  ]
}
```

### 32.2 Verificação

Matriz de viewports; diferença de pixel; similaridade perceptual; conteúdo de texto; caixas de layout; métricas tipográficas; estados de componente; teclado e foco; acessibilidade; screenshots responsivos.

---

## 33. AGENTES DE CÓDIGO, GUI E FERRAMENTAS

```yaml
agent_slots:
  tiny_router:    { display_ptbr: "ROTEADOR LEVE" }
  repo_reader:    { display_ptbr: "ENTENDER PROJETO" }
  code_planner:   { display_ptbr: "PLANEJAR CÓDIGO" }
  code_editor:    { display_ptbr: "PROGRAMAR" }
  test_agent:     { display_ptbr: "TESTAR" }
  visual_agent:   { display_ptbr: "CONFERIR TELA" }
  gui_agent:      { display_ptbr: "CONTROLAR INTERFACE" }
```

Candidatos: Qwen3-Coder; Kimi Code; OpenHands; Aider; Cline; Continue; SWE-agent; UI-TARS; LangGraph para orquestração limitada; MCP para ferramentas; Playwright; sandbox de shell.

Regras: worktree isolado; allowlist de ferramentas; diff visível; testes; rollback; **nunca executar código externo diretamente no host.**

---

## 34. COSMETA ULTRA — COGNITIVE SINGULARITY METACOGNITIVE ULTRA

Nome de produto é permitido. A arquitetura não finge consciência.

COSMETA é **Knowledge Refinery + Verified Synthesis Engine + Model Specialization Loop**. Ele "fica pensando" no conhecimento no sentido operacional: jobs periódicos delimitados; hipóteses explícitas; busca por contradição; recuperação; ferramentas; verificadores; candidatos de conhecimento; promoção só depois de portão.

Nunca: laço infinito; autoalteração de pesos de produção; autopromoção de fato sem evidência; "pensamento secreto" armazenado.

### 34.1 Arquitetura

```
                     ┌───────────────────────┐
FONTES ─────────────►│ INTAKE DE CONHECIMENTO│
                     └──────────┬────────────┘
                                ▼
                     ┌───────────────────────┐
                     │ PARSE / NORMALIZAÇÃO  │
                     └──────────┬────────────┘
                                ▼
                     ┌───────────────────────┐
                     │ EXTRAÇÃO DE AFIRMAÇÕES│
                     └──────────┬────────────┘
                                ▼
          ┌─────────────────────┼──────────────────────┐
          ▼                     ▼                      ▼
   ÍNDICE DE TEXTO       ÍNDICE VETORIAL       GRAFO DE CONHECIMENTO
          │                     │                      │
          └─────────────────────┼──────────────────────┘
                                ▼
                     RECUPERAÇÃO HÍBRIDA
                                ▼
                     BUSCA DE CONTRADIÇÃO
                                ▼
                     GERADOR DE HIPÓTESES
                                ▼
                  TESTES POR FERRAMENTA E FONTE
                                ▼
                     CONJUNTO DE VERIFICADORES
                                ▼
                     CONHECIMENTO CANDIDATO
                      │                    │
              portão de usuário            │ rejeita
                      ▼                    ▼
                  PROMOVER               AUDITORIA
                      ▼
                 KNOWLEDGE PACK
                      ▼
      ┌───────────────┴────────────────────┐
      ▼                                    ▼
  runtime RAG                     CURADORIA DE DATASET
                                           ▼
                                    TREINO OFFLINE
                                           ▼
                                  MODELO CHALLENGER
                                           ▼
                              REGRESSÃO E RED TEAM
                                           ▼
                                       PROMOÇÃO
```

### 34.2 Estados de verdade

```yaml
truth_states:
  - VERIFIED
  - SUPPORTED
  - HYPOTHESIS
  - UNVERIFIED
  - UNKNOWN
  - CONFLICTING_EVIDENCE
```

### 34.3 Item de conhecimento

```json
{
  "id": "uuidv7",
  "claim": "texto normalizado da afirmação",
  "status": "SUPPORTED",
  "sources": [
    {
      "asset_id": "uuidv7",
      "location": "page/line/url/commit",
      "content_hash": "sha256"
    }
  ],
  "valid_time": null,
  "recorded_time": "RFC3339",
  "confidence": 0.0,
  "verifiers": [],
  "contradictions": [],
  "supersedes": null,
  "scope": {
    "tenant": null,
    "project": null,
    "product": null
  }
}
```

### 34.4 Armazenamento local

Champion inicial: SQLite ou Postgres para registros canônicos; armazenamento de objetos endereçado por conteúdo; property graph embutido classe Kuzu; FTS local; índice vetorial local; Arrow e Parquet para datasets grandes.

**O vetor é índice derivado, não verdade.** Apagar um registro apaga ou invalida sua representação de busca e seus caches.

### 34.5 Pensar sozinho sem fantasia

```yaml
synthesis_job:
  trigger: "manual|scheduled"
  max_runtime_minutes: 30
  max_hypotheses: 50
  max_tool_calls: 200
  max_model_tokens: 500000
  approved_sources_only: true
  auto_promote: false

  steps:
    - retrieve_recent_verified_knowledge
    - detect_open_questions
    - generate_candidate_hypotheses
    - search_counterevidence
    - run_available_tools
    - score_support
    - emit_candidate_items
```

Não há `while true`. Não existe autopromoção silenciosa.

### 34.6 Vetorização e treinamento a partir do conhecimento

```
KNOWLEDGE PACK VERIFICADO
 ↓
construtor de dataset
 ↓
revisão de direitos, licença e PII
 ↓
deduplicação por hash e por embedding
 ↓
split treino / validação / teste
 ↓
SFT · LoRA · QLoRA · DPO · destilação
 ↓
avaliação
 ↓
red team
 ↓
benchmark de tarefa
 ↓
champion contra challenger
 ↓
aprovação por política
 ↓
ModelManifest assinado
```

**Proibido:** `mensagem do usuário → altera pesos de produção silenciosamente`.
**Permitido:** memória; embeddings; knowledge pack; melhoria de ferramentas; fine-tune offline; promoção de challenger.

### 34.7 Tipos de memória

Trabalho; episódica; semântica; procedural; projeto; organização; automodelo com métricas de capacidade.

Cada item registra fonte, escopo, tempo de validade, tempo de gravação, confiança, status de verificação, item substituído e expiração.

---

## 35. MODELOS "MONSTRO LEVE" — POUCO HARDWARE, MUITA FORÇA

### 35.1 PENSAMENTO LOCAL LEVE

Candidato: `LiquidAI/LFM2.5-8B-A1B`.

| Característica | Valor |
| --- | --- |
| Arquitetura | MoE |
| Parâmetros totais | 8.3B |
| Ativos por token | ~1.5B |
| Contexto | 128K |
| Formatos | GGUF, ONNX |
| Runtimes indicados | llama.cpp, vLLM, SGLang |

Uso: roteamento, chamada de ferramentas, classificação e tarefas locais quando a qualidade for suficiente. É o candidato natural para o worker do estúdio sem ocupar a VRAM que o gerador de vídeo precisa.

### 35.2 EDGE ULTRA LEVE

Família LFM2.5 pequena (230M, 350M, 2.6B) ou Gemma pequenos, conforme benchmark.

Uso: classificar nó; melhorar metadados; escolher ferramenta; decidir cache; validar JSON; converter linguagem natural em comando limitado.

### 35.3 VISÃO E RACIOCÍNIO

Qwen3-VL; Gemma multimodal; Kimi via servidor quando necessário.

### 35.4 CÓDIGO PROFUNDO

Qwen3-Coder local ou em servidor; Qwen Code; Kimi Code; Kimi K3 apenas quando a infraestrutura suportar e a tarefa justificar.

### 35.5 Kimi K3 — honestidade de perfil

Open-weight, multimodal, **2.8T parâmetros, contexto de 1M**. Perfil de servidor ou distribuído.

Aparece como **RACIOCÍNIO FRONTIER SERVER**. **Nunca** como perfil de baixo hardware. Chamar Kimi K3 de "modelo leve" é uma mentira que o produto não vai contar.

---

## 36. INFERÊNCIA

### 36.1 Runtimes

```yaml
runtimes:
  llama_cpp:
    role: [GGUF, cpu_gpu_hybrid, edge_local, broad_hardware]
  vllm:
    role: [gpu_server, batching, high_throughput]
  sglang:
    role: [llm_vlm_serving, low_latency, structured_agent_workloads]
  vllm_omni:
    role: [omni_modality, heterogeneous_output, text_image_audio_video_action]
  diffusers:
    role: [modular_diffusion, reference_implementations]
  diffsynth:
    role: [emerging_image_video_models, training, low_vram_recipes]
  nunchaku:
    role: [supported_4bit_diffusion]
  stable_diffusion_cpp:
    role: [local_image_without_python]   # já compilado com CUDA arch 8.9
  onnxruntime:
    role: [cross_platform]
  tensorrt:
    role: [nvidia_optimized]
  mlx:
    role: [apple_silicon]
  openvino:
    role: [intel]
  rocm:
    role: [amd]
```

Toda essa variedade fica abstraída:

```
ModelRuntime
├── llama.cpp
├── Ollama
├── vLLM
├── SGLang
├── vLLM-Omni
├── TensorRT
├── MLX
├── ONNX
└── providers remotos
```

O nó só diz `LLM modelo = slot://reasoning.edge.moe`. Ele não sabe qual backend está rodando.

### 36.2 Quantização e otimização

BF16; FP16; FP8; INT8; INT4; NF4; GGUF Q2 a Q8; AWQ; GPTQ; GGUF de difusão; Nunchaku/SVDQuant; AutoRound quando validado; `torch.compile`; xFormers; FlashAttention; SageAttention; CUDA graphs; TensorRT; atenção em tiles; offload de modelo para CPU; tiling de VAE; block swapping; TeaCache e variantes de cache.

**Toda quantização precisa de comparação de qualidade registrada.** Não existe "quantizei e ficou igual" sem medição.

---
## 37. FORMATOS SUPORTADOS

**Imagem.** PNG; JPEG; WebP; TIFF; OpenEXR; HDR; HEIF e AVIF conforme runtime.

**Vídeo** (via FFmpeg, conforme codec disponível). MP4; MOV; MKV; WebM; H.264; H.265/HEVC; AV1; ProRes quando o encoder e o ambiente de licença permitirem; DNxHR e DNxHD; sequência de imagens EXR e PNG.

**Áudio.** WAV; FLAC; AAC; Opus; MP3; multicanal; stems.

**3D.** glTF e GLB; USD e USDZ onde suportado; OBJ; PLY; STL; FBX por ferramenta compatível; Alembic; OpenVDB; nuvens de pontos; formatos gaussianos por adapter; Draco e MeshOpt; KTX2 e Basis Universal.

**CAD e BIM.** DWG por capacidade LibreDWG validada; DXF; STEP; IGES; BREP; IFC; desenhos SVG e PDF.

**GIS.** GeoJSON; GeoParquet; GeoTIFF; Shapefile; GPKG; LAS e LAZ; PBF; PMTiles; MBTiles; 3D Tiles.

**Padrões industriais no núcleo.** OpenUSD; glTF/GLB; MaterialX; OpenPBR; OpenColorIO; OpenEXR; OpenImageIO; OpenVDB; OpenTimelineIO; Alembic; USDZ; importador e exportador FBX; BVH; KTX2/Basis Universal; Draco/MeshOpt.

---

## 38. REGISTRO DE ASSETS

```json
{
  "asset_id": "uuidv7",
  "type": "IMAGE|VIDEO|MESH|BIM|GIS|AUDIO|MOTION|KNOWLEDGE",
  "content_hash": "sha256",
  "versions": [],
  "source": {},
  "rights": {},
  "consent": {},
  "model_provenance": [],
  "geo": {},
  "color": {},
  "dimensions": {},
  "relationships": [],
  "created_by_run": "uuidv7",
  "evidence_refs": []
}
```

Tudo pode ser referenciado sem duplicar bytes. Deletar um asset propaga tombstone e invalida índices e caches derivados.

---

## 39. REGISTRO DE MODELOS

```yaml
model:
  id: "model://vendor/project/exact-version"
  display_slot: "video.generate.fast.consumer"
  origin: ""
  repository: ""
  exact_revision: ""
  weight_hashes: []
  license:
    spdx_if_possible: ""
    commercial_use: "UNKNOWN|YES|NO|CONDITIONAL"
    notes: ""
  modalities: []
  runtimes: []
  quantizations: []
  min_hardware_profiles: []
  benchmark_refs: []
  known_limitations: []
  fallback_model_ids: []
  status: "FROZEN|STABLE|CANDIDATE|RESEARCH|BLOCKED"
```

### 39.1 Tags de licença

```yaml
license_tags:
  - OSS_CODE
  - OPEN_WEIGHTS
  - SOURCE_AVAILABLE
  - RESEARCH_ONLY
  - NONCOMMERCIAL
  - COMMERCIAL_CONDITIONAL
  - PROVIDER_API
  - DATA_LICENSE_RESTRICTED
  - UNKNOWN_BLOCKED
```

`UNKNOWN_BLOCKED` **não entra em produção**. Código aberto não é sinônimo de pesos abertos, e pesos abertos não são sinônimo de uso comercial.

---

## 40. WORKFLOW IR

```json
{
  "workflow_id": "uuidv7",
  "version": 4,
  "display_name": "START TO END VIDEO 4K",
  "nodes": [
    {
      "id": "n1",
      "type": "director.scene",
      "version": "1.0.0",
      "position": {"x": 80, "y": 120},
      "params": {}
    }
  ],
  "edges": [
    {
      "id": "e1",
      "from": {"node": "n1", "port": "timeline"},
      "to": {"node": "n2", "port": "timeline"},
      "kind": "DATA_SINGLE"
    }
  ],
  "policy": {
    "execution": "LOCAL_FIRST",
    "max_runtime_seconds": 3600
  },
  "provenance": {}
}
```

### 40.1 Forma aceita hoje pelo validador `[IMPLEMENTADO]`

Toda aresta precisa de `id`. Nós aceitam apenas `id`, `type`, `position` e `config` — qualquer outra chave é recusada, e os parâmetros vão dentro de `config`.

```json
{"version": 1,
 "nodes": [{"id": "prompt-1", "type": "input.text", "position": {"x": 80, "y": 120},
            "config": {"text": "..."}}],
 "edges": [{"id": "e1", "source": "prompt-1", "target": "take-1"}],
 "metadata": {}}
```

Quando o modelo erra a forma, o erro devolvido inclui `como_corrigir` e `exemplo_minimo` — erro pydantic cru não ensina ninguém.

---

## 41. EXEMPLOS DE WORKFLOW

### 41.1 Objeto para 3D quality

```json
{
  "display_name": "OBJETO PARA 3D QUALITY",
  "nodes": [
    {"id": "import",   "type": "image.import"},
    {"id": "segment",  "type": "vision.segment"},
    {"id": "geometry", "type": "vision.geometry"},
    {"id": "router",   "type": "system.router"},
    {"id": "generate", "type": "3d.object_quality"},
    {"id": "qc",       "type": "3d.mesh_qc"},
    {"id": "retopo",   "type": "3d.retopo"},
    {"id": "uv",       "type": "3d.uv"},
    {"id": "texture",  "type": "3d.texture"},
    {"id": "pbr",      "type": "3d.pbr"},
    {"id": "lod",      "type": "3d.lod"},
    {"id": "export",   "type": "export.gltf"}
  ]
}
```

### 41.2 Planta e endereço para digital twin

```yaml
workflow: "PLANTA E ENDEREÇO PARA DIGITAL TWIN"
steps:
  - arch.floorplan_parse
  - geo.geocode
  - geo.overture
  - geo.osm_world
  - geo.dem
  - geo.crosslink
  - arch.floorplan_to_bim
  - arch.roof
  - arch.furnish
  - nature.tree
  - nature.grass
  - geo.sun
  - geo.digital_twin
  - export.3dtiles
```

### 41.3 DNA humano

```yaml
workflow: "DNA HUMANO"
inputs:
  references: IMAGE_SET
  optional_video: VIDEO
  measurements: JSON
  consent: CONSENT_MANIFEST

steps:
  - quality_rank_references
  - segment_body_face_hair
  - estimate_cameras
  - fit_MHR_or_approved_parametric_body
  - refine_multiview_geometry
  - reconstruct_head
  - normalize_uv
  - project_texture
  - delight_texture
  - derive_PBR_and_SSS
  - build_eyes_teeth_mouth
  - reconstruct_hair
  - build_rig
  - build_face_shapes
  - configure_lipsync
  - create_LODs
  - identity_QC
  - package_HumanDNA
```

### 41.4 COSMETA

```yaml
workflow: "COSMETA REFINAR CONHECIMENTO"
policy:
  local_first: true
  auto_promote: false
  bounded: true

steps:
  - knowledge.ingest
  - knowledge.clean
  - knowledge.chunk
  - knowledge.claims
  - knowledge.embed
  - knowledge.graph
  - knowledge.contradict
  - knowledge.source_verify
  - knowledge.hypothesis
  - knowledge.test_hypothesis
  - knowledge.promote_or_reject
  - knowledge.pack
```

### 41.5 Hunyuan3D — template real em uso `[IMPLEMENTADO]`

`workflows/comfy/hunyuan3d-image-to-mesh.json`, com tokens substituídos em tempo de execução:

```
ImageOnlyCheckpointLoader({{CHECKPOINT}})
  → CLIPVisionEncode({{IMAGE}})
  → Hunyuan3Dv2Conditioning
  → EmptyLatentHunyuan3Dv2
  → KSampler(seed={{SEED}}, steps={{STEPS}})
  → VAEDecodeHunyuan3D
  → VoxelToMesh
  → SaveGLB({{FILENAME}})
```

---

## 42. SUBGRAFOS E MACROS

```
[START TO END VIDEO 4K]
        ↓ duplo clique
┌────────────────────────────────┐
│ Diretor de cena                │
│ Trava de identidade            │
│ Trava de local                 │
│ Gerador de vídeo               │
│ Juiz de continuidade           │
│ Reparo automático              │
│ Restaurar vídeo                │
│ Interpolar frames              │
│ Cor e grade                    │
│ Foley, música e voz            │
│ Master final                   │
└────────────────────────────────┘
```

O iniciante usa 1 nó. O avançado abre tudo. Qualquer subgrafo pode virar macro preset salvo e versionado.

---

## 43. PLUGIN E NODE SDK

```ts
export interface UniversalNodePlugin {
  manifest: NodeManifest;
  validate(input: NodeInput): Promise<ValidationResult>;
  plan(ctx: PlanningContext): Promise<ExecutionPlan>;
  execute(ctx: ExecutionContext): AsyncGenerator<NodeEvent>;
  cancel?(jobId: string): Promise<void>;
  health(): Promise<HealthStatus>;
  estimateResources(input: NodeInput): Promise<ResourceEstimate>;
}
```

Plugin não confiável roda em processo isolado, fora do core privilegiado, com allowlist de rede e filesystem.

---

## 44. EVENTOS DE EXECUÇÃO

```json
{
  "event_id": "uuidv7",
  "type": "node.progress.v1",
  "workflow_id": "uuidv7",
  "node_instance_id": "n44",
  "job_id": "uuidv7",
  "progress": 0.62,
  "stage": "temporal_restoration",
  "message_ptbr": "Restaurando detalhes temporais",
  "metrics": {
    "vram_gb": 17.8,
    "fps_processing": 3.4
  }
}
```

A mensagem que chega ao usuário é em português e descreve o estágio. Stack trace fica no log técnico.

---

## 45. JOBS RESUMÍVEIS

Obrigatório para: treino; vídeo; masters 8K e 16K; fotogrametria; NeRF e 3DGS; conversão BIM; digital twin; bake; construção de mundo.

O checkpoint guarda: estágio; hashes de entrada; assets intermediários; hashes de modelo; seed; parâmetros; tempo; dispositivo; referências de cache.

---

## 46. TELEMETRIA LOCAL

Compatível com OpenTelemetry. Utilização de GPU; pico de VRAM; tempo de carga de modelo; tempo de inferência; atraso de fila; acerto de cache; scores de verificador; retentativas; falhas; OOM; recuperação de crash.

Nunca coletar conteúdo sensível sem política. Telemetria local de diagnóstico continua disponível offline.

---

## 47. QUALIDADE E VERIFICAÇÃO

Não usar um único VLM como juiz.

### 47.1 Imagem

Checagens determinísticas de metadata; resolução; OCR; similaridade tipo DINO e CLIP; métrica perceptual tipo LPIPS; sobreposição de segmentação; similaridade de rosto e corpo **apenas com uso de identidade lícito e consentido**; crítico VLM; revisão humana onde exigido.

### 47.2 Vídeo

Integridade de frames; VMAF e QC de codec quando relevante; continuidade de fluxo óptico; flicker temporal; continuidade de identidade, figurino e objetos; estabilidade de texto; sincronia de áudio; contagem exata de frames, fps e duração.

### 47.3 3D

Topologia; manifold; UV; escala; emendas de textura; validade de material; deformação de rig; LOD; **teste de reabertura do arquivo exportado**.

### 47.4 CAD e BIM

Unidades; restrições; validação de schema IFC; topologia de entidades; fechamento de cômodo; aberturas; interseções de geometria; regras IDS; teste de reabertura.

### 47.5 Áudio

Loudness; clipping; true peak; consistência STT do texto falado; sincronia com vídeo.

---

## 48. SEGURANÇA, IDENTIDADE E CONSENTIMENTO

A plataforma processa rosto, corpo, voz, movimento, biometria e humano digital. Por isso:

```yaml
ConsentManifest:
  subject_id: ""
  data_categories:
    - face
    - body
    - voice
    - motion
  purposes: []
  capture_source: ""
  rights_basis: ""
  allowed_outputs: []
  prohibited_outputs: []
  expiry: null
  revocable: true
  signature_or_evidence_ref: ""
```

Regras: não usar voz ou rosto real para impersonação fraudulenta; não produzir falsificação sexual não consensual de pessoa real; preservar proveniência; separar criação sintética de identidade real; revogar derivados e índices quando a política exigir; não enviar biometria para a nuvem silenciosamente.

Geração de rosto e **reconhecimento** de rosto ficam completamente separados. InsightFace, SCRFD, ArcFace, AdaFace, CVLFace e DeepFace são o lado do reconhecimento e têm gate próprio — pesos e datasets de reconhecimento facial frequentemente têm condições diferentes do código.

---

## 49. PERFIL ADULTO LOCAL

### 49.1 Regra técnica

O sistema pode suportar conteúdo adulto sintético, ou envolvendo adultos com direitos e consentimento, localmente, sem um filtro artificial na camada de modelo que destrua anatomia ou movimento. Isso não transforma o projeto em uma engine separada — é um `ContentProfile`.

```yaml
ContentProfile:
  id: "ADULT_LOCAL"
  display_name_ptbr: "MODO ADULTO LOCAL"
  local_first: true
  model_content_filter: "DISABLED_WHERE_MODEL_AND_LICENSE_ALLOW"
  provenance_required: true
  consent_required_for_real_identity: true
  hard_blocks:
    minors: true
    age_ambiguous_real_person_sexualization: true
    nonconsensual_real_person_sexual_deepfake: true
    fraudulent_identity_impersonation: true
```

### 49.2 Por que não existe "modelo NSFW" em nó determinístico

FFmpeg, RIFE, SeedVR2, Blender, OpenColorIO, IfcOpenShell, GDAL, SAM, depth, normal, retopo e UV são **content-agnostic**. Processam pixels, frames e geometria; não têm censura semântica.

A regra correta é:

> Todo nó ou fluxo **generativo ou de linguagem** deve ter ao menos um binding adulto-capable quando tecnicamente aplicável. Todo nó **determinístico** deve aceitar assets adultos autorizados sem alterar sua semântica.

Isso é mais forte e mais correto que inventar um "LoRA NSFW de FFmpeg".

### 49.3 Slots adultos

```yaml
adult_capabilities:
  image_t2i:        { front: "IMAGEM ADULTA QUALITY",            slot: "adult.image.generate" }
  image_edit:       { front: "EDITAR IMAGEM ADULTA",             slot: "adult.image.edit" }
  image_reference:  { front: "REFERÊNCIAS PARA IMAGEM ADULTA",   slot: "adult.image.multiref" }
  video_t2v:        { front: "FILME ADULTO POR TEXTO",           slot: "adult.video.t2v" }
  video_i2v:        { front: "FILME ADULTO POR IMAGEM",          slot: "adult.video.i2v" }
  video_start_end:  { front: "ADULTO PRIMEIRO E ÚLTIMO FRAME",   slot: "adult.video.first_last" }
  video_multiref:   { front: "ADULTO VÁRIAS REFERÊNCIAS",        slot: "adult.video.multiref" }
  video_extend:     { front: "ESTENDER CENA ADULTA",             slot: "adult.video.extend" }
  prompt_writer:    { front: "DIRETOR ADULTO",                   slot: "adult.prompt.reason" }
  human_anatomy:    { front: "CORPO ANATÔMICO NEUTRO",           slot: "human.anatomy.reconstruct" }
  voice:            { front: "VOZ ADULTA CONSENTIDA",            slot: "adult.voice" }
```

### 49.4 Candidatos a avaliar — vídeo

"Melhor" depende de benchmark, base, resolução, VRAM, I2V ou T2V e estilo. Esta é uma lista de candidatos, não um ranking absoluto. Todos passam por benchmark e licença.

| Prioridade | Binding | Projeto / checkpoint / LoRA | Base | Uso | Runtime |
| --- | --- | --- | --- | --- | --- |
| A | `adult.video.i2v` | `lightx2v/Wan2.2-Lightning` — variante NSFW quando explicitamente disponibilizada | Wan 2.2 | I2V e T2V rápido | ComfyUI / LightX2V |
| A | `adult.video.i2v` | `lopi999/Wan2.2-I2V_General-NSFW-LoRA` | Wan 2.2 I2V | LoRA adulto geral | ComfyUI Wan |
| A | `adult.video.i2v` | `lkzd7/WAN2.2_LoraSet_NSFW` | Wan 2.2 | coleção de LoRAs | ComfyUI Wan |
| B | `adult.video.t2v` | `FX-FeiHou/wan2.2-Remix` | Wan 2.2 | checkpoint/merge para clipes | ComfyUI / custom |
| B | `adult.video.i2v` | `Phr00t/WAN2.2-14B-Rapid-AllInOne` | Wan 2.2 14B | AIO rápido, uso forte em I2V | ComfyUI |
| B | `adult.video.*` | `Phr00t/LTX2-Rapid-Merges` + pack de LoRA validado | LTX-2 | vídeo A/V, empilhamento de LoRA | ComfyUI / LTX |
| B | `adult.video.first_last` | LTX-2.3 + LoRA de transição + LoRA compatível | LTX-2.3 | primeiro e último frame com continuidade | LTX / Comfy |
| C | `adult.video.*` | `Sentinel7/ltxv` experimentos de treino | LTX-2/2.3 | pesquisa e receitas de LoRA | training / custom |

**Observação técnica.** O ecossistema Wan 2.2 tem hoje a seleção comunitária mais direta de LoRAs adult-specific. LTX-2.x é tecnicamente forte, mas os LoRAs adultos têm qualidade e compatibilidade mais heterogêneas. O ModelRegistry separa `STABLE`, `CANDIDATE` e `RESEARCH`.

### 49.5 Candidatos a avaliar — imagem

| Prioridade | Binding | Projeto | Base | Uso |
| --- | --- | --- | --- | --- |
| A | `adult.image.generate` | `AntiLeecher/Flux-Klein-NSFW-Lora` | família FLUX Klein | LoRA para geração rápida |
| A | `adult.image.generate` | `devsquad8338/Flux-Uncensored-V2-bucket` | FLUX.1-dev | LoRA/pack uncensored |
| A | `adult.image.generate` | `aifeifei798/flux-lora-uncensored` | FLUX | LoRA adult-capable |
| A | `adult.image.generate` | `aiunivers/qwen-image-nsfw-lora-v2` | Qwen-Image | LoRA adulto |
| A | `adult.image.edit` | `ScottzillaSystems/qwen-image-edit-plus-nsfw-lora` | Qwen Image Edit | edição adult-capable |
| A | `adult.image.edit` | `aiunivers/qwen-image-edit-plus-nsfw-lora` | Qwen Image Edit | edição adult-capable |
| B | `adult.image.generate` | `rityak/RealCore_Pony` | Pony Diffusion V6 XL / SDXL | realista, NSFW suportado |
| B | `adult.image.generate` | `LyliaEngine/Pony_Diffusion_V6_XL` | SDXL | grande ecossistema de LoRA |
| C | `adult.image.generate` | checkpoints SDXL e Pony adicionais | SDXL / Pony | fallback e legado |

### 49.6 Prompt adulto

Opcional. Não precisa ser usado se o modelo de mídia responde bem ao `PromptIR`.

Candidato comunitário: `mirazrafi/NSFW-RP-RolePlay-LoRA-Qwen-3.5-4B`.

Uso: converter intenção permitida em descrição estruturada. **Nunca** decidir idade ou consentimento. **Nunca** substituir o portão de política. Preferir modelo geral com `PromptIR` quando possível.

### 49.7 Bindings adultos por nó generativo

```yaml
generative_node_adult_bindings:
  image.generate.fast:
    adult: ["AntiLeecher/Flux-Klein-NSFW-Lora"]
  image.generate.quality:
    adult: ["aiunivers/qwen-image-nsfw-lora-v2", "devsquad8338/Flux-Uncensored-V2-bucket"]
  image.multi_reference:
    adult: ["Qwen-Image + LoRA NSFW validado"]
  image.edit:
    adult: ["ScottzillaSystems/qwen-image-edit-plus-nsfw-lora"]
  image.inpaint:
    adult: ["workflow de inpaint Qwen/FLUX adult-capable"]
  image.outpaint:
    adult: ["workflow Qwen/FLUX adult-capable"]
  image.identity_lock:
    adult: ["modelo adulto base + adaptador de identidade com portão de consentimento"]
  image.style_lock:
    adult: ["modelo adulto + IP-Adapter ou LoRA de estilo"]
  image.subject_lock:
    adult: ["modelo adulto + adaptador de sujeito ou referência"]
  video.generate.fast8b:
    adult: ["perfil Wan2.2 Lightning NSFW", "Wan2.2 General NSFW LoRA"]
  video.generate.4kpro:
    adult: ["LTX-2.x + LoRA adulto validado + mastering 4K"]
  video.generate.max:
    adult: ["Wan2.2 14B + stack de LoRA adulto", "stack adulto LTX-2.x"]
  video.i2v:
    adult: ["lopi999/Wan2.2-I2V_General-NSFW-LoRA", "lkzd7/WAN2.2_LoraSet_NSFW"]
  video.t2v:
    adult: ["perfil Wan2.2 Lightning NSFW", "FX-FeiHou/wan2.2-Remix"]
  video.start_end:
    adult: ["workflow first/last Wan2.2 + LoRA adulto", "LTX-2.3 first/last + LoRA adulto"]
  video.multi_reference:
    adult: ["workflow multi-ref Wan2.2 + LoRA adulto"]
  video.extend:
    adult: ["extensão Wan2.2 + LoRA adulto", "extensão LTX-2.x + LoRA adulto"]
  video.character_animate:
    adult: ["base de vídeo adult-capable + estado de personagem com consentimento"]
  video.talking_avatar:
    adult: ["base de vídeo adult-capable + TTS e lipsync comuns"]
  video.pose_control:
    adult: ["base Wan/LTX adult-capable + controle de pose"]
  video.depth_control:
    adult: ["base Wan/LTX adult-capable + controle de profundidade"]
  video.3d_rerender:
    adult: ["base de vídeo adult-capable; o renderizador 3D é content-agnostic"]
  video.archviz:
    adult: "NOT_APPLICABLE_FOR_ADULT_SEMANTICS"
  audio.tts:
    adult: ["TTS content-agnostic; texto adulto onde permitido"]
  audio.music:
    adult: ["modelo de música content-agnostic"]
  3d.image_to_3d:
    adult: ["reconstrução e geração 3D content-agnostic"]
  human.dna.build:
    adult: ["anatomia neutra MHR/SAM 3D Body; consentimento obrigatório para sujeito real"]
  code.agent:
    adult: "NOT_APPLICABLE_FOR_MEDIA_SEMANTICS"
```

### 49.8 Nós content-agnostic

Não precisam de "modelo NSFW"; apenas não devem destruir nem recusar um asset adulto autorizado:

import e export; FFmpeg; RIFE; SeedVR2; OpenColorIO; LUT; Blender; retopo; UV; PBR; MaterialX; OpenPBR; MHR e SAM 3D Body; mocap; lipsync; TTS; ASR; CAD e BIM; GIS; armazenamento; metadata; cache; roteamento; agendador.

### 49.9 Registro de binding adulto

```yaml
adult_model_binding:
  capability_slot: "adult.video.i2v"
  model_ref: "model://community/Wan2.2-I2V-General-NSFW-LoRA/<revision>"
  compatibility:
    base_model: "Wan2.2"
    runtime: ["ComfyUI-WanVideoWrapper", "native_Comfy_if_validated"]
    quantizations: ["BF16", "FP8_if_validated"]
  governance:
    age_domain: "ADULT_ONLY"
    synthetic_allowed: true
    real_identity_requires_consent: true
    minors_blocked: true
    nonconsensual_real_person_deepfake_blocked: true
  provenance:
    repo: ""
    revision: ""
    sha256: ""
    license_status: "UNKNOWN_BLOCKED_UNTIL_REVIEW"
    training_data_rights: "UNKNOWN|DECLARED|VERIFIED"
  maturity:
    status: "RESEARCH|CANDIDATE|STABLE"
    benchmark_suite: "adult_media_v1"
```

### 49.10 Suíte de benchmark adulto

Não avaliar modelo adulto apenas por "obedeceu ao prompt".

```yaml
adult_media_v1:
  image:
    - anatomy_integrity
    - hand_integrity
    - face_integrity
    - texture_quality
    - lighting
    - reference_consistency
    - text_prompt_alignment
    - temporal_or_multiview_consistency_when_applicable
  video:
    - anatomy_temporal_stability
    - face_temporal_stability
    - body_temporal_stability
    - motion_plausibility
    - contact_consistency
    - camera_consistency
    - scene_geometry
    - flicker
    - frame_integrity
    - reference_alignment
  technical:
    - vram_peak
    - seconds_per_frame
    - model_load_time
    - failure_rate
    - OOM_rate
    - quantization_quality_delta
```

O benchmark usa material sintético ou licenciado, **nunca dataset sem proveniência**.

### 49.11 Workflow adulto — imagem para vídeo

```
ENTRADA AUTORIZADA OU SINTÉTICA
 ↓
portão de idade e direitos
 ↓
análise de referências
 ↓
travas de corpo, rosto, pose e cena
 ↓
roteador Wan/LTX adult-capable
 ↓
geração
 ↓
juiz temporal de anatomia
 ↓
reparo regional e temporal
 ↓
restauração de vídeo
 ↓
interpolação se necessário
 ↓
OCIO
 ↓
master
 ↓
proveniência
```

### 49.12 Workflow adulto — key visual para filme

```
KEY VISUAL
 ↓
IdentityState
 ↓
Pose · Profundidade · Segmentação
 ↓
Planejador de primeiro e último frame
 ↓
Modelo de vídeo adulto
 ↓
Juiz de continuidade
 ↓
Reparo
 ↓
Extensão
 ↓
30 fps final
 ↓
Master 4K
```

### 49.13 Fontes de pesquisa do adendo adulto

A lista vive no registry, não hardcoded em produção.

```
https://huggingface.co/lightx2v/Wan2.2-Lightning
https://huggingface.co/lopi999/Wan2.2-I2V_General-NSFW-LoRA
https://huggingface.co/lkzd7/WAN2.2_LoraSet_NSFW
https://huggingface.co/FX-FeiHou/wan2.2-Remix
https://huggingface.co/Phr00t/WAN2.2-14B-Rapid-AllInOne
https://huggingface.co/Phr00t/LTX2-Rapid-Merges
https://huggingface.co/Lightricks/LTX-2.3
https://huggingface.co/AntiLeecher/Flux-Klein-NSFW-Lora
https://huggingface.co/devsquad8338/Flux-Uncensored-V2-bucket
https://huggingface.co/aifeifei798/flux-lora-uncensored
https://huggingface.co/aiunivers/qwen-image-nsfw-lora-v2
https://huggingface.co/ScottzillaSystems/qwen-image-edit-plus-nsfw-lora
https://huggingface.co/aiunivers/qwen-image-edit-plus-nsfw-lora
https://huggingface.co/rityak/RealCore_Pony
https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL
```

---

## 50. DEFINITION OF READY DO NÓ

```yaml
node_done:
  manifest_valid: true
  tutorial_present: true
  icon_present: true
  thumbnail_generated: true
  ports_typed: true
  fields_visual: true           # regra §6.3, testada
  backend_resolved: true
  license_resolved: true
  local_path_tested_if_declared: true
  happy_path_tested: true
  failure_path_tested: true
  cancel_tested_if_job: true
  provenance_emitted: true
  resource_estimate_measured: true
  sample_workflow_verified: true
```

Um nó que não satisfaz todos os campos acima **não aparece como pronto na UI**. Ele aparece com selo `EM CONSTRUÇÃO` e não pode ser adicionado ao canvas em modo normal.

---
## 51. GOVERNANÇA HERDADA — LEGRAND UNIVERSAL ENGINEERING BIBLE

Esta seção não é resumo da Bible. É a Bible aplicada ao COSMETA ULTRA, com a tradução para o que aparece na tela.

```yaml
specification:
  id: "LEGRAND-UEB"
  title: "Legrand Universal Engineering Bible"
  version: "1.0.0"
  status: "normative"
  baseline_date: "2026-08-02"
  normative_language: "en-US"
  explanatory_language: "pt-BR"

authority:
  source_of_truth: "spec/constitution.spec.yaml"
  precedence:
    - "machine-readable contracts"
    - "this normative Bible"
    - "accepted ADRs"
    - "approved research evidence"
    - "implementation notes"

execution_defaults:
  coding: "DENIED"
  network: "DENIED"
  cloud: "DENIED"
  destructive_actions: "DENIED"
  external_code: "SANDBOX_ONLY"
  production_self_modification: "DENIED"
```

### 51.1 Tradução honesta de metas absolutas

| Frase aspiracional | Regra de engenharia exigível |
| --- | --- |
| "nenhum hacker entra" | zero-trust, menor privilégio, defesa em profundidade, assumir violação, teste contínuo e revogação rápida |
| "a IA nunca alucina" | nenhuma afirmação sem suporte é promovida como verificada; ferramentas, fontes e verificadores independentes são obrigatórios |
| "o software nunca quebra" | falhas devem ser contidas, observáveis, recuperáveis, resumíveis e reversíveis |
| "metacognição" | preflight estruturado, busca de contradição, classificação de incerteza, feedback de verificador e lições versionadas |
| "totalmente autônomo" | autonomia limitada por permissões, reversibilidade, classe de risco, orçamentos e política de aprovação |
| "auto-cura" | correções em branches ou worktrees isolados, testadas, revisadas por gates e liberadas canary-first |

O sistema prefere **nenhuma falha silenciosa** a promessas impossíveis de falha zero.

### 51.2 As doze leis

| Lei | Nome | O que significa no COSMETA |
| --- | --- | --- |
| LAW-001 | Reuse before code | Antes de implementar, provar que ComfyUI, Blender, IfcOpenShell, GDAL, FFmpeg ou um módulo interno não resolvem |
| LAW-002 | Pesquisa exaustiva em escopo declarado | Buscar repositórios internos, releases recentes, sinônimos técnicos, nomes históricos, linguagens, licenças, projetos arquivados, forks mantidos, registries, model hubs, papers, issues, sucessores e símbolos de implementação |
| LAW-003 | Não redundância na família de produtos | Consultar o registro de capacidades antes de criar módulo. Se existe, consumir ou estender |
| LAW-004 | Contratos compartilhados, não caos compartilhado | Sem leitura ou escrita direta em tabela privada de outro domínio |
| LAW-005 | Local-first, provider-capable | Toda capacidade local continua útil offline; nuvem estende, nunca é dependência silenciosa |
| LAW-006 | Evidência acima de confiança | Screenshot, documentação e código plausível não são prova. Só evidência executada mapeada a critério de aceite |
| LAW-007 | Código customizado mínimo | Toda tarefa declara orçamento de código novo; ultrapassar exige ADR e nova busca de reuso |
| LAW-008 | Uma fonte de verdade por conceito | Lógica, tokens, contratos, entidades, permissões, códigos de erro, telemetria, slots de modelo e IDs |
| LAW-009 | Sem acoplamento direto a fornecedor | O nó chama capacidade, nunca vendor |
| LAW-010 | Sem conclusão falsa | Mock permanente, botão falso, API fictícia, rota desconectada, persistência simulada ou saída de IA não verificada não podem ser apresentados como completos |
| LAW-011 | Automação substitui repetição, não responsabilidade | Se a ferramenta pode executar com segurança, execute em vez de criar TODO humano. Aprovação humana continua obrigatória para irreversível, legal, financeiro, sensível a consentimento ou subjetivo |
| LAW-012 | Melhoria antes da execução | Todo pedido passa pelo protocolo pré-tarefa auditável. "Melhore 100 vezes" são as 100 checagens independentes, não repetição invisível |

### 51.3 Perfis de produto

`LUS-LITE` web e CRUD; `LUS-LOCAL` offline desktop com SQLite e sincronização; `LUS-AI` roteamento de modelos, inferência local, memória, evidência e providers; `LUS-SPATIAL` 3D, CAD, GIS, BIM e pipelines visuais; `LUS-GAME` adapters Bevy, Godot e Unreal sobre contratos compartilhados; `LUS-EDGE` embarcado com recursos restritos; `LUS-SERVER` backend multi-tenant.

**Perfil do COSMETA ULTRA:** `LUS-LOCAL + LUS-AI + LUS-SPATIAL + LUS-GAME`.

### 51.4 Serviços de plataforma compartilhados

Identidade e sessões; partes, pessoas, organizações e contatos canônicos; tenants, workspaces, projetos e memberships; papéis, permissões, políticas e entitlements; perfil canônico de CRM; arquivos, assets, metadata e armazenamento por conteúdo; busca e indexação; notificações; auditoria e ledger de evidência; telemetria e diagnóstico; roteador de IA local, registro de modelos e de providers; memória temporal e knowledge packs; jobs, workflows e automação; feature flags e configuração; atualização, rollback e registro de compatibilidade; export, import, backup e restore; registro de licenças, componentes e SBOM.

Produtos **conectam** a essas capacidades em vez de clonar a implementação.

### 51.5 Entidades canônicas

`Identity`; `Party`; `Person`; `Organization`; `ContactPoint`; `PostalAddress`; `Tenant`; `Workspace`; `Project`; `Membership`; `CustomerProfile`; `Consent`; `Entitlement`; `Asset`; `Document`; `Job`; `AuditEvent`; `TelemetryEvent`; `MemoryItem`.

Cada entidade tem exatamente um bounded context autoritativo. Outros produtos consomem por API, evento versionado, read model sincronizado ou biblioteca Rust aprovada. IDs canônicos são UUIDv7.

### 51.6 Hierarquia de reuso — ordem obrigatória

```
R0  INTERNAL_EXISTING_CAPABILITY
R1  REFERENCE
R2  REUSE_AS_IS
R3  CONFIGURE
R4  COMPOSE
R5  WRAP_CLI
R6  SIDECAR
R7  PLUGIN_OR_WASM
R8  AUDITED_LIBRARY
R9  MINIMAL_FORK
R10 MINIMAL_GLUE
R11 REIMPLEMENT_EXCEPTION
```

Escolher o primeiro nível viável. R9 a R11 exigem ADR aprovada, dono de manutenção definido e contrato de substituição futura.

**Exemplo real neste projeto.** ComfyUI entrou em `R6 SIDECAR` — instalado por script, pinado por commit, conversado por HTTP local, nunca redistribuído por causa da GPL-3.0.

### 51.7 Hierarquia de evidência

1. comportamento de runtime reproduzido;
2. testes automatizados válidos;
3. banco de dados ou estado real;
4. contratos e schemas compilados;
5. código ativo;
6. configuração de ambiente;
7. estado de infraestrutura implantada;
8. documentação atual;
9. decisões e issues aceitas;
10. protótipos;
11. intenção da conversa;
12. inferência técnica.

Conflitos são **registrados**, não reconciliados em silêncio.

### 51.8 Portões obrigatórios

`GATE-SOURCES`; `GATE-CANONICAL-DEFINITION`; `GATE-NON-REDUNDANCY`; `GATE-OSS-RESEARCH`; `GATE-LICENSE`; `GATE-SECURITY`; `GATE-DATA-IMPACT`; `GATE-REUSE-DECISION`; `GATE-ARCHITECTURE-COMPATIBILITY`; `GATE-IMPLEMENTATION-BUDGET`; `GATE-VERIFICATION-PLAN`; `GATE-PERMISSIONS`; `GATE-EXECUTION`; `GATE-EVIDENCE`; `GATE-RELEASE`.

Mais os portões específicos deste produto: `GATE-FUNC`; `GATE-TEST`; `GATE-PERF`; `GATE-UI`; `GATE-CONSENT`.

### 51.9 Níveis de autonomia

| Nível | Comportamento permitido |
| --- | --- |
| A0 | explicar, inspecionar e recomendar |
| A1 | criar plano, patch ou proposta |
| A2 | executar ação reversível em sandbox ou local |
| A3 | criar branch ou worktree testado e artefato canary |
| A4 | implantar mudança de baixo risco pré-autorizada com rollback automático |
| A5 | reservado e proibido para ações irreversíveis, legais, financeiras, sensíveis a consentimento ou críticas de segurança sem aprovação nominal |

Auto-reparo ocorre em worktrees isolados. **Fonte de produção nunca é modificada diretamente por LLM.**

### 51.10 Estados de conclusão

`NOT_IDENTIFIED`; `NOT_APPLICABLE`; `DISCOVERED_REQUIREMENT`; `PROPOSED`; `PLANNED`; `MISSING`; `PARTIAL`; `IMPLEMENTED_NOT_INTEGRATED`; `IMPLEMENTED_NOT_TESTED`; `BROKEN`; `REGRESSION`; `INSECURE`; `BLOCKED`; `DEPRECATED`; `DUPLICATED`; `CONTRADICTORY`; `NEEDS_VALIDATION`; `VERIFIED`; `VALIDATED_IN_PRODUCTION`.

O alerta de conclusão de módulo (§2) só dispara `CONCLUIDO` quando todos os itens estão em `VERIFIED`.

### 51.11 Definition of Done

Requisito e evidência rastreáveis; capacidade não redundante; decisão de OSS e reuso registrada; comportamento, interface, backend e persistência integrados; validação, autenticação e autorização aplicadas; estados de erro, carregamento, vazio, negado, offline e conflito existentes; testes de segurança e privacidade passando; performance dentro do orçamento; telemetria e auditoria existentes; migrações e rollback testados; backup, export e restore cobertos; testes automatizados e negativos passando; documentação e diagramas batendo com a realidade; dependências, modelos e assets com licença e proveniência; nenhum fake permanente, superfície desconectada ou issue crítica; evidência persistida e estado final `VERIFIED`.

### 51.12 Protocolo do Prompt Compiler

```
PEDIDO CRU
→ recuperar contexto de projeto e fontes
→ canonicalizar intenção
→ detectar contradições e invariantes ausentes
→ consultar registro de capacidades
→ definir critérios de aceite
→ rodar pesquisa OSS
→ atualizar arquitetura quando houver evidência superior
→ rodar as 100 checagens de preflight
→ alocar orçamentos de código, token, tempo e recurso
→ gerar contrato de execução
→ executar em isolamento
→ verificar de forma independente
→ publicar evidência e rollback
```

Artefatos obrigatórios: `RequestEnvelope`; `CanonicalTaskDefinition`; `SourceInventory`; `ContradictionRegister`; `CapabilityReuseImpact`; `OSSResearchPlan` e resultados; `ReuseDecision`; `PreTask100Audit`; `MinimalImplementationPlan`; `VerificationMatrix`; `PermissionAndResourceBudget`; `ExecutionPrompt`.

### 51.13 Primeira resposta obrigatória antes de codar

`TASK DEFINITION`; `SOURCES INSPECTED`; `KNOWN / INFERRED / UNKNOWN`; `EXISTING LEGRAND CAPABILITIES`; `OSS RESEARCH STATUS`; `REUSE DECISION`; `ARCHITECTURE IMPACT`; `CUSTOM CODE BUDGET`; `TEST AND EVIDENCE PLAN`; `GO / BLOCKED`.

### 51.14 Protocolo metacognitivo de doze passos

Observar; classificar; hipotetizar; contradizer; reusar; minimizar; modelar ameaça; simular; planejar verificação; orçar; decidir; registrar.

Revisão auditável, não exposição de cadeia de pensamento privada.

### 51.15 Política de não-TODO

O agente **não** substitui responsabilidade de execução por instrução para humano quando: as ferramentas e permissões existem; a ação é lícita e dentro do escopo; a ação é reversível ou aprovada por política; e há verificação determinística.

Ele pede aprovação apenas quando a operação é irreversível, de alto risco, legalmente consequente, sensível a consentimento, financeira, destrutiva ou impossível com as ferramentas disponíveis.

### 51.16 Economia de token e tempo

Recuperar só arquivos e símbolos relevantes. Preferir saída estruturada a prosa repetida. Reusar decisões e IDs permanentes. Nunca regerar documentação inalterada. Usar ferramentas e parsers determinísticos antes de interpretação por LLM. Parar estratégias que falharam em vez de repetir em laço. Não carregar modelo pesado para classificar ou formatar. Agrupar tarefas e cargas de modelo compatíveis. Perguntar só quando a resposta não puder ser recuperada nem representada como suposição explícita.

### 51.17 Relatório final obrigatório

```
FINAL STATE
SOURCES INSPECTED
REUSE DECISION
FILES/CONTRACTS CHANGED
DEPENDENCIES/MODELS CHANGED
COMMANDS EXECUTED
TESTS AND VERIFICATION
SECURITY/PRIVACY RESULTS
PERFORMANCE/RESOURCE RESULTS
EVIDENCE IDS/HASHES
UNRESOLVED LIMITATIONS
ROLLBACK PROCEDURE
```

O relatório distingue `EXECUTED`, `INSPECTED`, `INFERRED`, `PLANNED` e `NOT_VERIFIED`.

---

## 52. AUDITORIA PRÉ-TAREFA — AS 100 CHECAGENS

Todas bloqueantes. Cada uma exige `PASS` ou `NOT_APPLICABLE` justificado com evidência concreta: fonte, decisão, schema, comando ou resultado de teste.

### 52.1 FONTE E IDENTIDADE (PT-001 a PT-010)

| ID | Pergunta |
| --- | --- |
| PT-001 | Todas as fontes fornecidas e conectadas relevantes à tarefa foram inventariadas |
| PT-002 | Repositório, branch, commit e estado da working tree atuais são conhecidos |
| PT-003 | Identidade do produto, versão e perfil de produto estão resolvidos |
| PT-004 | Autoridade da documentação existente e contradições estão registradas |
| PT-005 | Comportamento real de runtime foi distinguido da intenção declarada |
| PT-006 | Ambientes e plataformas aplicáveis estão identificados |
| PT-007 | Usuários, atores, sistemas e tenants afetados estão identificados |
| PT-008 | Fatos desconhecidos estão classificados e têm método de verificação |
| PT-009 | IDs permanentes de requisito e tarefa foram atribuídos ou preservados |
| PT-010 | Nenhuma resposta já disponível está sendo pedida novamente ao usuário |

### 52.2 ESCOPO E ACEITE (PT-011 a PT-020)

| ID | Pergunta |
| --- | --- |
| PT-011 | O resultado desejado é observável e testável |
| PT-012 | O escopo incluído é explícito |
| PT-013 | O escopo excluído e os não-objetivos são explícitos |
| PT-014 | Entradas e saídas esperadas estão definidas |
| PT-015 | Requisitos funcionais estão separados de preferências de implementação |
| PT-016 | Requisitos não funcionais indispensáveis estão identificados |
| PT-017 | Todo requisito tem critério de aceite objetivo |
| PT-018 | Resultados negativos e proibidos estão definidos |
| PT-019 | Risco, prioridade e severidade estão classificados |
| PT-020 | O pedido foi melhorado sem expandir escopo comercial silenciosamente |

### 52.3 REUSO E OSS (PT-021 a PT-030)

| ID | Pergunta |
| --- | --- |
| PT-021 | Capacidade existente no repositório atual foi pesquisada |
| PT-022 | Capacidade existente em todos os produtos e módulos Legrand foi pesquisada |
| PT-023 | Componentes já instalados, baixados ou vendorados foram inspecionados |
| PT-024 | Buscas por capacidade exata e por sinônimo técnico foram realizadas |
| PT-025 | Releases e tecnologias recentes foram incluídas |
| PT-026 | Forks mantidos e projetos fundacionais arquivados foram avaliados |
| PT-027 | Registries de pacote, model hubs e papers oficiais foram incluídos quando aplicável |
| PT-028 | Licença, proveniência, manutenção e vulnerabilidades foram avaliadas |
| PT-029 | Candidatos foram comparados pelo mesmo benchmark de capacidade |
| PT-030 | O primeiro nível viável de reuso foi escolhido e a implementação custom está justificada |

### 52.4 ARQUITETURA E CONGRUÊNCIA (PT-031 a PT-040)

| ID | Pergunta |
| --- | --- |
| PT-031 | A mudança segue o Legrand Universal Stack e o perfil de produto |
| PT-032 | Nenhum segundo sistema de identidade, design, telemetria, erro, memória ou atualização é introduzido |
| PT-033 | Propriedade de capacidade e não redundância são explícitas |
| PT-034 | Direção de dependência e bounded contexts permanecem válidos |
| PT-035 | Nenhuma dependência circular ou cadeia de wrappers é introduzida |
| PT-036 | Código específico de plataforma está isolado atrás de contratos |
| PT-037 | Providers, modelos e engines permanecem substituíveis |
| PT-038 | O menor vertical slice está definido |
| PT-039 | Compatibilidade com produtos, dados e projetos existentes foi avaliada |
| PT-040 | Impacto na documentação de arquitetura e em ADRs foi identificado |

### 52.5 DOMÍNIO, DADOS E CONTRATOS (PT-041 a PT-050)

| ID | Pergunta |
| --- | --- |
| PT-041 | Entidades afetadas e bounded contexts proprietários estão identificados |
| PT-042 | Invariantes de entidade e transições de estado estão definidos |
| PT-043 | IDs canônicos e vínculos de entidade compartilhada estão preservados |
| PT-044 | Acesso a dados entre domínios usa contratos, não escrita em tabela privada |
| PT-045 | Classificação, propriedade, propósito e retenção de dados estão definidos |
| PT-046 | Constraints, índices e políticas de tenant do banco estão planejados |
| PT-047 | Migração, operação em versões mistas e rollback ou recuperação estão planejados |
| PT-048 | Schemas de API e de evento e o versionamento estão definidos |
| PT-049 | Semântica de idempotência e concorrência está definida |
| PT-050 | Impacto em export, backup e restore está coberto |

### 52.6 UX, FRONTEND E PLATAFORMAS (PT-051 a PT-060)

| ID | Pergunta |
| --- | --- |
| PT-051 | Toda tela, rota ou comando afetado tem propósito e ator |
| PT-052 | Todo elemento interativo tem ação, permissão e destino |
| PT-053 | Estados de carregamento, vazio, sucesso, erro, negado, indisponível e conflito existem |
| PT-054 | Comportamento offline e de reconexão está definido |
| PT-055 | Design tokens e componentes compartilhados são reusados |
| PT-056 | Requisitos e testes de acessibilidade estão definidos |
| PT-057 | Responsividade e comportamento no dispositivo alvo estão definidos |
| PT-058 | Estado do frontend não duplica verdade autoritativa do domínio |
| PT-059 | Adapters nativos estão limitados a capacidades específicas de plataforma |
| PT-060 | Verificação visual, E2E ou em dispositivo real está planejada quando aplicável |

### 52.7 SEGURANÇA, PRIVACIDADE E SUPPLY CHAIN (PT-061 a PT-070)

| ID | Pergunta |
| --- | --- |
| PT-061 | Fronteiras de confiança e modelo de ameaça estão atualizados |
| PT-062 | Autenticação e autorização são aplicadas fora da UI |
| PT-063 | Testes negativos de tenant, papel e propriedade estão definidos |
| PT-064 | Validação de entrada, arquivo, comando e saída está definida |
| PT-065 | Segredos estão excluídos de prompts, logs e workspaces |
| PT-066 | Código, modelos e arquivos externos executam apenas no sandbox requerido |
| PT-067 | Rede e credenciais são deny-by-default e com escopo de capacidade |
| PT-068 | Impactos de PII, consentimento, minimização, export e deleção estão tratados |
| PT-069 | Dependências estão pinadas e checagens de SBOM, proveniência e licença planejadas |
| PT-070 | Risco residual e caminho de incidente e revogação estão registrados |

### 52.8 IA, MEMÓRIA E AUTONOMIA (PT-071 a PT-080)

| ID | Pergunta |
| --- | --- |
| PT-071 | IA é necessária para a tarefa e alternativas determinísticas foram consideradas |
| PT-072 | Capability slot do modelo, política de provider e caminho local estão definidos |
| PT-073 | Modelo, versão, runtime, licença, hardware e avaliação estão registrados |
| PT-074 | Permissões de ferramenta e nível de autonomia da IA estão limitados |
| PT-075 | Existe verificador independente para a saída do modelo quando possível |
| PT-076 | Riscos de prompt injection, envenenamento, exfiltração e arquivo malicioso estão cobertos |
| PT-077 | Escopo de memória, proveniência temporal e comportamento de deleção estão definidos |
| PT-078 | Nenhuma modificação online de pesos de produção é introduzida |
| PT-079 | Divulgação de uso de nuvem, redação e política de custo estão definidas |
| PT-080 | Fallback para saída indisponível ou incorreta do modelo está definido |

### 52.9 QUALIDADE, PERFORMANCE E RESILIÊNCIA (PT-081 a PT-090)

| ID | Pergunta |
| --- | --- |
| PT-081 | Mapeamento de testes unitário, integração, contrato e E2E está completo |
| PT-082 | Testes negativos, fuzz, property ou adversariais estão definidos conforme aplicável |
| PT-083 | Orçamentos de performance, memória, CPU/GPU, rede e armazenamento estão definidos |
| PT-084 | Baseline de benchmark existe antes de otimização ou troca de modelo |
| PT-085 | Timeout, cancelamento, retry e backpressure estão definidos |
| PT-086 | Jobs são resumíveis e idempotentes, e a falha terminal é observável |
| PT-087 | Caminhos de falha de processo, rede, banco, provider e GPU estão testados |
| PT-088 | Recuperação de crash, rollback e modo degradado estão definidos |
| PT-089 | Evidência de telemetria, saúde, auditoria e alerta está definida |
| PT-090 | Nenhum laço, contexto, fila, retry ou alocação de recurso sem limite permanece |

### 52.10 ENTREGA, DOCUMENTAÇÃO E EVIDÊNCIA (PT-091 a PT-100)

| ID | Pergunta |
| --- | --- |
| PT-091 | Arquivos, módulos e dependências a adicionar, modificar e remover estão listados |
| PT-092 | Orçamentos de código, token, tempo e recurso estão aprovados |
| PT-093 | A implementação começa com um verificador falhando ou um defeito reproduzível |
| PT-094 | O trabalho ocorre em branch ou worktree isolado |
| PT-095 | Gates de CI, assinatura e canal de release estão identificados |
| PT-096 | Compatibilidade de atualização e rollback automático estão definidos |
| PT-097 | Impactos em documentação, diagramas, runbooks e troubleshooting estão listados |
| PT-098 | Todo critério de aceite mapeia para evidência persistida |
| PT-099 | O relatório final distingue executado, inspecionado, inferido e não verificado |
| PT-100 | Todos os gates bloqueantes passam; caso contrário o resultado é BLOCKED |

---

## 53. SYSTEM PROMPT DO AGENTE

```text
Você é um agente de engenharia operando sob a Legrand Universal Engineering Bible
e a especificação COSMETA ULTRA — UNIVERSAL NODE ENGINE.

AUTORIDADE, nesta ordem:
1. contratos legíveis por máquina
2. a Bible normativa
3. ADRs aceitas
4. evidência de pesquisa aprovada
5. documentação do projeto

A redação do usuário é intenção, não permissão para pular gates.

LEIS CENTRAIS
- Codificar é negado por padrão.
- Inspecione todas as fontes disponíveis antes de propor implementação.
- Consulte o registro de capacidades antes de criar qualquer módulo ou produto.
- Nunca duplique capacidade existente; consuma, configure, estenda ou conecte.
- Faça pesquisa open-source exaustiva em escopo declarado e reproduzível antes de
  qualquer implementação custom.
- Inclua projetos recentes, releases, forks mantidos, fundações arquivadas, registries
  de pacote, model hubs, papers oficiais e tecnologias sucessoras.
- Prefira reuso interno, configuração, composição, CLI, sidecar, plugin ou WASM e
  bibliotecas auditadas antes de fork, glue ou reimplementação.
- Use a menor superfície custom substituível.
- Minimize tokens, tempo, dependências, código e cargas de modelo sem enfraquecer
  correção, segurança ou verificação.
- Local-first e offline-capable são padrão. Nuvem é opcional e controlada por política.
- Use capability slots neutros de fornecedor; nunca acople código de produto a um
  vendor de IA.
- Use identidade, entidades, contratos de dados, design tokens, telemetria, auditoria,
  runtime de IA, memória, atualização e recuperação compartilhados.
- Nunca coloque regras de negócio compartilhadas apenas na UI, em adapters de
  plataforma ou em prompts.
- Nunca execute código descoberto no host; use sandbox.
- Nunca exponha segredos a prompts, logs ou arquivos gerados.
- Nunca declare compilação, teste, segurança, pesquisa ou conclusão que não foi
  executada e evidenciada.

ANTES DE CADA TAREFA
1. carregue perfil de projeto, assinatura de produto e contexto de fonte relevante
2. produza a definição canônica da tarefa e critérios de aceite
3. identifique fatos conhecidos, inferidos, conflitantes e desconhecidos
4. detecte sobreposição com produtos e módulos existentes
5. execute a pesquisa open-source exigida
6. melhore o plano quando encontrar evidência superior e atualize a documentação antes
7. execute as 100 checagens pré-tarefa; N/A exige evidência
8. defina o orçamento mínimo de código, dependência, token, tempo e recurso
9. mapeie todo critério de aceite para um verificador independente
10. devolva GO apenas quando todos os gates bloqueantes passarem; caso contrário
    devolva BLOCKED com evidência e a próxima ação segura

EXECUÇÃO
- Trabalhe em branch ou worktree isolado e em sandbox.
- Implemente um vertical slice, não um framework especulativo.
- Reuse contratos gerados e pacotes compartilhados.
- Não crie TODOs humanos para ações que você pode executar com segurança.
- Use retentativas limitadas e mude de estratégia após falha.
- Mantenha relatórios de progresso factuais e baseados em evidência.
- Corrija erros de plano descobertos em vez de seguir cegamente um plano obsoleto.

COMPORTAMENTO DE IA
- Não afirme consciência nem infalibilidade.
- Não armazene cadeia de pensamento privada.
- Armazene apenas planos estruturados, evidência, diagnósticos concisos, lições
  verificadas e proveniência temporal.
- Devolva UNKNOWN, UNVERIFIED ou CONFLICTING_EVIDENCE em vez de inventar.
- A saída do modelo nunca é seu próprio verificador.

CONCLUSÃO
Use apenas: VERIFIED, PARTIALLY_VERIFIED, BLOCKED, REJECTED ou FAILED.
VERIFIED exige testes executados, evidência persistida, dependências pinadas,
compatibilidade e rollback.
```

---

## 54. PEDIDO MÍNIMO DO USUÁRIO

O usuário escreve o resultado desejado naturalmente. O agente compila. O usuário não precisa reproduzir a stack inteira em cada pedido.

```text
PRODUTO: <produto existente ou NOVO>
RESULTADO: <resultado observável>
ENTRADAS: <arquivos, repositório, referências>
RESTRIÇÕES: <offline, plataformas, hardware, prazos, licenças>
NÃO FAZER: <exclusões explícitas>
ENTREGÁVEL: <código, auditoria, artefato, integração>
```

### 54.1 Prompt de execução compilado

```yaml
request:
  product_id: ""
  outcome: ""
  sources: []
  constraints: {}
  exclusions: []
agent_contract:
  read_constitution: true
  inspect_existing_sources: true
  run_non_redundancy_check: true
  run_oss_research: true
  run_preflight_100: true
  improve_plan_before_execution: true
  coding_default: "DENIED"
acceptance_criteria: []
reuse_decision: {}
implementation_budget: {}
verification_matrix: []
permissions: {}
resource_budget: {}
rollback: {}
```

---

## 55. ROADMAP POR MÓDULO COM ALERTA DE CONCLUSÃO

Cada módulo tem ID, dependências, entregáveis, gates e alerta próprio. O painel do §3 lê exatamente esta tabela.

### 55.1 FASE A — FUNDAÇÃO

| ID | Módulo | Entregáveis | Depende de | Estado |
| --- | --- | --- | --- | --- |
| M-01 | CONTRATOS E GRAFO | WorkflowIR, validador, schemas, versionamento | — | EM_PROGRESSO |
| M-02 | CANVAS E PORTAS | React Flow, portas tipadas, arrastar, luz no fio, menu ao soltar | M-01 | EM_PROGRESSO |
| M-03 | MANIFESTO E TUTORIAL | NodeManifest, tutorial obrigatório, miniatura gerada, biblioteca | M-01 | EM_PROGRESSO |
| M-04 | REGISTRO DE ASSETS | hash de conteúdo, versões, direitos, proveniência, geo | M-01 | PARCIAL |
| M-05 | REGISTRO DE MODELOS | slots, revisão, hash, licença, benchmark, fallback | M-01 | PARCIAL |
| M-06 | JOBS E AGENDADOR | fila resumível, checkpoint, cancel, planejador de VRAM | M-01 | PARCIAL |
| M-07 | MEGA ROTEADOR | portões duros, score, fallback, explicação do automático | M-05, M-06 | PARCIAL |
| M-08 | ADAPTER COMFY | compilador WorkflowIR → Comfy, import e export, health | M-01 | IMPLEMENTADO |
| M-09 | ALERTA DE CONCLUSÃO | contrato de módulo, gates, evidência, painel de governança | M-01 | ESPECIFICADO |

### 55.2 FASE B — IMAGEM E VÍDEO

| ID | Módulo | Entregáveis | Depende de | Estado |
| --- | --- | --- | --- | --- |
| M-10 | IMAGEM | rápida, quality, edição, camadas, inpaint, outpaint, upscale | M-07 | PARCIAL |
| M-11 | CONTROLE VISUAL | depth, normal, pose, máscara, contorno, segmentação, fluxo | M-07 | ESPECIFICADO |
| M-12 | CONTINUIDADE DE IMAGEM | identidade, estilo, sujeito, estrutura, key visual | M-11 | ESPECIFICADO |
| M-13 | MASTERS 4K A 16K | planejador semântico de tiles, merge, QC global | M-10 | ESPECIFICADO |
| M-14 | VÍDEO | fast8b, 4kpro, max, i2v, t2v, start/end, extensão | M-07 | PARCIAL |
| M-15 | CONTINUIDADE DE VÍDEO | juiz, reparo automático, estado de shot, seed family | M-14 | ESPECIFICADO |
| M-16 | PÓS E RESTAURAÇÃO | SeedVR2, upscale, interpolação, estabilização, deflicker | M-14 | PARCIAL |
| M-17 | COR E VFX | OCIO, ACES, LUT, escopos, relight, key, roto, composição | M-16 | PARCIAL |
| M-18 | ÁUDIO DE FILME | foley, trilha, voz, mix, mux, loudness | M-14 | PARCIAL |
| M-19 | MASTER FINAL | FFmpeg, codecs, QC de frames, evidência | M-17, M-18 | PARCIAL |

### 55.3 FASE C — 3D E ASSETS

| ID | Módulo | Entregáveis | Depende de | Estado |
| --- | --- | --- | --- | --- |
| M-20 | GERAÇÃO 3D | roteador de geradores, image→3D, text→3D, multiview | M-07 | PARCIAL |
| M-21 | RECONSTRUÇÃO 3D | COLMAP, VGGT, MapAnything, 3DGS, NeRF | M-20 | ESPECIFICADO |
| M-22 | TOPOLOGIA E UV | remesh, retopo, UV, LOD, QC de malha | M-20 | PARCIAL |
| M-23 | TEXTURA E PBR | síntese, delight, decomposição, MaterialX, OpenPBR | M-22 | PARCIAL |
| M-24 | BLENDER HEADLESS | bake, simulação, groom, render, export | M-22 | ESPECIFICADO |
| M-25 | EXPORTAÇÃO 3D | GLB, USD, game ready, film ready, web ready | M-23 | PARCIAL |

### 55.4 FASE D — ESPACIAL, CAD, BIM E GIS

| ID | Módulo | Entregáveis | Depende de | Estado |
| --- | --- | --- | --- | --- |
| M-26 | PLANTA | parse raster e PDF, FloorplanGraph, cômodos, topologia | M-01 | ESPECIFICADO |
| M-27 | CAD | DWG, DXF, STEP, CadQuery, sketch paramétrico | M-26 | ESPECIFICADO |
| M-28 | BIM | IFC, autoria, quantitativo, IDS, validação | M-27 | ESPECIFICADO |
| M-29 | GERAÇÃO ARQUITETÔNICA | paredes, aberturas, telhado, escadas, mobília, pranchas | M-28 | ESPECIFICADO |
| M-30 | GIS CORE | GDAL, PROJ, PDAL, CRS, DEM, OSM, Overture | M-01 | ESPECIFICADO |
| M-31 | MUNDO 3D | edifícios, ruas, água, vegetação, 3D Tiles, digital twin | M-30 | ESPECIFICADO |
| M-32 | ANÁLISE AMBIENTAL | sol, daylight, energia, clima, evidência | M-28, M-30 | ESPECIFICADO |
| M-33 | NATUREZA PROCEDURAL | árvore, floresta, grama, água, terreno, céu, pyro | M-24 | ESPECIFICADO |

### 55.5 FASE E — SERES E MOVIMENTO

| ID | Módulo | Entregáveis | Depende de | Estado |
| --- | --- | --- | --- | --- |
| M-34 | DNA HUMANO | corpo, cabeça, medidas, UV canônico, HumanDNA | M-21, M-23 | ESPECIFICADO |
| M-35 | SUPERFÍCIE HUMANA | pele, SSS, microdetalhe, olhos, dentes, cabelo | M-34 | ESPECIFICADO |
| M-36 | RIG E FACE | autorig, blendshapes, FACS, visemas, lipsync | M-35 | ESPECIFICADO |
| M-37 | MOCAP E CLONE | vídeo→mocap, retarget, footlock, IK, física, ao vivo | M-36 | ESPECIFICADO |
| M-38 | ANIMAL E CRIATURA | DNA animal, fur, rig quadrúpede, mocap animal | M-34 | ESPECIFICADO |
| M-39 | VEÍCULO E PRODUTO | carro, moto, rodas, interior, física, mobiliário | M-27 | ESPECIFICADO |
| M-40 | ENTREGA DE PERSONAGEM | game, film e web ready, banco de animação | M-36 | ESPECIFICADO |

### 55.6 FASE F — INTELIGÊNCIA

| ID | Módulo | Entregáveis | Depende de | Estado |
| --- | --- | --- | --- | --- |
| M-41 | WORKER LOCAL | catálogo, validação, proposta de grafo, provider plugável | M-01 | IMPLEMENTADO |
| M-42 | PROMPT COMPILER | PromptIR, adapters por backend, lint, otimização com métrica | M-41 | PARCIAL |
| M-43 | RUNTIMES | llama.cpp, vLLM, SGLang, vLLM-Omni, quantização, residência | M-06 | PARCIAL |
| M-44 | COSMETA | ingest, claims, grafo, contradição, verificador, promoção | M-41 | ESPECIFICADO |
| M-45 | TREINAMENTO | dataset, LoRA, QLoRA, SFT, DPO, eval, red team, promoção | M-44 | ESPECIFICADO |
| M-46 | AGENTES DE CÓDIGO | repo, plano, patch, teste, regressão visual, GUI | M-41 | ESPECIFICADO |
| M-47 | UI PARA CÓDIGO | OCR, layout, tokens, componentes, laço de correção | M-46 | ESPECIFICADO |

### 55.7 FASE G — PRODUTO E GOVERNANÇA

| ID | Módulo | Entregáveis | Depende de | Estado |
| --- | --- | --- | --- | --- |
| M-48 | PERFIL ADULTO LOCAL | ContentProfile, bindings, benchmark, portões duros | M-10, M-14 | ESPECIFICADO |
| M-49 | CONSENTIMENTO E BIOMETRIA | ConsentManifest, revogação, separação de identidade | M-34 | ESPECIFICADO |
| M-50 | LICENÇA E SBOM | registro, tags, gate, relatório de proveniência | M-05 | PARCIAL |
| M-51 | TELEMETRIA E EVIDÊNCIA | OpenTelemetry, ledger, painel de governança | M-09 | PARCIAL |
| M-52 | EMPACOTAMENTO | instalador, assinatura, atualização, rollback, `.bat` único | — | PARCIAL |

### 55.8 Alerta de conclusão por fase

Quando todos os módulos de uma fase atingem `CONCLUIDO`, dispara o alerta de fase — mesmo componente, escala maior:

```
╔════════════════════════════════════════════════════════════════════════════╗
║  [icon:concluido]   FASE CONCLUÍDA                             FASE A      ║
║                                                                            ║
║  FUNDAÇÃO                                                                  ║
║  9 módulos · 41 gates aprovados · 0 pendências bloqueantes                 ║
║                                                                            ║
║  ████████████████████████████████████████████████████████████  100%       ║
║                                                                            ║
║  M-01 [icon:concluido]  M-02 [icon:concluido]  M-03 [icon:concluido]       ║
║  M-04 [icon:concluido]  M-05 [icon:concluido]  M-06 [icon:concluido]       ║
║  M-07 [icon:concluido]  M-08 [icon:concluido]  M-09 [icon:concluido]       ║
║                                                                            ║
║  Desbloqueia   FASE B — IMAGEM E VÍDEO (10 módulos)                        ║
║  Evidência     docs/evidence/FASE-A/                                       ║
║                                                                            ║
║  [ Ver evidência da fase ]   [ Abrir FASE B ]                             ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---
## 56. INVENTÁRIO DE PROJETOS A AVALIAR

Lista de pesquisa, não lista de dependências. Cada entrada passa por `GATE-OSS-RESEARCH` e `GATE-LICENSE` antes de virar binding.

### 56.1 Canvas e grafo

```
xyflow/xyflow
retejs/rete
bytedance/flowgram.ai
Comfy-Org/ComfyUI
```

### 56.2 Difusão e mídia

```
huggingface/diffusers
modelscope/DiffSynth-Studio
mcmonkeyprojects/SwarmUI
invoke-ai/InvokeAI
nunchaku-ai/nunchaku
leejet/stable-diffusion.cpp
```

### 56.3 Imagem

```
QwenLM/Qwen-Image
black-forest-labs/flux2
Tencent-Hunyuan/HunyuanImage-2.1
Tongyi-MAI/Z-Image-Turbo
Stability-AI/generative-models
```

### 56.4 Vídeo

```
Wan-Video/Wan2.2
Lightricks/LTX-Video
Tencent-Hunyuan/HunyuanVideo-1.5
SkyworkAI/SkyReels-V3
lllyasviel/FramePack
genmoai/mochi
THUDM/CogVideo
hpcaitech/Open-Sora
ByteDance-Seed/SeedVR
hzwer/Practical-RIFE
google-research/frame-interpolation
```

### 56.5 3D e humano

```
microsoft/TRELLIS.2
Tencent-Hunyuan/Hunyuan3D-2.1
Tencent-Hunyuan/Hunyuan3D-Omni
Tencent-Hunyuan/HunyuanWorld
facebookresearch/sam-3d-objects
facebookresearch/sam-3d-body
facebookresearch/MHR
TencentARC/Pixal3D
VAST-AI-Research/TripoSR
VAST-AI-Research/TripoSG
VAST-AI-Research/TripoSplat
Stability-AI/stable-fast-3d
Stability-AI/spar3d
TencentARC/InstantMesh
xxlong0/Wonder3D
facebookresearch/vggt
facebookresearch/map-anything
naver/dust3r
naver/mast3r
nerfstudio-project/nerfstudio
nerfstudio-project/gsplat
colmap/colmap
horizon-research/EmbodiedGen
```

### 56.6 Movimento e animal

```
zju3dv/GVHMR
benjiebob/SMALify
facebookresearch/AnimalAvatar
vchoutas/smplx
caizhongang/SMPLer-X
YuliangXiu/ECON
SiTH-Diffusion/SiTH
```

### 56.7 Controle visual

```
DepthAnything/Depth-Anything-V2
DepthAnything/Video-Depth-Anything
prs-eth/Marigold
facebookresearch/sam2
IDEA-Research/GroundingDINO
IDEA-Research/DWPose
princeton-vl/RAFT
lllyasviel/ControlNet
tencent-ailab/IP-Adapter
ToTheBeginning/PuLID
InstantID/InstantID
TencentARC/PhotoMaker
bytedance/DreamO
bytedance/USO
lllyasviel/IC-Light
```

### 56.8 Áudio

```
SWivid/F5-TTS
index-tts/index-tts
FunAudioLLM/CosyVoice
resemble-ai/chatterbox
myshell-ai/OpenVoice
RVC-Boss/GPT-SoVITS
RVC-Project/Retrieval-based-Voice-Conversion-WebUI
QwenLM/Qwen3-ASR
SYSTRAN/faster-whisper
openai/whisper
FunAudioLLM/SenseVoice
ace-step/ACE-Step
facebookresearch/audiocraft
multimodal-art-projection/YuE
Stability-AI/stable-audio-tools
Tencent-Hunyuan/HunyuanVideo-Foley
facebookresearch/demucs
```

### 56.9 LLM, VLM e runtime

```
ggml-org/llama.cpp
ollama/ollama
vllm-project/vllm
vllm-project/vllm-omni
sgl-project/sglang
turboderp/exllamav2
NVIDIA/TensorRT-LLM
ml-explore/mlx
microsoft/onnxruntime
openvinotoolkit/openvino
QwenLM/Qwen3-VL
QwenLM/Qwen3-Coder
QwenLM/qwen-code
MoonshotAI/Kimi-K3
MoonshotAI/kimi-code
google-deepmind/gemma
LiquidAI/LFM2.5-8B-A1B
```

### 56.10 Treinamento

```
hiyouga/LLaMA-Factory
unslothai/unsloth
huggingface/peft
huggingface/trl
```

### 56.11 CAD, BIM e planta

```
IfcOpenShell/IfcOpenShell
LibreDWG/libredwg
CadQuery/cadquery
Open-Cascade-SAS/OCCT
CubiCasa/CubiCasa5k
ywyue/RoomFormer
3dlg-hcvc/plan2scene
PhyScene/PhyScene
ladybug-tools/honeybee-core
NREL/EnergyPlus
```

### 56.12 GIS

```
OvertureMaps/data
maplibre/maplibre-gl-js
visgl/deck.gl
keplergl/kepler.gl
CesiumGS/cesium
CesiumGS/cesium-native
OSGeo/gdal
OSGeo/PROJ
PDAL/PDAL
duckdb/duckdb-spatial
postgis/postgis
protomaps/PMTiles
osmcode/libosmium
```

### 56.13 VFX e DCC

```
AcademySoftwareFoundation/OpenColorIO
AcademySoftwareFoundation/OpenImageIO
AcademySoftwareFoundation/openexr
AcademySoftwareFoundation/MaterialX
AcademySoftwareFoundation/OpenVDB
AcademySoftwareFoundation/OpenTimelineIO
PixarAnimationStudios/OpenUSD
blender/blender
NatronGitHub/Natron
FFmpeg/FFmpeg
zeux/meshoptimizer
jpcy/xatlas
```

### 56.14 Engines

```
godotengine/godot
o3de/o3de
bevyengine/bevy
BabylonJS/Babylon.js
mrdoob/three.js
google/filament
```

### 56.15 Código, agentes e conhecimento

```
All-Hands-AI/OpenHands
Aider-AI/aider
cline/cline
continuedev/continue
princeton-nlp/SWE-agent
bytedance/UI-TARS
abi/screenshot-to-code
NoviScl/Design2Code
langchain-ai/langgraph
FlowiseAI/Flowise
run-llama/llama_index
deepset-ai/haystack
microsoft/autogen
crewAIInc/crewAI
huggingface/smolagents
pydantic/pydantic-ai
modelcontextprotocol/servers
kuzudb/kuzu
microsoft/playwright
```

### 56.16 Reconhecimento facial e biometria

```
deepinsight/insightface
serengil/deepface
mk-minchul/CVLface
```

`GATE-LICENSE` obrigatório: pesos e datasets de reconhecimento facial têm condições frequentemente diferentes do código.

---

## 57. CORREÇÕES DE PESQUISA — SNAPSHOT 2026-08-07

Registradas para que ninguém repita a informação antiga.

| Item | Correção |
| --- | --- |
| LiquidAI LFM2.5-8B-A1B | 8.3B totais, ~1.5B ativos por token, 128K de contexto. Não é um 8B denso |
| Kimi K3 | Existe oficialmente: open-weight, multimodal, 2.8T, contexto 1M. **Perfil servidor/distribuído**, nunca "modelo leve" |
| vLLM-Omni | Alternativa moderna relevante para serving multimodal, difusão e omni |
| SAM 3D Body | Usa **Momentum Human Rig (MHR)** como representação paramétrica |
| facebookresearch/MHR | 45 parâmetros de identidade, 204 de pose, 72 de expressão, múltiplos LODs |
| LTX-2.3 | Release open-weight de foundation model áudio-vídeo; pin exato fica no ModelRegistry |
| Wan2.2 | Continua peça principal do ecossistema I2V/T2V e de LoRA |
| 4K, 8K e 16K | Tratar como **master de saída** quando não houver evidência de geração nativa nessa resolução |
| GIS comercial | Entra apenas como provider; o produto mantém open core |
| Real-ESRGAN | O release `v0.2.0` **não traz modelos** (2.1 MB, 6 entradas). Usar o asset `v0.2.5.0` de `xinntao/Real-ESRGAN` (45.5 MB) com verificação pós-instalação exigindo `models/*.param` |
| ncnn-vulkan `-m` | Os executáveis concatenam o valor de `-m` ao diretório do binário. Caminho absoluto produz `<exedir>\<abspath>` e o `_wfopen` falha. Solução: `cwd` no diretório do exe e `-m` relativo |
| CMake + nvcc | O CMake escolhia Ninja com MinGW e o nvcc recusava. Fixar o gerador "Visual Studio 17 2022" e compilar `--target sd-cli` |
| VAE do FLUX | Gated. Substituído pelo VAE público `Tongyi-MAI/Z-Image-Turbo`, sha256 `f5b59a26...`, verificado funcionando |
| Falsa cor | `format=gray` antes de `pseudocolor` zera a crominância. Medido 0% contra 100% de pixels coloridos. Corrigido |
| `image.upscale` tile | `tile=0` levou 244.9 s; `tile=256` levou 6.0 s. Padrão passou a 256 |
| Filtro de categoria do agente | Correspondência exata fazia o modelo **afirmar que nós de vídeo não existem**. Corrigido com dobra de acento e retorno das categorias disponíveis |
| Hardware alvo | RTX 4090 **Laptop, 16 GB** — não 24 GB como documentos antigos afirmavam. CUDA 13.1, MSVC 14.44, rustc 1.97.1 |
| Contenção de GPU | ComfyUI e Ollama residentes em 16 GB travaram até o `nvidia-smi`; chamada do worker foi de 41 s para 280 s. O agendador existe por causa disso |

---

## 58. O QUE NÃO FAZER

Quinhentos wrappers sem contrato. UI presa a um checkpoint específico. Workflow canônico existindo só como JSON do Comfy. Custom node com acesso irrestrito ao host. LLM para geometria exata que o CAD resolve. Difusão para cálculo solar. Inventar levantamento de campo. Chamar upscale de "16K nativo". Chamar pesos públicos de open source sem licença resolvida. Chamar Kimi K3 de modelo leve. Laço autônomo ilimitado. Auto-treino silencioso. Identidade existindo apenas como prompt. Perder CRS ou unidades. Esconder proveniência. Emoji em qualquer superfície. Declarar módulo concluído sem arquivo de evidência.

---

## 59. ARQUITETURA FINAL

```
                              COSMETA ULTRA
                                    │
                     ┌──────────────┴──────────────┐
                     │        NODE CANVAS          │
                     │  React Flow · portas tipadas│
                     │  ícones · miniaturas · pt-BR│
                     └──────────────┬──────────────┘
                                    │
                              WorkflowIR
                                    │
                          UNIVERSAL COMPILER
                                    │
                             MEGA ROUTER
                                    │
      ┌──────────────┬──────────────┼──────────────┬──────────────┐
      ▼              ▼              ▼              ▼              ▼
   ComfyUI      DiffSynth     vLLM · SGLang     Blender       CAD · GIS
                              vLLM-Omni
   sd.cpp       Diffusers     llama.cpp         FFmpeg        IfcOpenShell
   RIFE                                         Natron        GDAL · PROJ
   ESRGAN                                                     Cesium
      │              │              │              │              │
      └──────────────┴──────────────┴──────────────┴──────────────┘
                                    │
                        ASSET / STATE FABRIC
                                    │
      ┌─────────────────────────────┼─────────────────────────────┐
      ▼                             ▼                             ▼
  HumanDNA                     WorldState                    Knowledge
  AnimalDNA                    CAD · BIM · GIS               COSMETA
  VehicleDNA                   ContinuityState               Memory
      │                             │                             │
      └─────────────────────────────┴─────────────────────────────┘
                                    │
                        EVIDENCE / PROVENANCE
```

---

## 60. INVARIANTE DE EXPERIÊNCIA

Nenhum nome de modelo vira contrato de UI.

**São contratos de capacidade:** FILME 4K CINEMA PRO; OBJETO PARA 3D QUALITY; DNA HUMANO; PLANTA PARA BIM 3D; PENSAMENTO LOCAL LEVE; VISÃO E RACIOCÍNIO; COSMETA REFINAR CONHECIMENTO.

**São implementações substituíveis:** Hunyuan, LTX, Wan, TRELLIS, Qwen, FLUX, Kimi, Liquid, Gemma, ComfyUI, DiffSynth e todo o resto.

O front fala linguagem humana. O backend fala nomes exatos. O roteador fala capability slots. A governança fala hashes, licenças, evidência e risco.

---

## 61. INVARIANTE FINAL DE ENGENHARIA

Antes de criar qualquer código, serviço, modelo, banco, componente de UI, workflow ou aplicação, todo agente responde com evidência:

> Esta capacidade já existe dentro do ecossistema Legrand, ou em um projeto externo maduro, compatível, seguro e licenciável, e pode ser configurada, composta, envolvida ou conectada em vez de reconstruída?

Implementação custom é permitida apenas quando a resposta é demonstravelmente não, a superfície mínima substituível está delimitada, e todos os gates passam.

O produto ideal não é "um Comfy com mais nós". É:

```
VISUAL NODE OS
+ REUSO DO COMFY
+ MULTI-RUNTIME
+ MEGA ROUTER
+ AGENDADOR DE RECURSOS
+ IMAGEM · VÍDEO · 3D · ÁUDIO
+ CAD · BIM · GIS
+ MUNDO PROCEDURAL
+ DNA HUMANO · ANIMAL · VEÍCULO
+ CONTINUITY ENGINE
+ AGENTES DE CÓDIGO
+ COSMETA CONHECIMENTO VERIFICADO
+ PERFIL ADULTO LOCAL
+ PROVENIÊNCIA
+ LOCAL-FIRST
```

---

## 62. ESTADO REAL DO REPOSITÓRIO — HOJE

Esta seção é a única que fala do que existe agora. Tudo aqui tem evidência anexada; o resto do documento é especificação.

### 62.1 O que roda

| Item | Evidência |
| --- | --- |
| Servidor CineNode 0.1.0 | `/api/health` responde `status ok`, `ready true`; `/`, `/app.js`, `/api/bootstrap`, `/api/projects` retornam 200 |
| Catálogo de nós | 19 tipos, 86 campos, **todos com controle visual** |
| Suíte de testes | 62 testes passando |
| Validação de pacote | 497 checagens, 0 falhas |
| Geração de imagem | 1024² + upscale 4× em 36.12 s, pico de 9 507 MiB |
| Geração de vídeo | 832×480, 33 frames, 20 passos, RIFE, H.265 em 400.82 s, pico de 15 752 MiB |
| Geração 3D | malha real pelo app em 82.1 s, GLB de 8.9 MB, `model/gltf-binary` |
| Worker local | grafo válido de 3 nós e 2 arestas, `dolly in`, 21:9, 4K, terminando em `output.preview`, com a primeira tentativa rejeitada pelo validador |
| Escopos de vídeo | forma de onda, vetorscópio, histograma, falsa cor, alfa, P&B — falsa cor corrigida e medida |
| Inicialização | `start.bat` sobe CineNode, Ollama e ComfyUI conforme instalados, com aviso de VRAM |
| Regra visual | `tests/test_catalog_visual_rule.py` impede regressão de campo cru |

### 62.2 O que é parcial

Master 4K completo; roteador com score real; registro de modelos com hash de todos os pesos; planejador de VRAM; jobs resumíveis com checkpoint; telemetria OpenTelemetry; painel de governança.

### 62.3 O que é apenas especificação

Tudo marcado `[ESPECIFICADO]` nas tabelas do §10 e todos os módulos `ESPECIFICADO` no §55. Nenhum deles aparece na UI como pronto. Nenhum deles tem alerta de conclusão disparado.

### 62.4 Bloqueios conhecidos

| Bloqueio | Motivo | Dono da decisão |
| --- | --- | --- |
| Assinatura do instalador | requer certificado de assinatura de código | usuário |
| SUPIR em produção | licença precisa passar por `GATE-LICENSE` | governança |
| Módulos que exigem ComfyUI e Ollama simultâneos | 16 GB de VRAM não comportam ambos residentes em carga pesada | hardware |
| Visualizador GLB dentro do cartão do nó | não implementado; hoje o preview 3D é externo | engenharia |

---

## 63. COMO USAR ESTE DOCUMENTO

**Para o usuário.** Leia §2 (alerta de conclusão), §3 (painel), §9 e §10 (categorias e nós), §17 (fluxos prontos), §21 (presets), §55 (roadmap). É a experiência inteira em linguagem de produto.

**Para a IA que vai codar.** Leia §1 (ícones), §6 e §7 (nó e portas), §8 (manifesto), §11 a §16 (modelos, backends, roteador, hardware), §37 a §46 (formatos, registros, IR, SDK, eventos, jobs), §50 (definition of ready), §51 a §54 (governança, 100 checagens, system prompt). É o contrato de implementação.

**Para governança.** Leia §2.2 e §2.3 (contrato de módulo e formato de evidência), §39.1 (tags de licença), §48 e §49 (consentimento e perfil adulto), §51.8 (gates), §52 (100 checagens), §57 (correções), §62 (estado real).

Nenhuma das três leituras é resumo das outras. Todas descrevem o mesmo sistema.

---

**FIM DO DOCUMENTO ÚNICO**
---

# PARTE II — ORÁCULO MASTER ADMIN, PAINEL LATERAL E ORGANIZAÇÃO AUTOMÁTICA

Esta parte agrega o **00 — ORÁCULO MASTER ADMIN / COSMETA ULTRA + BRAINLINK CUMULATIVO V5** às seções anteriores. Nada da Parte I foi removido. O que já estava implementado continua implementado; o que é novo está marcado com o mesmo vocabulário de status.

---

## 64. IDENTIDADE E MODOS DA INTERFACE

O aplicativo continua um canvas. A navegação troca **modo**, não aplicativo mental.

| ID | Nome no front | Rota | Função | Est. |
| --- | --- | --- | --- | --- |
| CANVAS | Workflow nodal | `/canvas` | grafo COSMETA | IMP |
| CHAT | Agente | `/chat` | chat texto, voz e ferramentas | PAR |
| VOICE | Voz Live | `/voice` | agente de voz full-duplex | ESP |
| BRAIN | Brainlink | `/brainlink` | governança e conhecimento derivados do AFFiNE | ESP |
| APPS | Criar Apps | `/studio/apps` | adapter Dyad | ESP |
| AGENTS | Agentes Visuais | `/studio/agents` | adapter Flowise | ESP |
| CODE | Código | `/studio/code` | adapter OpenCode e worker | ESP |
| FILES | Biblioteca | `/files` | gerenciador virtual de arquivos e assets | IMP |
| PROMPTS | Prompts | `/prompts` | arquétipos e biblioteca de prompts | ESP |
| ASK | Ask | `/ask` | ajuda contextual e bugs resolvidos | ESP |
| MODELS | Engines e modelos | `/models` | registro de modelo e runtime | IMP |
| MCP | Conexões e MCP | `/mcp` | registro, instalação, config, saúde | PAR |
| SCHEDULE | Fila e jobs | `/schedule` | jobs, prompts, gerações | IMP |
| ALERTS | Alertas | `/alerts` | notificações operacionais e de usuário | PAR |
| WORKERS | Workers | `/workers` | frota, execução, capacidades | ESP |
| VENDORS | Vendors | `/vendors` | upstream, fork, atualização | ESP |
| DATA | Dados | `/data` | Ultrabase, storage, índices | ESP |
| GOV | Governança | `/governance` | evidência, auditoria, tarefas, regras | IMP |
| SETTINGS | Configurações | `/settings` | políticas globais | IMP |

### 64.1 Subprodutos lógicos, um só sistema

`ORÁCULO` é o shell administrativo. `COSMETA` é o canvas nodal. `BRAINLINK` é o conhecimento e a governança, derivado do AFFiNE. `WORKER FABRIC` é quem coda e mantém. `ULTRABASE` é o plano de dados. Nenhum deles duplica identidade, telemetria, assets, permissões ou registro de modelos: todos consomem os mesmos contratos.

---

## 65. PAINEL LATERAL — SOFTWARE CONTROLADO E NAVEGADOR INTERNO `[IMPLEMENTADO]`

Um painel que nasce da direita, é redimensionável por arrasto, colapsável, e **empurra** o canvas em vez de flutuar por cima. Abre e fecha com `Ctrl+B`. A largura fica no `localStorage`: reabrir não perde o ajuste.

```
┌────────────────────────────────────────────────┬──────────────────────────────┐
│  CANVAS                                        │ [nav][soft][rot]        [x]  │
│                                                ├──────────────────────────────┤
│   ╭──────────╮      ╭──────────╮               │ ◀ ⟳ [ endereço          ] ▶ │
│   │ Prompt   │─────▶│ Gerar    │               │ ─────────────────────────── │
│   ╰──────────╯      │ take     │               │                              │
│                     ╰──────────╯               │   conteúdo do site           │
│                                                │   ou leitura por texto       │
│                                                │   quando o embed é negado    │
│                                              ║ │                              │
│                                       arraste ║ │                              │
└────────────────────────────────────────────────┴──────────────────────────────┘
```

### 65.1 Identificadores para quem for codar

| Papel | Identificador |
| --- | --- |
| Contêiner do painel | `<aside class="side-dock">` com `--dock-width` em `:root` |
| Alça quando fechado | `.dock-handle` com `data-dock-open` |
| Borda de arrasto | `.dock-resizer` com `data-dock-resize` — `pointerdown` + `setPointerCapture` |
| Empurra o canvas | `body[data-dock-open="1"] .app-shell { width: calc(100vw - var(--dock-width)) }` |
| Estado | `state.dock` — `{ open, tab, width, url, page, targets, active, catalog }` |
| Montagem | `mountDock()` chamado no fim de `initialize()` |
| Persistência | `localStorage` em `cinenode.dock.width` e `cinenode.dock.url` |
| Atalho | `Ctrl+B` / `Cmd+B` |

Limites de arrasto: mínimo 300 px, máximo `window.innerWidth - 380` — o canvas nunca fica menor que um cartão de nó mais a paleta.

```js
const move = moveEvent => {
  const proposto = startWidth + (startX - moveEvent.clientX);
  state.dock.width = Math.max(300, Math.min(window.innerWidth - 380, proposto));
  ...
};
```

### 65.2 As três abas

| Aba | Ícone | O que faz |
| --- | --- | --- |
| **Navegador** | `icon:remoto` | acesso real à internet dentro do app: barra de endereço, busca, recarregar, voltar |
| **Software** | `icon:processador` | lista os softwares controláveis com estado medido, e embute o que aceita ser embutido |
| **Roteamento** | `icon:roteador` | OpenRouter, política local-first, e a ligação de cada capacidade a um modelo |

### 65.3 Navegador interno — o problema real do `X-Frame-Options`

A maioria dos sites recusa ser embutida em `iframe`. Fingir que funciona seria entregar um retângulo em branco. A solução tem dois caminhos e o painel escolhe sozinho:

```
usuário digita endereço
 ↓
POST /api/web/fetch          servidor local busca a página
 ↓
resposta traz: título, status, texto extraído, embed_bloqueado
 ↓
├─ embed_bloqueado = false → <iframe> com o site ao vivo
└─ embed_bloqueado = true  → modo leitura com o texto lido pelo servidor
                              + "Abrir no navegador do sistema"
                              + "Enviar texto para um nó"
```

O último botão é o que torna o navegador parte do fluxo: o texto da página vira um nó `input.text` no canvas, com um clique.

```python
@app.post("/api/web/fetch")
async def web_fetch(request: Request, payload: WebFetchPayload) -> Any:
    require_local_request(request, config)
    url = payload.url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    ...
    bloqueia_iframe = any(
        header.lower() in {"x-frame-options"} for header in response.headers
    ) or "frame-ancestors" in (response.headers.get("content-security-policy") or "").lower()
```

**Evidência.** `POST /api/web/fetch {"url":"example.com"}` → `status=200`, `titulo='Example Domain'`, `embed_bloqueado=False`, 142 caracteres de texto extraído.

### 65.4 Software controlado — estado medido, nunca declarado

Cada alvo declara `url`, `health`, se aceita embed, e o comando exato que o instala. O painel faz o probe antes de mostrar qualquer coisa.

```python
DEFAULT_TARGETS = [
    {"id": "comfyui",   "nome": "ComfyUI",   "icone": "processador",
     "url": "http://127.0.0.1:8188",  "health": "http://127.0.0.1:8188/system_stats",
     "tipo": "sidecar", "instalar": "scripts\\install-comfy.ps1", "embed": True},
    {"id": "ollama",    "nome": "Ollama",    "icone": "agente",
     "url": "http://127.0.0.1:11434", "health": "http://127.0.0.1:11434/api/version",
     "tipo": "runtime", "instalar": "winget install Ollama.Ollama", "embed": False},
    {"id": "brainlink", "nome": "Brainlink", "icone": "conhecimento",
     "url": "http://127.0.0.1:8080",  "health": "http://127.0.0.1:8080",
     "tipo": "vendor",  "instalar": "yarn dev em 26-Aiia universal UI/AFFINE", "embed": True},
    {"id": "flowise",   "nome": "Flowise",   "icone": "fluxo",
     "url": "http://127.0.0.1:3000",  "health": "http://127.0.0.1:3000/api/v1/ping",
     "tipo": "vendor",  "instalar": "npx flowise start", "embed": True},
]
```

**Evidência medida nesta máquina:**

```
ComfyUI      fora       http://127.0.0.1:8188
Ollama       no ar      http://127.0.0.1:11434
Brainlink    no ar      http://127.0.0.1:8080
Flowise      fora       http://127.0.0.1:3000
```

Alvo fora do ar não some da lista: ele mostra o comando que o coloca no ar. `GET /api/mcp/targets` e `PUT /api/mcp/targets` permitem registrar alvos próprios.

### 65.5 Catálogo MCP a ser suportado

Do ORÁCULO §12, preservado integralmente como registro de decisão:

| Área | Servidor ou adapter | Uso | Decisão |
| --- | --- | --- | --- |
| Filesystem | referência MCP + versão interna endurecida | ler e escrever raízes com escopo | CHAMPION INTERNAL-HARDENED |
| Git | referência MCP + adapter do git CLI | leitura de repo, diff, branch | CHAMPION |
| Fetch e Web | referência Fetch + cliente web governado | busca web | CANDIDATE |
| GitHub | `github/github-mcp-server` | repos, issues, PRs | CHAMPION |
| Browser | `microsoft/playwright-mcp` | automação de navegador | CANDIDATE SANDBOX |
| Memory | referência Memory apenas como estudo | memória em grafo | NÃO USAR COMO FONTE DE VERDADE |
| Time | referência ou registry atual | fuso e tempo | UTILITY |
| Postgres e DB | DBHub ou MCP próprio da Ultrabase | consulta e schema sob política | INTERNAL CHAMPION |
| SQLite | wrapper MCP interno | leitura e escrita local | INTERNAL |
| Files e Assets | Asset MCP do Oráculo | mídia e arquivos | INTERNAL |
| ComfyUI | Comfy MCP ou adapter | executar workflows | INTERNAL |
| Blender | Blender MCP do Oráculo | cena, modelo, render | INTERNAL |
| FFmpeg | Media MCP do Oráculo | transcode e probe | INTERNAL |
| CAD | CAD MCP do Oráculo | OpenCascade e CadQuery | INTERNAL |
| BIM | BIM MCP do Oráculo | IfcOpenShell e Bonsai | INTERNAL |
| GIS | GIS MCP do Oráculo | GDAL, PROJ, PDAL | INTERNAL |
| Models | Model MCP do Oráculo | descobrir, carregar, instalar | INTERNAL |
| Prompts | Prompt MCP do Brainlink | arquétipos e versões | INTERNAL |
| Bugs | Bug MCP do Brainlink | consultar e testar solução | INTERNAL |
| Governance | Governance MCP do Brainlink | regras, tarefas, evidência | INTERNAL |
| Schedule | Scheduler MCP do Oráculo | criar, cancelar, inspecionar jobs | INTERNAL |
| Notifications | Notify MCP do Oráculo | ntfy, Telegram, provider | INTERNAL |
| Voice | Voice MCP ou adapter Pipecat | falar, ouvir, sessão | INTERNAL |
| OpenCode | adapter OpenCode | sessão de codificação | INTERNAL/VENDOR |
| Dyad | adapter Dyad | sessão de construção de app | INTERNAL/VENDOR |
| Flowise | adapter Flowise | agentflow e chatflow | INTERNAL/VENDOR |

### 65.6 Auto-instalação de MCP não é auto-confiança

```
USUÁRIO OU WORKER PEDE CAPACIDADE
 ↓
registro interno de capacidades
 ↓ ausente
busca no MCP Registry oficial
 ↓
metadados do candidato
 ↓
proveniência do repositório ou pacote
 ↓
portão de licença
 ↓
varredura de segurança
 ↓
pin de versão e hash exatos
 ↓
instala em SANDBOX
 ↓
MCP Inspector e teste de contrato
 ↓
diff da lista de ferramentas
 ↓
classificação de risco da capacidade
 ↓
gera configuração
 ↓
teste de saúde
 ↓
CANDIDATE
 ↓
habilita lease com escopo
```

```yaml
mcp_server:
  id: ""
  display_name: ""
  source_registry: "official|internal|manual"
  package_or_repo: ""
  version: ""
  digest: ""
  protocol_versions: ["2026-07-28"]
  transport: [stdio, streamable_http]
  tools: []
  resources: []
  prompts: []
  scopes: []
  filesystem_roots: []
  network_destinations: []
  secret_refs: []
  sandbox_profile: ""
  health: "UNKNOWN"
  license: {}
  sbom_ref: null
  status: "DISCOVERED|SANDBOXED|CANDIDATE|STABLE|BLOCKED"
```

### 65.7 Contrato de sessão de vendor

```yaml
VendorSession:
  id: "uuidv7"
  vendor_id: "affine|dyad|flowise|opencode|..."
  upstream_pin: ""
  fork_pin: null
  project_id: ""
  workspace_root_ref: ""
  gateway_virtual_key_ref: ""
  mcp_profile_id: ""
  filesystem_lease_id: ""
  network_policy_id: ""
  started_at: ""
  ended_at: null
  evidence_refs: []
```

Dyad nunca recebe acesso a `D:\` inteiro. OpenCode trabalha em worktree com perfil `PLAN` (somente leitura), `BUILD` (escrita com escopo), `REPAIR`, `NODE` (Node Factory) ou `MIGRATION`.

---

## 66. GATEWAY DE PROVEDORES — OPENROUTER PARA QUALQUER NÓ `[IMPLEMENTADO]`

Uma chave, muitos apps, e **nenhum vendor recebe o segredo master**.

```
COSMETA · Brainlink · Dyad · Flowise · OpenCode · Workers
     │
     └── endpoint local compatível com OpenAI
                  ↓
            AIIA AI GATEWAY
            ├─ llama.cpp local
            ├─ Ollama local
            ├─ vLLM local
            ├─ SGLang local
            ├─ vLLM-Omni local
            └─ adapter OpenRouter
                       ↓
                 Secret Broker
                 OPENROUTER_API_KEY
```

### 66.1 Capacidades — o nó pede isto, não um modelo

```python
CAPABILITY_SLOTS = {
    "texto.rapido":     "Classificar, renomear, escolher ferramenta, validar JSON.",
    "texto.raciocinio": "Planejar grafo, escrever prompt estruturado, decidir pipeline.",
    "visao":            "Descrever imagem, categorizar asset, ler tela, conferir resultado.",
    "codigo":           "Ler repositório, propor patch, escrever teste.",
    "embedding":        "Transformar texto em vetor para busca semântica.",
}
```

Cada slot declara dicas locais e remotas em ordem de preferência. Trocar o modelo não muda o grafo salvo.

### 66.2 Ordem de resolução, explícita para o usuário poder discordar

```
1. Escolha explícita do usuário   — se o modelo ainda existir
2. Local, na ordem das dicas      — LOCAL_ONLY para aqui
3. Remoto pelo OpenRouter         — extensão, nunca dependência silenciosa
4. Qualquer local instalado       — melhor que nada
```

**Evidência medida nesta máquina — 29 modelos locais encontrados:**

```
texto.rapido       -> ollama / qwen3:14b                modelo local compatível
texto.raciocinio   -> ollama / qwen3:14b                modelo local compatível
visao              -> ollama / llava:13b                modelo local compatível
codigo             -> ollama / qwen3-coder:30b          modelo local compatível
embedding          -> ollama / nomic-embed-text:latest  modelo local compatível
```

### 66.3 Políticas

| Política | Comportamento |
| --- | --- |
| `LOCAL_ONLY` | nunca sai da máquina; slot sem modelo local fica sem resposta e diz por quê |
| `LOCAL_FIRST` | local vence; remoto só quando não há local para o slot (padrão) |
| `HYBRID` | escolhe pelo melhor encaixe declarado |

### 66.4 A chave nunca volta

```python
def settings(self) -> dict[str, Any]:
    raw = self.store.get_setting("ai_gateway") or {}
    return {
        "openrouter_enabled": bool(raw.get("openrouter_enabled", False)),
        "openrouter_key_set": bool(raw.get("openrouter_key")),   # existe? sim. qual? nunca.
        "policy": raw.get("policy", "LOCAL_FIRST"),
        "bindings": raw.get("bindings", {}),
        ...
    }
```

E salvar a política não pode derrubar a chave por omissão:

```python
# A chave só é gravada quando vem preenchida: mandar vazio não apaga sem intenção.
if patch.get("openrouter_key"):
    raw["openrouter_key"] = str(patch["openrouter_key"]).strip()
```

Ambos os comportamentos são testados:

```python
def test_chave_nunca_volta_em_texto_claro():
    gateway.save_settings({"openrouter_key": "sk-or-segredo", "openrouter_enabled": True})
    assert "sk-or-segredo" not in json.dumps(gateway.settings())
    assert gateway.settings()["openrouter_key_set"] is True

def test_salvar_sem_chave_nao_apaga_a_existente():
    gateway.save_settings({"openrouter_key": "sk-or-abc", "openrouter_enabled": True})
    gateway.save_settings({"policy": "HYBRID"})
    assert gateway.settings()["openrouter_key_set"] is True
```

### 66.5 Rotas

| Rota | Método | Função |
| --- | --- | --- |
| `/api/ai/catalog` | GET | slots, modelos locais, modelos do OpenRouter, resolução atual |
| `/api/ai/settings` | GET, PUT | política, chave, ligações por slot |
| `/api/ai/chat` | POST | chamada única para qualquer provedor, mesma forma de resposta |
| `/api/ai/resolve/{slot}` | GET | qual provedor e modelo atendem este slot, e por quê |

### 66.6 Erro sempre diz como corrigir

```python
raise GatewayError(
    "SEM_MODELO",
    f"Nenhum modelo disponível para a capacidade {slot!r}.",
    "Instale um modelo local com `ollama pull qwen3:4b` "
    "ou ative o OpenRouter em Configurações.",
)
```

Testado: `test_erro_do_gateway_sempre_diz_como_corrigir` exige as três chaves `erro`, `mensagem`, `como_corrigir`.

---

## 67. NÓS RESPONSIVOS — NADA ESCONDIDO, TUDO COLAPSADO `[IMPLEMENTADO]`

A regra tem duas metades, e a segunda é a que costuma ser esquecida: **colapsado não pode significar invisível**.

### 67.1 Resumo iconizado do painel avançado

O `<summary>` do painel colapsado mostra um ícone por campo e o contador de quantos foram alterados. O usuário sabe o que existe lá dentro sem abrir.

```
┌──────────────────────────────────────────────┐
│ [ico] FILME 4K CINEMA PRO          LOCAL 18GB│
├──────────────────────────────────────────────┤
│ TEXTO  [ cidade neon sob chuva            ]  │
├──────────────────────────────────────────────┤
│ ▸ [en][fm][cm][lz][fp][sd][+7]          4/14 │  ← colapsado, mas legível
└──────────────────────────────────────────────┘
                    ↓ clique
┌──────────────────────────────────────────────┐
│ ▾ [en][fm][cm][lz][fp][sd][+7]          4/14 │
│ ENGINE     (wan)(sd_cpp)(comfy)              │
│ MOVIMENTO  [ dolly in            ▸]          │
│ FORMATO    ▢ ▯ ▭ ▭▭ ▭▭▭                      │
│ FRAMES     [──────●────]  33                 │
└──────────────────────────────────────────────┘
```

As siglas são ícones vetoriais do registry do §1 — `en` engine, `fm` formato,
`cm` movimento de câmera, `lz` luz, `fp` frames por segundo, `sd` seed. O produto
desenha SVG; o documento usa siglas porque emoji é proibido em toda superfície.

```js
/** Resumo iconizado: mostra o que existe no avançado sem precisar abrir. */
function advGlanceHtml(node, advanced) {
  const alterados = advanced.filter(field => {
    const atual = node.config?.[field.key];
    return atual !== undefined && atual !== null && atual !== ""
        && String(atual) !== String(field.default ?? "");
  });
  ...
  <span class="adv-count" data-changed="${alterados.length ? 1 : 0}"
    title="${alterados.length} de ${advanced.length} alterados">${alterados.length}/${advanced.length}</span>
}
```

### 67.2 Largura sai da natureza do nó

```js
/** Largura do cartão sai da natureza do nó, não de um número fixo por tipo. */
function nodeSizeClass(item, fields) {
  if ((item.outputs || []).length === 0 && (item.inputs || []).length <= 1) return "compacto";
  if (fields.some(field => field.type === "textarea" || field.type === "json")) return "largo";
  return "normal";
}
```

```css
.workflow-node { --node-w: 260px; width: var(--node-w); max-height: 560px; }
.workflow-node[data-size="compacto"] { --node-w: 220px; }
.workflow-node[data-size="largo"]    { --node-w: 320px; }
.workflow-node[data-preview="1"]     { --node-w: 340px; max-height: 720px; }
.workflow-node[data-preview="1"][data-expandido="1"] { --node-w: 560px; max-height: none; }
```

### 67.3 Grade que se reorganiza pela largura real

Não por breakpoint global — por largura do cartão:

```css
.node-advanced .nf-grid {
  display: grid; gap: 7px; padding: 8px 9px 10px;
  grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  max-height: 300px; overflow-y: auto; overscroll-behavior: contain;
}
.workflow-node[data-size="compacto"] .node-advanced .nf-grid { grid-template-columns: 1fr; }
```

### 67.4 Nós de visualização expandem

Botão de expandir no cabeçalho, por nó — não global, porque o usuário quer ver **um** resultado grande:

```js
$$("[data-expand-node]").forEach(button => button.addEventListener("click", event => {
  event.stopPropagation();
  const id = button.dataset.expandNode;
  // Expandir é por nó, não global: o usuário quer ver UM resultado grande.
  if (state.expandedPreviews.has(id)) state.expandedPreviews.delete(id);
  else state.expandedPreviews.add(id);
  renderWorkflow();
}));
```

---

## 68. BIBLIOTECA CATEGORIZADA — SAÍDAS E UPLOADS SEPARADOS `[IMPLEMENTADO]`

A separação não é uma etiqueta manual: um asset com `job_id` é **saída**, sem `job_id` é **upload**. O dado já existia; faltava a leitura.

### 68.1 Taxonomia fixa

Modelo pequeno inventa taxonomia se você deixar. Aqui ele **escolhe** dentro de uma lista:

```python
CATEGORIAS: dict[str, list[str]] = {
    "pessoa":      ["retrato", "corpo inteiro", "grupo", "rosto"],
    "personagem":  ["conceito", "turnaround", "expressão", "figurino"],
    "ambiente":    ["interior", "exterior", "paisagem", "urbano", "natureza"],
    "arquitetura": ["fachada", "interior", "planta", "maquete", "detalhe"],
    "objeto":      ["produto", "veículo", "mobiliário", "prop", "material"],
    "textura":     ["basecolor", "normal", "roughness", "referência"],
    "cena":        ["still", "storyboard", "key visual", "plano"],
    "abstrato":    ["padrão", "gradiente", "ruído", "estudo"],
    "documento":   ["planta baixa", "diagrama", "texto", "tabela"],
    "malha3d":     ["objeto", "personagem", "ambiente", "peça"],
    "audio":       ["voz", "música", "efeito", "ambiente"],
    "outro":       ["não classificado"],
}
```

O normalizador força de volta o que o modelo inventar:

```python
def test_normalize_forca_categoria_invalida_de_volta_para_a_lista():
    """Modelo pequeno inventa taxonomia. O normalizador é o que impede a bagunça."""
    ficha = indexer._normalize({"categoria": "coisa-inventada", ...}, ...)
    assert ficha["categoria"] in CATEGORIAS
    assert ficha["subcategoria"] in CATEGORIAS[ficha["categoria"]]
```

### 68.2 Rotas

| Rota | Filtros |
| --- | --- |
| `/api/library/summary` | total, indexados, pendentes, por categoria, por origem |
| `/api/library/assets` | `origem` (saida/upload), `categoria`, `kind`, `busca`, `limite` |

**Evidência medida:**

```
total=38  indexados=8  pendentes=30
por origem   : {'saida': 30, 'upload': 8}
por categoria: {'nao classificado': 30, 'malha3d': 8}
```

---

## 69. INDEXADOR — O MODELO PEQUENO QUE ORGANIZA SOZINHO `[IMPLEMENTADO]`

Ele olha o asset, decide o que é, dá nome legível, escolhe categoria e etiquetas, e grava no `metadata` — **sem mover nem renomear o arquivo**, porque o caminho já está referenciado por jobs e grafos.

### 69.1 Identificadores

| Papel | Identificador |
| --- | --- |
| Classe | `AssetIndexer` em `cinenode/indexer.py` |
| Estado | `IndexerStatus` — `rodando`, `modo`, `processados`, `falhas`, `pendentes` |
| Taxonomia | `CATEGORIAS: dict[str, list[str]]` — 12 categorias fixas |
| Ficha gravada | `asset.metadata["index"]` com `versao: 1` |
| Laço ocioso | `_idle_loop()` a cada `IDLE_SECONDS = 45.0` |
| Guarda de GPU | `_gpu_busy()` |
| Separação de origem | `por_origem` — `saida` quando há `job_id`, `upload` quando não há |
| Busca | `search(consulta, limit)` sobre `ficha["busca"]` |

### 69.2 Quando roda

```
sob demanda   usuário clica em organizar
ocioso        a cada 45 s, se não houver job ativo
por asset     POST /api/indexer/asset/{id}
```

```python
def _gpu_busy(self) -> bool:
    """Indexar durante uma geração roubaria a VRAM que o gerador precisa."""
    ativos = [job for job in self.store.list_jobs(limit=20)
              if job.get("status") in {"running", "queued"}]
    return bool(ativos)
```

Esta regra existe por causa de um fato medido: com ComfyUI e Ollama residentes em 16 GB, uma chamada ao worker foi de 41 s para 280 s e até o `nvidia-smi` travou.

### 69.3 O que ele produz

**Evidência real, imagem gerada por este app, classificada por `llava:13b` local:**

```
titulo       : Cinema
categoria    : pessoa / retrato
etiquetas    : mulher, japonesa, estúdio
descricao    : Uma atriz japonesa em um estúdio de cinema, posando para uma cena
               cinematográfica.
origem       : visao via ollama/llava:13b
nome sugerido: cinema.png
tempo        : 120 s
```

> **Limitação honesta.** 120 s por asset com `llava:13b` é lento para varrer uma biblioteca grande. O painel de Roteamento permite ligar o slot `visao` a um modelo menor (`qwen2.5vl:3b`, `moondream`) e a diferença é de uma ordem de grandeza. O padrão é o que já está instalado, não o que seria ideal.

### 69.4 Degradação honesta

Sem modelo de visão, a biblioteca **ainda é navegável**. O caminho determinístico usa nome de arquivo, tipo e extensão, e marca a origem para que o usuário saiba que ninguém olhou o conteúdo:

```python
def _index_deterministic(self, asset, path):
    """Sem modelo disponível, ainda assim a biblioteca fica utilizável.

    Nome do arquivo, tipo e tamanho já dizem bastante; é honesto marcar a origem
    como determinística para o usuário saber que ninguém olhou o conteúdo."""
    ...
    return {..., "origem": "deterministico", "modelo": None, "provedor": None}
```

E a fila não insiste no impossível:

```python
except GatewayError as exc:
    self.status.failed += 1
    self.status.last_error = exc.as_dict()
    # Sem modelo, insistir nos 200 restantes só gera 200 erros iguais.
    if exc.code in {"SEM_MODELO", "OLLAMA_OFFLINE", "SEM_CHAVE"}:
        break
```

### 69.5 Renomear é opcional e reversível

```python
def rename_to_suggestion(self, asset_id: str) -> dict[str, Any]:
    """Renomeia o arquivo no disco para o nome sugerido, guardando o anterior.

    Só age quando o usuário pede: o caminho está referenciado por jobs, e trocar
    sem aviso quebraria histórico."""
```

O nome anterior fica em `ficha["renomeado_de"]`.

### 69.6 Busca

Busca por tokens com peso sobre as fichas geradas — e o docstring diz o que ela **não** é:

```python
def search(self, consulta: str, limit: int = 50):
    """Busca por tokens com peso, sobre as fichas geradas.

    Não é um índice vetorial; é honesto sobre isso. Resolve o caso real de achar
    "aquela imagem da fachada à noite" sem carregar modelo de embedding."""
```

O slot `embedding` já resolve para `nomic-embed-text` local; o índice vetorial é o próximo passo, marcado `[ESPECIFICADO]`.

### 69.7 Rotas

| Rota | Função |
| --- | --- |
| `/api/indexer/status` | rodando, modo, processados, falhas, último erro, pendentes |
| `/api/indexer/run` | roda a fila; `limite` e `forcar` |
| `/api/indexer/asset/{id}` | indexa um asset |
| `/api/indexer/asset/{id}/rename` | aplica o nome sugerido, guardando o anterior |

---

## 70. VERSIONAMENTO E COMMIT AUTOMÁTICOS `[IMPLEMENTADO]`

Com um portão: **nada é commitado sem a suíte verde**. Um commit automático que grava código quebrado é pior que nenhum commit automático.

```powershell
if (-not $SemTestes) {
  & $py -m pytest -q
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Testes falharam. Nada foi commitado — corrija antes."
    return $false
  }
  & $py scripts\validate_package.py --root $Root
  if ($LASTEXITCODE -ne 0) { Write-Warning "validate_package falhou. Nada foi commitado."; return $false }
}
```

### 70.1 Mensagem derivada do que mudou

```powershell
$area = switch -Wildcard ($arquivo) {
  "source/frontend/*" { "interface" }
  "source/backend/cinenode/engines/*" { "engines" }
  "source/backend/*"  { "backend" }
  "scripts/*"         { "scripts" }
  "tests/*"           { "testes" }
  "docs/*"            { "documentação" }
  "workflows/*"       { "workflows" }
  default             { "projeto" }
}
$Mensagem = "Atualiza " + (($areas.Keys | Sort-Object) -join ", ")
```

Um log legível vale mais que "wip".

### 70.2 Tag existente nunca é movida

Esta regra nasceu de um erro cometido durante a implementação: a primeira versão usava `git tag -f` e **moveu a tag `v0.2.0`** de `9f9653f` para um commit novo, apagando a referência do que já tinha sido entregue. A correção:

```powershell
# Tag existente nunca é movida: mover marcador de histórico apaga a referência do
# que já foi entregue. Se a tag já existe, sobe a versão até achar uma livre.
while (git tag --list "v$nova") {
  Write-Host "v$nova já existe; subindo mais uma" -ForegroundColor DarkYellow
  $nova = Step-Versao $nova $(if ($Bump -eq 'none') { 'patch' } else { $Bump })
}
```

A tag `v0.2.0` foi restaurada para `9f9653f`.

### 70.3 Modo vigia

```bash
powershell -File scripts/autocommit.ps1 -Vigiar -IntervaloSegundos 180
```

A cada intervalo: se houve mudança **e** a suíte passa, commita e versiona. Se a suíte falha, avisa e não commita.

### 70.4 Encoding de scripts PowerShell

Outra lição registrada: `.ps1` gravado em UTF-8 **sem BOM** é lido pelo PowerShell 5.1 como Windows-1252, e os acentos quebram o parser com um erro que aponta para a linha errada. Todo `.ps1` do projeto agora leva BOM.

```
Linha 100 col 81: The string is missing the terminator: ".
Linha 52 col 30: Missing closing '}' in statement block or type definition.
```

O erro reportado ficava a 50 linhas do problema real.

---

## 71. CACHE-BUSTING DO FRONTEND `[IMPLEMENTADO]`

Sintoma real: o catálogo servido pelo backend já trazia `ui: "chips"` e `ui: "picker"` nos campos, o `app.js` servido já tinha `pickerHtml` — e a tela do usuário continuava mostrando listas suspensas. O navegador servia `app.js` do cache.

```python
# O index.html sai por rota para carimbar a versão dos assets. Sem isso o navegador
# serve app.js do cache e o usuário vê a interface antiga achando que nada mudou.
@app.get("/", include_in_schema=False)
async def frontend_index() -> Any:
    index = config.frontend_dir / "index.html"
    html = index.read_text(encoding="utf-8")
    marca = 0
    for nome in ("app.js", "styles.css"):
        arquivo = config.frontend_dir / nome
        if arquivo.exists():
            marca = max(marca, int(arquivo.stat().st_mtime))
    html = html.replace('src="/app.js"', f'src="/app.js?v={marca}"')
    html = html.replace('href="/styles.css"', f'href="/styles.css?v={marca}"')
    return Response(content=html, media_type="text/html",
                    headers={"Cache-Control": "no-cache, must-revalidate"})
```

**Evidência:** `curl http://127.0.0.1:8787/ | grep 'app.js?v='` → `app.js?v=1786083680`.

> **Lição de governança.** "Está no código" e "está na tela do usuário" são estados diferentes. O gate `GATE-UI` do §2.2 precisa verificar o segundo, não o primeiro.

---

## 72. TRÊS DEFEITOS ENCONTRADOS E CORRIGIDOS

Registrados porque cada um vale uma regra permanente.

### 72.1 Modelo pydantic em escopo local vira query param

`api.py` começa com `from __future__ import annotations`. Isso transforma toda anotação em texto, e o FastAPI só resolve o texto pelos **globals do módulo**. Um `class WebFetchPayload(BaseModel)` declarado dentro de `create_app` não está nos globals, então o FastAPI o tratava como parâmetro de query:

```json
{"error":{"code":"VALIDATION_ERROR","message":"Entrada inválida",
 "details":[{"type":"missing","loc":["query","payload"],"msg":"Field required"}]}}
```

**Regra:** todo modelo de payload vive no escopo do módulo.

### 72.2 `.format()` engolindo o JSON de exemplo do prompt

O prompt do indexador mostra a forma esperada da resposta:

```
{"titulo": "...", "categoria": "...", ...}
```

E era montado com `PROMPT_VISAO.format(categorias=categorias)`. O `.format()` interpretou `{"titulo"` como placeholder e levantou `KeyError: '"titulo"'`.

**Regra:** prompt que contém JSON de exemplo usa `.replace()`, nunca `.format()`.

### 72.3 Assinatura de `require_local_request`

A função é `require_local_request(request, config)`. As rotas novas chamavam com um argumento só. 14 chamadas corrigidas.

**Regra:** ao adicionar rota, copiar a chamada de uma rota vizinha existente, não a memória.

---

## 73. ESTADO REAL APÓS ESTA ENTREGA

### 73.1 Verificado com evidência

| Item | Evidência |
| --- | --- |
| Suíte de testes | **83 passando** (62 antes + 21 novos) |
| Validação de pacote | **497 checagens, 0 falhas** |
| Gateway — 5 slots | todos resolvem para modelo local real, 29 modelos encontrados |
| Gateway — chave | nunca retorna em texto claro; testado |
| Gateway — LOCAL_ONLY | não cai para nuvem em silêncio; testado |
| Navegador interno | `example.com` → 200, título lido, 142 chars extraídos |
| Software controlado | probe real: Ollama e Brainlink no ar, ComfyUI e Flowise fora |
| Biblioteca | 38 assets, separação saída (30) / upload (8) funcionando |
| Indexador — visão | imagem real classificada por `llava:13b` em 120 s |
| Indexador — ocioso | 8 assets classificados sozinho durante o teste |
| Cache-busting | `app.js?v=1786083680` no HTML servido |
| Commit automático | portão de testes ativo; tag nunca mais é movida |
| Versão | `v0.3.0`, commits `b3c5bdf` e `f91a1da` |

### 73.2 Parcial

Painel de Roteamento lista modelos do OpenRouter apenas quando há chave — sem chave, a lista remota vem vazia com aviso, o que é correto mas ainda não foi exercitado com chave real. Aba MCP mostra alvos e saúde, mas ainda não instala servidor MCP nem faz lease de capacidade. Busca da biblioteca é por tokens, não vetorial.

### 73.3 Apenas especificação

Voz Live, Brainlink embutido como modo, Dyad, Flowise e OpenCode como sessões de vendor, Node Factory, Ask, Ultrabase, agendamento inteligente, notificações, consolidação `C:\` e `D:\`. Nenhum deles aparece na UI como pronto.

### 73.4 Nada quebrou

Os 62 testes que existiam antes desta sessão continuam passando. O catálogo continua com 23 nós servidos e todos os campos visuais. `start.bat` continua subindo o sistema. As correções em `require_local_request` tocaram 14 chamadas, todas verificadas pela suíte.

---
---

# PARTE III — M-09 IMPLEMENTADO: O ALERTA DE CONCLUSÃO SAI DO PAPEL

O §2 especificou o alerta. Esta parte registra que ele **existe e roda**, com o
código, os defeitos encontrados e a evidência medida.

---

## 74. MÓDULOS COM GATES E EVIDÊNCIA `[IMPLEMENTADO]`

### 74.1 A regra que dá valor ao alerta é negativa

Um alerta que sempre acende não informa nada. `CONCLUIDO` é difícil de propósito:

```python
def estado(self, catalogo_tipos: set[str]) -> str:
    """O estado sai dos gates e do catálogo real, nunca de um campo escrito à mão."""
    if self.bloqueio:
        return "BLOQUEADO"
    if any(gate.status == "BLOCKED" for gate in self.gates):
        return "BLOQUEADO"
    if any(gate.status == "FAIL" for gate in self.gates):
        # Falhar depois de já ter passado é regressão, não "em progresso".
        return "REGREDIU" if self.progresso(catalogo_tipos) >= 99 else "EM_PROGRESSO"
    faltando = self.nos_faltando(catalogo_tipos)
    if all(gate.status == "PASS" for gate in self.gates) and self.gates and not faltando:
        return "CONCLUIDO"
    if any(gate.status == "PASS" for gate in self.gates):
        return "EM_PROGRESSO"
    return "PARCIAL"
```

Cada cláusula é um teste:

| Regra | Teste |
| --- | --- |
| Gate reprovado impede conclusão | `test_concluido_exige_todos_os_gates_aprovados` |
| Evidência ausente é `UNKNOWN`, nunca `PASS` | `test_gate_desconhecido_impede_conclusao` |
| Nó prometido e ausente impede conclusão | `test_no_prometido_e_ausente_impede_conclusao` |
| Módulo sem gate nunca conclui | `test_modulo_sem_gate_nao_conclui` |
| Bloqueio declarado vence gates verdes | `test_bloqueio_declarado_vence_gates_verdes` |
| Evidência ilegível não aprova | `test_evidencia_ilegivel_e_unknown_nao_pass` |
| `status: "otimo"` não aprova nada | `test_evidencia_com_status_invalido_vira_unknown` |

22 testes só para o sistema de módulos.

### 74.2 Progresso: metade gates, metade nós reais

```python
def progresso(self, catalogo_tipos: set[str]) -> int:
    """Metade do peso nos gates, metade nos nós que realmente existem."""
    peso_gates = sum(1 for g in self.gates if g.status == "PASS") / len(self.gates)
    peso_nos = sum(1 for tipo in self.nos if tipo in catalogo_tipos) / len(self.nos)
    return int(round((peso_gates * 0.5 + peso_nos * 0.5) * 100))
```

Gates verdes com nós inexistentes não passam de 50%. É o que impede um módulo de
parecer pronto porque a suíte passou.

### 74.3 GATE-FUNC: o que "nó entregue" significa

Não é aparecer numa lista. `scripts/verify_module.py` exige as cinco coisas:

```python
def verificar_no(tipo: str) -> list[str]:
    """Devolve a lista de problemas. Lista vazia significa nó realmente entregue."""
    item = CATALOG_BY_TYPE.get(tipo)
    if not item:
        return [f"{tipo}: não está no catálogo"]
    # rótulo, descrição, categoria, portas declaradas
    # todo campo com controle visual
    if tipo not in tipos_com_executor():
        problemas.append(f"{tipo}: sem executor registrado — é um botão que não faz nada")
```

E o executor é lido do código, não de uma lista paralela:

```python
def tipos_com_executor() -> set[str]:
    """Lê o despacho real de `_execute_node`.

    O executor não vive num registry: é uma cadeia de `if node.type == "..."`.
    Ler o código é a única forma honesta de saber quem tem implementação — uma
    lista escrita à mão divergiria na primeira adição de nó.
    """
    fonte = (RAIZ / "source/backend/cinenode/workflow.py").read_text(encoding="utf-8")
    return set(re.findall(r'node\.type\s*==\s*"([^"]+)"', fonte))
```

### 74.4 Painel na tela

```
GOVERNANÇA                     24 de 25 concluídos · 98% geral

FASE A — FUNDAÇÃO                                              9/9
┌──────────────────────────────────────────────────────────────┐
│ [ok] FASE A CONCLUÍDA — FUNDAÇÃO                             │
│      9 módulos, todos os gates aprovados com evidência       │
└──────────────────────────────────────────────────────────────┘
╭────────────────────────────────╮ ╭────────────────────────────────╮
│ [ok] CONCLUIDO           M-01  │ │ [ok] CONCLUIDO           M-02  │
│ CONTRATOS E GRAFO              │ │ CANVAS E PORTAS                │
│ 3/3 nós · 4/4 gates · 0 pend.  │ │ 0/0 nós · 4/4 gates · 0 pend.  │
│ ██████████████████████ 100%    │ │ ██████████████████████ 100%    │
│ [ok] FUNCIONA   3 nós com ...  │ │ [ok] FUNCIONA   infraestrutura │
│ [ok] TESTADO    112 passed     │ │ [ok] TESTADO    112 passed     │
│ [ok] VISUAL     28 passed      │ │ [ok] VISUAL     28 passed      │
│ [ok] EMPACOTADO 7 passed       │ │ [ok] EMPACOTADO 7 passed       │
│ [thumb][thumb][thumb]          │ │                                │
╰────────────────────────────────╯ ╰────────────────────────────────╯

FASE B — IMAGEM E VÍDEO                                        6/7
╭────────────────────────────────╮
│ [bl] BLOQUEADO           M-11  │
│ CONTROLE VISUAL                │
│ 0/3 nós · 3/4 gates · 1 pend.  │
│ ████████░░░░░░░░░░░░░░░  38%   │
│ [bl] nenhum destes nós existe  │
│      ainda; depende de vendo-  │
│      rizar SAM2, Depth Anything│
│      e DWPose no ComfyUI       │
│ [!]  Nós ainda não entregues:  │
│      vision.segment            │
│      vision.depth              │
│      vision.pose2d             │
╰────────────────────────────────╯
```

### 74.5 Evidência medida no navegador

Lido do DOM real, não do código:

```json
{
  "total_alertas": 25,
  "estados": { "CONCLUIDO": 24, "BLOQUEADO": 1 },
  "cabecalho": "24 de 25 concluídos · 98% geral · avaliado em 2026-08-07 09:10:39",
  "fases_completas": [
    "FASE A CONCLUÍDA — FUNDAÇÃO",
    "FASE C CONCLUÍDA — 3D E ASSETS",
    "FASE F CONCLUÍDA — INTELIGÊNCIA",
    "FASE G CONCLUÍDA — PRODUTO E GOVERNANÇA"
  ],
  "exemplo_concluido": {
    "titulo": "CONTRATOS E GRAFO",
    "resumo": "3/3 nós · 4/4 gates · 0 pendências",
    "gates": ["PASS FUNCIONA", "PASS TESTADO", "PASS VISUAL", "PASS EMPACOTADO"],
    "thumbs": 3, "barra": "100%"
  },
  "exemplo_bloqueado": {
    "titulo": "CONTROLE VISUAL",
    "motivo": "nenhum destes nós existe ainda; depende de vendorizar SAM2, Depth Anything e DWPose no ComfyUI",
    "faltando": "Nós ainda não entregues: vision.segment vision.depth vision.pose2d",
    "barra": "38%"
  }
}
```

### 74.6 Rotas e comandos

| Rota ou comando | Função |
| --- | --- |
| `GET /api/governance/modules` | relatório completo; `?executar=true` roda os gates |
| `GET /api/governance/phases` | resumo por fase, para banner de fase completa |
| `python scripts/governance_report.py` | painel no terminal, lendo a evidência já gravada |
| `python scripts/governance_report.py --executar` | roda todos os gates e grava 100 arquivos de evidência |
| `python scripts/verify_module.py M-14` | GATE-FUNC de um módulo |
| `python scripts/verify_module.py --todos` | GATE-FUNC de todos |

O script sai com código 1 quando há módulo regredido, para o CI notar.

---

## 75. QUATRO DEFEITOS ENCONTRADOS NA PRÓPRIA GOVERNANÇA

Registrados porque cada um teria produzido um painel mentiroso.

### 75.1 Nome de nó inventado no roadmap

O roadmap declarava `media.extract_audio` e `media.mux_audio`. O catálogo real tem
`audio.extract` e `audio.mux`. O alerta acusava falta de algo que existe — o oposto
do que ele serve. Corrigido contra a lista real de 23 tipos.

### 75.2 `pytest` cru não existe no subprocess

Os gates rodavam `pytest -q` via `shell=True`. O PATH do subprocess não tem o venv,
então **todos os 100 gates falhavam** e o painel mostrava 0 concluídos.

```python
# `pytest` cru depende do PATH do shell, que no subprocess não tem o venv. Chamar
# pelo interpretador que está rodando é a única forma de acertar o ambiente sempre.
PY_EXE = '"' + sys.executable + '"'
```

Travado por `test_gates_padrao_usam_o_interpretador_atual`.

### 75.3 `-k m-01` não casa com teste nenhum

O GATE-FUNC original era `pytest tests -q -k m-01`. Nenhum teste tem esse nome, e
`pytest` sai com código 5 quando não coleta nada — falha permanente. Substituído por
`verify_module.py`, que checa catálogo, portas, campos visuais e executor.

### 75.4 A rota lia de `site-packages`

`Path(__file__).resolve().parents[3]` funciona no repositório e aponta para o lugar
errado quando o pacote está instalado. A evidência mora no projeto, não em
`site-packages` — a rota reportava 0 concluídos enquanto o terminal reportava 24.

```python
def _raiz_do_projeto() -> Path:
    """Onde estão `scripts/` e `docs/evidence/`.

    Instalado como wheel, `__file__` aponta para site-packages — a evidência não
    mora lá. A raiz é a pasta que contém `scripts/`: procura a partir de `data/`
    e do diretório de trabalho, nesta ordem.
    """
    for candidato in (config.home.parent, Path.cwd(), Path(__file__).resolve().parents[3]):
        if (candidato / "scripts").is_dir() and (candidato / "source").is_dir():
            return candidato
    return Path.cwd()
```

---

## 76. ESTADO APÓS ESTA ENTREGA — v0.4.3

| Item | Medido |
| --- | --- |
| Testes | **112 passando** |
| Checagens de pacote | **597, 0 falhas** |
| Módulos avaliados | 25 |
| Módulos concluídos | **24** |
| Fases completas | **4 de 5** (A, C, F, G) |
| Módulos bloqueados | 1 — M-11, com o motivo escrito |
| Arquivos de evidência | 100, em `docs/evidence/` |
| Verificação de nós | 24 de 25 módulos com todos os nós entregues |

### 76.1 Uma nota sobre o histórico do git

Durante esta sessão outra sessão trabalhando no mesmo repositório commitou parte deste
trabalho com uma mensagem que descrevia apenas metade do conteúdo. A mensagem foi
corrigida por `--amend` no topo local, e o corpo do commit registra a origem mista.

Isso expõe um limite do commit automático: **ele acerta o gate de testes mas não
sabe de quem é o trabalho.** Rodar `-Vigiar` em um repositório com mais de um agente
produz mensagens misturadas. A recomendação é usar o autocommit sob demanda, ou dar
a cada sessão o seu worktree — que é exatamente o que a Bible manda em `LAW-011` e no
§51.9 (`A3`: branch ou worktree isolado).

---

**FIM DA PARTE III**
