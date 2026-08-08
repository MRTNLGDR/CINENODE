# Guia de auditoria — onde procurar defeito neste código

Este arquivo existe para você **não perder tempo** onde já foi olhado, e gastar
atenção onde o risco é real.

O código está em `codigo/`: 128 arquivos, 33.547 linhas, 1,6 MB. Você consegue
ler tudo. Você **não** consegue executar nada — não há pesos, binários, banco nem
saídas no pacote, de propósito: eles somam 105 GB e não se lê defeito neles.

---

## 1. Onde o risco é maior, em ordem

### 1.1 `codigo/backend/perzon/` — 12 arquivos, o cálculo novo

É onde 71 operações fazem matemática sobre geometria, pixel e áudio. **É o código
mais novo e o menos exercitado em produção.** Cada função devolve um número que
alguém vai acreditar.

Pergunte a cada uma:

- O número devolvido **depende da entrada**, ou é uma constante disfarçada?
  (Foi assim que `cabecas_de_altura` devolvia 7,69 para qualquer corpo.)
- A operação **preserva o invariante** que promete? Fio de cabelo não estica,
  peso de skin soma 1, comprimento de osso não muda.
- O que acontece com entrada **degenerada**: malha de altura zero, imagem de um
  pixel, animação de dois quadros, fio de comprimento zero.
- A medida é feita **onde diz que é feita**? Amostrar vértices e dizer que mede
  uma seção horizontal foi um defeito real: cilindro só tem vértice nas tampas.

Arquivos por ordem de risco:

| arquivo | por quê |
|---|---|
| `cloth_ops.py` | solucionador iterativo; já divergiu para 10¹⁵² uma vez |
| `character_ops.py` | detecção de pescoço por estrangulamento, heurística |
| `motion_ops.py` | convenção de derivada; já teve dois índices discordando |
| `hair_ops.py` | reprojeção de comprimento a cada deformação |
| `export_ops.py` | escreve binário glTF à mão; deslocamento errado = arquivo quebrado |
| `face_ops.py` | 20 índices de landmark fixos; um errado dá medida plausível e falsa |
| `rig_ops.py` | distância euclidiana atravessa o corpo (defeito conhecido, seção 4) |

### 1.2 `codigo/backend/api.py` — 1.100+ linhas, toda a superfície HTTP

- Rota literal registrada **depois** de rota com parâmetro é engolida por ela.
  (`/api/jobs/resumable` já foi vítima disso.)
- Toda rota deve chamar `require_local_request`. Procure alguma que não chame.
- Erro deve sair como `{"code", "message", "hint"}`. Procure `raise HTTPException`
  com `detail` em texto solto — a UI lê `detail.code`.
- `_endereco_permitido`: o guard de SSRF. `is_global` devolve `True` para
  multicast; confira se cada faixa está checada explicitamente.

### 1.3 `codigo/backend/workflow.py` — o catálogo e o executor

O `NODE_CATALOG` é fonte única para UI e worker. Um nó declarado sem executor
aparece na tela e falha ao rodar. Confira:

- Todo `type` do catálogo tem ramo em `_execute_node`.
- Todo campo `select` tem `default` dentro de `options`.
- Todo campo `number` tem `default` dentro de `min..max`.
- As portas usam a grafia `nome:tipo` com sufixo `?` ou `*` — **acabou de mudar**,
  e é o lugar mais provável de haver inconsistência agora.

### 1.4 `codigo/frontend/app.js` — 3.300 linhas, uma função `render()`

- `render()` faz `app.innerHTML = shell(content)`: **destrói e recria o DOM
  inteiro**. Procure tudo que guarda referência a elemento entre renders — foi
  assim que o visualizador GLB vazou contexto WebGL.
- Procure `${...}` em template de HTML sem `escapeHtml` sobre dado que veio do
  servidor ou do usuário.
- Procure listener adicionado sem ser removido, em elemento que o render destrói.
- Estado de tela: `carregando`, `erro` e `vazio` são três coisas diferentes.
  Metade das telas ainda não distingue as três (ver seção 3).

### 1.5 `codigo/backend/database.py` — 5 migrações

- `executescript` emite COMMIT implícito: falha no meio deixa a migração pela
  metade com a versão já registrada. Por isso existe `MIGRATION_OBJECTS`.
- `ALTER TABLE ADD COLUMN` não é idempotente; por isso existe `COLUMN_ADDITIONS`
  com verificação de `PRAGMA table_info`.
- Confira se toda migração nova entrou nos dois registros.

---

## 2. Onde NÃO gastar tempo

Estes já foram medidos e estão corretos. Reportá-los é ruído.

| já verificado | resultado |
|---|---|
| XSS por interpolação | `toast()` usa `textContent`; todo caminho HTML escapa |
| `data-action` órfão | 10 declarados, 10 com listener |
| `target=_blank` | 4, todos com `rel=noopener` |
| foreign keys | ligadas na conexão do app, `foreign_key_check` limpo |
| WAL | ativo |
| chave de provedor no backup | removida antes de zipar (`backup.py`) |
| `:focus-visible` | presente em toda a interface |
| `prefers-reduced-motion` | respeitado |
| vazamento de contexto WebGL | corrigido: `Map` iterável + `dispose()` completo |

---

## 3. Defeitos conhecidos e ainda abertos

Não precisa encontrá-los. **Precisa dizer se há outros como estes.**

| defeito | onde | efeito |
|---|---|---|
| autocolisão de tecido ausente | `cloth_ops.simular` | saia atravessa a própria dobra |
| colisão de cabelo ausente | `hair_ops` | cabelo atravessa o ombro |
| peso de skin por distância euclidiana | `rig_ops.calcular_pesos` | mover uma perna arrasta a pele da outra |
| convergência cai com malha densa | `cloth_ops` | 1,8% de estiramento com 10 divisões, 4,2% com 24 |
| estados de tela incompletos | `app.js` | `dashboard`, `projects`, `workflow`, `gallery` sem estado de erro; 6 de 8 sem estado de carregando |
| trilha de auditoria adulterável | `governance.py` | log pode ser editado sem deixar rastro |
| custom nodes do ComfyUI sem sandbox | `engines/` | código de terceiro roda sem isolamento |
| 3 licenças `UNKNOWN_BLOCKED` | `registry_models.py` | LLaVA, Z-Image-Turbo, Hunyuan3D |
| 25 de 29 licenças não conferidas no disco | `registry_models.py` | vieram do card upstream |

---

## 4. O padrão que mais produziu defeito aqui

Em **20 defeitos reais** encontrados neste projeto (listados em
`04_DEFEITOS_ENCONTRADOS.md`), nenhum foi achado por leitura de código. Todos
apareceram quando um número medido não bateu com o esperado.

Os três formatos recorrentes:

**Constante disfarçada de medida.** A função calcula, devolve, e o resultado não
depende da entrada. Teste mental: *se eu dobrar a entrada, o número muda?*

**Convenção divergente entre duas funções.** Uma usa diferença para trás, a outra
para frente; uma indexa de 0, a outra de 1. Cada uma está certa sozinha.

**Filtro que cega o detector para o próprio defeito.** Detecção de apoio exigia
velocidade baixa — e pé que escorrega tem velocidade alta, então sumia da lista.

Ao ler cada função, aplique os três.

---

## 5. Formato útil de resposta

Para cada achado:

1. **arquivo:linha**
2. **entrada concreta** que produz o erro
3. **o que sai** contra **o que deveria sair**
4. por que a leitura casual não pega

Um achado com entrada concreta vale mais que dez observações genéricas. Se não
conseguir construir a entrada que falha, provavelmente não é defeito — é estilo.
