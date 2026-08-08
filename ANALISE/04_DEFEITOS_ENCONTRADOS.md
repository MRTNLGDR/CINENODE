# Defeitos que a medição pegou

Nenhum destes veio de leitura de código. Todos apareceram porque um número medido
não bateu com o que se esperava. Vários são erros meus, corrigidos na mesma
execução — estão aqui porque o padrão importa mais que a autoria.

## A classe mais perigosa: parece medida e é constante

**`cabecas_de_altura` era tautologia.** Calculava a altura da cabeça como
`1 - 0,870` da estatura, uma fração fixa. Devolvia **7,69 para qualquer corpo** —
um boneco de cabeça enorme e um humano normal recebiam o mesmo número.

Correção: o pescoço passou a ser detectado como **estrangulamento** — seção mais
estreita que a de cima *e* a de baixo. Medido depois: 7,4 cabeças no corpo
normal, **1,59 no cabeçudo**.

A primeira tentativa de correção também estava errada: pegava o mínimo global no
terço superior, que num corpo de cabeça grande cai no **topo do crânio**, onde a
esfera afina. Resultado: 20 cabeças de altura — o inverso exato do certo.

## Simulação que diverge e se chama estável

**PBD explodiu para 7×10¹⁵² metros.** Eu somava a correção de cada aresta ao
vértice sem dividir pelo número de arestas. Com 4 a 6 arestas por vértice e
rigidez 0,9, cada iteração multiplicava o erro.

A afirmação "PBD é incondicionalmente estável" vale para o método aplicado
certo, não para quem o invoca pelo nome.

Depois da divisão, o estiramento ainda era de 115%: em Jacobi a informação anda
**uma aresta por iteração**, e 8 iterações fixas não atravessam um painel de 16
divisões. Iterações proporcionais à malha + sobrerrelaxação trouxeram para 1,8%.

## Amostragem que parece equivalente e não é

**Cilindro do trimesh só tem vértice nas duas tampas.** Medir largura coletando
vértices numa faixa horizontal deixava quadril, joelho e peito **sem medida** num
corpo perfeitamente medível. O fallback devolvia a largura da caixa envolvente —
exatamente o que a função existia para não fazer: ombro de 1,10 m num corpo cujo
ombro tem 0,63 m.

Correção: interseção com plano, que corta as arestas onde elas cruzam a altura.

## Convenção divergente entre duas funções

**`detectar_contatos` usava diferença para trás, `medir_deslize` para frente.**
O mesmo índice apontava para quadros diferentes, e o último quadro de apoio era
medido com a velocidade do balanço seguinte. Uma caminhada com o pé cravado
durante todo o apoio acusava **3,0 m/s de deslize**.

## Filtro que cega o detector para o próprio defeito

**Detecção de apoio exigia velocidade baixa.** Parece razoável e é
autodestrutivo: um pé que escorrega tem velocidade alta, some da lista de
contatos, e o detector fica cego exatamente para o defeito que existe para achar.
Medido: numa caminhada com deslize injetado, a versão com filtro reportava
**0,0 m/s** porque descartara todos os quadros ruins.

## Correção que piora e o teste que não vê

**`travar_pes` levou o deslize de 0,64 para 0,94 m/s** — piorou. Eu comparava
antes e depois **redetectando** os contatos, o que compara dois conjuntos
diferentes de quadros. Medir nos mesmos quadros expôs a piora.

## Exportador que entrega a casca

**GLB sem `skin`.** O `trimesh` exporta geometria e nada de esqueleto: o
personagem sai estátua. E na primeira versão do exportador próprio, a raiz não
virava nó — os três ossos filhos do quadril viravam raízes soltas e o esqueleto
saía **partido em três árvores** que se desmontam na primeira pose.

## Limiar calibrado no lugar errado

**Luz assada não era detectada.** O borrão gaussiano de raio grande achatava as
pontas: uma rampa de 0,059–0,769 virava 0,148–0,474, e o sinal que devia acusar
sumia. Reduzir a imagem por área é passa-baixa sem esse defeito.

O limiar também estava alto: 0,35 deixava passar rampa de 2:1, que é luz assada
de verdade. Recalibrado para 0,20 contra medição em rampas conhecidas.

## Infraestrutura

- **O venv guardava cópia do pacote, não a fonte.** Servidor rodava 0.7.0 com a
  fonte em 0.7.2; toda edição exigia reinstalar, e sem reinstalar servia código
  velho em silêncio. Era a causa da "UI antiga" que confundiu antes.
- **`set_alert_status` existia sem rota nenhuma** — código morto desde sempre.
- **Regiões do corpo se sobrepunham**: vértice em duas regiões recebe a edição
  duas vezes.
- **`ndarray.ptp()` foi removido no NumPy 2.**
- **A fixture de humanoide tinha os membros deitados** — o cilindro do trimesh
  nasce ao longo de Z, não de Y.
- **`is_global` devolve True para multicast** (224.0.0.1): o guard de SSRF
  deixava passar.
- **`/api/jobs/{job_id}` engolia `/api/jobs/resumable`** — FastAPI casa na ordem
  de registro.
- **A chave do OpenRouter ia em texto puro dentro do backup.**
- **Autocommit gravava BOM no `pyproject.toml`**, quebrando `pip install`, e o
  defeito ficava escondido porque o servidor rodava do pacote antigo.

## O padrão

Em todos os casos, o código estava escrito de forma plausível e o defeito só
apareceu quando alguém comparou um número medido com o número esperado. Revisão
de código não teria pego nenhum destes.
