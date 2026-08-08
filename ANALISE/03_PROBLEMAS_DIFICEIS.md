# Os problemas genuinamente difíceis

Difícil aqui não significa trabalhoso. Significa que **existe uma armadilha
específica** que faz a solução óbvia produzir um resultado que parece certo e
está errado. Cada item abaixo nomeia a armadilha.

---

## 1. VRAM: o teto que nenhuma engenharia contorna

| medida | valor |
|---|---|
| VRAM total | 16.376 MiB |
| pico do job de vídeo | **15.752 MiB** |
| livre com desktop aberto | ~13.200 MiB |

**A armadilha:** otimizar o que é fácil de medir (tempo de CPU, tamanho de
código) e não o que trava. Vídeo no máximo não roda hoje, e nenhuma reescrita de
linguagem muda isso.

**O que de fato ajuda:** quantização mais agressiva, offload de camadas para a
RAM, geração em blocos de quadros. Todos custam qualidade ou tempo, e a escolha é
do usuário — o que o sistema deve fazer é **medir e avisar antes**, não falhar no
meio.

---

## 2. Autocolisão de tecido

Hoje `cloth_ops.simular` colide o tecido com o **corpo**. Não colide o tecido
**consigo mesmo**.

**A armadilha:** parece um detalhe e é o que separa roupa de plástico. Sem
autocolisão, uma saia atravessa a própria dobra, uma manga entra no torso, e o
resultado só aparece em movimento.

**Por que é difícil:** colisão corpo-tecido é O(n) com uma árvore espacial sobre
uma malha estática. Autocolisão é O(n²) sobre uma malha que muda a cada passo —
a árvore precisa ser reconstruída, e o teste é triângulo contra triângulo, não
ponto contra superfície.

**Caminho:** hash espacial reconstruído por passo, com célula do tamanho da maior
aresta. Continua caro; a alternativa honesta é declarar que a simulação não
resolve autocolisão e mostrar onde ela ocorreria.

---

## 3. Convergência do solucionador de tecido

Medido no painel de 0,6 × 0,8 m pendurado:

| divisões | iterações | estiramento médio | máximo |
|---|---|---|---|
| 10 | 20 | 1,8% | 9,3% |
| 16 | 32 | 3,0% | 24,5% |
| 24 | 48 | 4,2% | 39,2% |

**Malha mais densa converge pior**, mesmo com iterações proporcionais.

**A armadilha:** em Jacobi a informação caminha **uma aresta por iteração**. Um
painel de 24 divisões precisa de ~24 iterações só para o vértice de baixo saber
que o de cima está preso. Aumentar iterações resolve linearmente um problema que
cresce com o tamanho.

**Caminho:** solucionador multigrid (resolver numa malha grossa e refinar) ou
XPBD com compliance, que dá rigidez independente do número de iterações. Ambos
são reescrita do núcleo, não ajuste de parâmetro.

---

## 4. Retarget de animação entre esqueletos diferentes

`motion_ops` hoje mede e corrige uma animação **no seu próprio esqueleto**.
Transferir para outro corpo é outro problema.

**A armadilha:** escalar as posições pelo tamanho do corpo parece resolver e
quebra o contato. Um personagem mais baixo com o mesmo passo escalado **não
alcança o chão** — os pés flutuam ou afundam, e o deslize que
`travar_pes` corrige volta multiplicado.

**Por que é difícil:** o que precisa ser preservado não é posição nem ângulo, é
**contato**: pé no chão, mão na maçaneta, dedo no gatilho. Isso é um problema de
otimização com restrições, não de transformação.

**Caminho:** IK com restrições de contato detectadas na animação de origem —
`detectar_contatos` já existe e é a base. O solucionador de IK não existe.

---

## 5. Desdobramento UV automático de qualidade

`mesh_ops.desdobrar_uv` faz projeção esférica e **mede a distorção**. Serve para
corpo e cabeça, que são topologicamente próximos de uma esfera.

**A armadilha:** projeção esférica em objeto de topologia complexa produz UV
tecnicamente válido e visualmente inútil — a textura estica na parte que importa,
e a medida de distorção acusa mas não conserta.

**Por que é difícil:** o desdobramento bom exige **decidir onde cortar**, e o
corte ótimo é um problema combinatório sobre o grafo da malha.

**Caminho:** integrar `xatlas` (MIT, C++ com binding Python). É reuso, não
pesquisa — e é exatamente o tipo de caso em que escrever do zero seria erro.

---

## 6. Reconstrução facial a partir de uma foto

`headshot_ops` mede se a foto **serve**. Não reconstrói o rosto em 3D.

**A armadilha:** parece que medir landmarks já dá a geometria. Não dá: 478 pontos
2D projetados não determinam profundidade. Duas cabeças de formatos diferentes
produzem os mesmos landmarks vistas de frente.

**Por que é difícil:** exige um modelo estatístico de rostos (3DMM) treinado, que
resolve a ambiguidade com um prior. FLAME e DECA existem; **as licenças são
restritivas para uso comercial** e nenhum está no disco.

**Caminho honesto:** ou aceitar a licença explicitamente, ou reconstruir de
múltiplas fotos por fotogrametria — que é mais trabalho e não tem o problema
de licença. `comparar_fotos` já existe e é o começo disso.

---

## 7. Voz: a parte fácil e a parte bloqueada

**Implementável hoje, sem modelo:** RMS e ganho, detecção de silêncio por
energia, pitch por autocorrelação, bandas de energia → visema aproximado,
abertura de mandíbula a partir da envoltória.

**Bloqueado sem modelo:** transcrição (Whisper), texto-para-voz, alinhamento
fonema-a-tempo.

**A armadilha:** o alinhamento por energia parece resolver a sincronia labial e
não resolve. Energia alta não distingue "AH" de "OH" — as duas têm a mesma
potência e formas de boca opostas. Sem análise de formante ou sem transcrição
alinhada, o resultado é uma boca que abre e fecha no ritmo certo dizendo coisa
nenhuma.

---

## 8. Colisão de cabelo

`hair_ops` preserva comprimento em toda deformação — medido, desvio 0,000000.
Não colide.

**A armadilha:** cabelo que atravessa o ombro é o defeito mais visível de
personagem em movimento, e a correção ingênua (empurrar o ponto para fora)
**quebra o comprimento do fio**, que é justamente o invariante que o módulo
protege.

**Por que é difícil:** as duas restrições competem. Resolver colisão move o
ponto; preservar comprimento move de volta. Precisa de projeção iterativa
alternada, com convergência não garantida.

---

## 9. Pesos de skin de qualidade

`rig_ops.calcular_pesos` usa distância ao segmento de osso com queda inversa ao
quadrado. Funciona, soma 1 em todo vértice, e o vértice do pé segue o pé.

**A armadilha:** distância euclidiana **atravessa o corpo**. Um vértice na parte
interna da coxa esquerda está geometricamente perto do osso da coxa direita, e
recebe peso dele. O resultado: mover uma perna arrasta a pele da outra.

**Por que é difícil:** a distância correta é **geodésica dentro do volume**, não
euclidiana no espaço. É o que `heat weights` (Baran & Popović) resolve, com
difusão de calor sobre a malha.

**Caminho:** `PZ-11-heat-weights` está no catálogo e não implementado. Exige
resolver uma equação de Laplace sobre o volume — scipy tem os solucionadores; o
trabalho é a discretização.

---

## 10. Governança contra fadiga de alerta

Medido agora: **5 alertas abertos**, 25 componentes com licença não conferida.

**A armadilha:** um painel que acusa tudo deixa de ser lido. E um painel que
silencia para parecer verde é pior.

**O que já foi feito:** alerta tem id permanente, reexecutar a auditoria atualiza
em vez de duplicar, e alerta resolvido que volta é **reaberto** preservando a
evidência anterior. O gate de licença tem escopo por módulo, porque a primeira
versão reprovava o módulo de vídeo por causa de uma licença de 3D — e gate que
acusa quem não tem culpa é gate que o time aprende a ignorar.

**O que falta:** `SEC-003`, trilha à prova de adulteração. Hoje o log pode ser
editado sem deixar rastro.

---

## 11. O problema meta: contrato sem cálculo

O PERZON é o caso extremo — 1697 contratos exatos, zero cálculo. Mas o padrão
reaparece em escala menor toda vez que se escreve a interface antes do algoritmo.

**A defesa que está no código:** operação sem cálculo recusa com código nomeado.
O verificador conta separadamente o que o PERZON declara e o que executa aqui.
Somar os dois num número só esconderia exatamente a diferença que importa.
