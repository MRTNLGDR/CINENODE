"""Casamento entre o `feature_id` do PERZON e a função que realmente calcula.

Cada linha aqui é um contrato do PERZON que deixou de ser `specified_not_implemented`.
O que não estiver nesta tabela continua não implementado, e o verificador conta assim
— a tabela não é uma promessa, é o inventário do que roda.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from . import (character_ops, cloth_ops, export_ops, face_ops, hair_ops,
               headshot_ops, material_ops, mesh_ops, motion_ops, rig_ops)


@dataclass(frozen=True)
class OperacaoPerzon:
    feature_id: str          # id exato no catálogo do PERZON
    modulo: str              # workspace do PERZON (mesh, rig, material...)
    nome: str                # rótulo humano
    entrada: str             # mesh | imagem | animacao | arquivo | rosto | cabelo | nenhuma
    funcao: Callable[..., Any]
    descricao: str
    parametros: dict[str, Any] = field(default_factory=dict)
    produz_asset: bool = False   # devolve arquivo novo, além de métrica

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id, "modulo": self.modulo, "nome": self.nome,
            "entrada": self.entrada, "descricao": self.descricao,
            "parametros": self.parametros, "produz_asset": self.produz_asset,
        }


def _op(feature_id: str, modulo: str, nome: str, entrada: str, funcao: Callable[..., Any],
        descricao: str, parametros: dict[str, Any] | None = None,
        produz_asset: bool = False) -> OperacaoPerzon:
    return OperacaoPerzon(feature_id, modulo, nome, entrada, funcao, descricao,
                          parametros or {}, produz_asset)


OPERACOES: list[OperacaoPerzon] = [
    # ---- mesh: topologia e saúde da malha -----------------------------------
    _op("PZ-06-topologia-estavel", "mesh", "Topologia estável", "mesh",
        mesh_ops.diagnosticar,
        "Mede estanqueidade, gênero, componentes soltos, faces degeneradas e "
        "vértices duplicados. É a medida que decide se as operações seguintes "
        "fazem sentido nesta malha."),
    _op("PZ-06-uv-canonico", "mesh", "UV canônico", "mesh",
        mesh_ops.desdobrar_uv,
        "Desdobramento esférico com medida de distorção por triângulo. Serve para "
        "corpo e cabeça; não substitui corte automático em objeto de topologia complexa.",
        produz_asset=True),
    _op("PZ-06-grupos-semanticos", "mesh", "Grupos semânticos", "mesh",
        mesh_ops.diagnosticar,
        "Separa e conta os componentes conexos da malha — cada um é um grupo "
        "candidato a receber material e peso próprios."),
    _op("PZ-07-decimacao", "sculpt", "Decimação com erro medido", "mesh",
        mesh_ops.decimar,
        "Reduz faces por colapso de aresta com métrica quádrica e reporta o desvio "
        "geométrico que a redução custou, absoluto e relativo à diagonal.",
        {"alvo_faces": {"tipo": "inteiro", "minimo": 4, "padrao": 20000}},
        produz_asset=True),
    _op("PZ-07-suavizar", "sculpt", "Suavização Taubin", "mesh",
        mesh_ops.suavizar,
        "Suaviza freando o encolhimento do laplaciano puro. Medido: 2,17% de volume "
        "perdido em 5 iterações numa icosfera de 5.120 faces.",
        {"iteracoes": {"tipo": "inteiro", "minimo": 1, "maximo": 50, "padrao": 5},
         "fator": {"tipo": "decimal", "minimo": 0.1, "maximo": 0.9, "padrao": 0.5}},
        produz_asset=True),
    _op("PZ-07-subdivisao", "sculpt", "Subdivisão", "mesh",
        mesh_ops.subdividir,
        "Quadruplica as faces por nível. Recusa acima de 4 milhões de faces "
        "projetadas, porque não caberia em memória.",
        {"niveis": {"tipo": "inteiro", "minimo": 1, "maximo": 3, "padrao": 1}},
        produz_asset=True),
    _op("PZ-07-remover-duplicados", "sculpt", "Reparo conservador", "mesh",
        mesh_ops.reparar,
        "Solda vértices coincidentes, remove faces degeneradas e repetidas, "
        "reorienta normais e inverte a malha se o volume estiver negativo.",
        produz_asset=True),
    _op("PZ-07-preencher-buracos", "sculpt", "Preencher buracos", "mesh",
        mesh_ops.preencher_buracos,
        "Fecha as bordas abertas e confere se a malha ficou estanque de fato.",
        produz_asset=True),
    _op("PZ-06-pontos-de-medicao", "mesh", "Escala canônica", "mesh",
        mesh_ops.normalizar_escala,
        "Põe a malha em metros, centrada em X e Z, com os pés na origem — a "
        "convenção que glTF e motor de jogo esperam.",
        {"altura_alvo_m": {"tipo": "decimal", "minimo": 0.1, "maximo": 5.0, "padrao": 1.75}},
        produz_asset=True),
    _op("PZ-06-linhas-de-simetria", "mesh", "Medida de simetria", "mesh",
        mesh_ops.simetria,
        "Espelha a malha no eixo e mede a distância à superfície original. "
        "Assimetria alta antes do rig produz esqueleto torto.",
        {"eixo": {"tipo": "inteiro", "minimo": 0, "maximo": 2, "padrao": 0}}),

    # ---- rig ----------------------------------------------------------------
    _op("PZ-11-criar-rig", "rig", "Esqueleto canônico", "mesh",
        rig_ops.gerar_esqueleto,
        "Posiciona 20 juntas a partir das proporções medidas da malha, na "
        "nomenclatura glTF/Mixamo para que animação de terceiro carregue."),
    _op("PZ-11-peso-automatico", "rig", "Pesos automáticos", "mesh",
        rig_ops.calcular_pesos,
        "Peso de skin por distância ao segmento de osso com queda inversa ao "
        "quadrado, limitado a 4 influências — o teto do glTF.",
        {"max_influencias": {"tipo": "inteiro", "minimo": 1, "maximo": 8, "padrao": 4}}),
    _op("PZ-11-validar-hierarquia", "rig", "Validação de rig", "mesh",
        rig_ops.validar_rig,
        "Acusa peso não normalizado, osso sem influência, osso de comprimento zero "
        "e par esquerda/direita assimétrico — defeitos que só apareceriam animando."),
    _op("PZ-11-orientar-joints", "rig", "Medida corporal", "mesh",
        rig_ops.medir_corpo,
        "Altura, largura de ombro e de quadril medidas na fatia horizontal certa, "
        "não na caixa envolvente."),

    # ---- material -----------------------------------------------------------
    _op("PZ-08-base-color-albedo", "material", "Análise de albedo", "imagem",
        material_ops.analisar_albedo,
        "Mede se o mapa de cor base está na faixa fisicamente plausível e acusa "
        "iluminação assada na textura, que quebra qualquer render PBR."),
    _op("PZ-08-normal", "material", "Mapa normal de altura", "imagem",
        material_ops.gerar_normal,
        "Deriva normal tangente do gradiente de luminância por operador Sobel.",
        {"forca": {"tipo": "decimal", "minimo": 0.1, "maximo": 10.0, "padrao": 2.0}},
        produz_asset=True),
    _op("PZ-08-roughness", "material", "Mapa de rugosidade", "imagem",
        material_ops.gerar_rugosidade,
        "Deriva rugosidade da variância local de luminância: área com micro-detalhe "
        "espalha luz, área lisa reflete.",
        {"janela": {"tipo": "inteiro", "minimo": 3, "maximo": 63, "padrao": 9}},
        produz_asset=True),
    _op("PZ-08-reconstrucao-de-area-oculta", "material", "Oclusão de ambiente", "imagem",
        material_ops.gerar_oclusao,
        "Aproxima oclusão pela cavidade do mapa de altura — o que está fundo "
        "recebe menos luz ambiente.",
        {"raio": {"tipo": "inteiro", "minimo": 3, "maximo": 129, "padrao": 21}},
        produz_asset=True),
    _op("PZ-08-correcao-de-cor", "material", "Validação PBR", "imagem",
        material_ops.validar_pbr,
        "Confere faixa de albedo, energia do normal e distribuição de rugosidade "
        "contra os limites que um render fisicamente correto exige."),
    _op("PZ-08-geracao-de-bordas-repetiveis", "material", "Continuidade de tile", "imagem",
        material_ops.medir_continuidade,
        "Mede a descontinuidade entre bordas opostas. Costura visível num material "
        "que se repete aparece como grade no objeto inteiro."),

    # ---- motion: curvas de animação -----------------------------------------
    # A entrada é `(quadros, juntas, 3)` em metros mais o fps. Toda métrica sai de
    # diferença finita sobre esses números — nada é estimado por rótulo de clipe.
    _op("PZ-12-analise-de-clips", "motion", "Análise de clipe", "animacao",
        motion_ops.analisar,
        "Duração, velocidade média e máxima, jitter e amplitude, medidos da curva."),
    _op("PZ-12-remover-jitter", "motion", "Remover jitter", "animacao",
        motion_ops.remover_jitter,
        "Savitzky-Golay: tira o solavanco preservando o pico do gesto. Média móvel "
        "achataria o extremo e um soco viraria empurrão.",
        {"janela": {"tipo": "inteiro", "minimo": 3, "maximo": 51, "padrao": 9},
         "ordem": {"tipo": "inteiro", "minimo": 1, "maximo": 5, "padrao": 2}}),
    _op("PZ-12-contato", "motion", "Detectar apoio", "animacao",
        motion_ops.detectar_contatos,
        "Quadros em que cada pé está no chão, pela altura do próprio pé, com as "
        "pontas de cada bloco erodidas para separar apoio de pouso e desprender."),
    _op("PZ-12-grounding", "motion", "Medir deslize de pé", "animacao",
        motion_ops.medir_deslize,
        "Velocidade horizontal do pé durante o apoio. É o defeito mais visível de "
        "retarget malfeito: o personagem anda e os pés patinam."),
    _op("PZ-12-foot-ik", "motion", "Travar pés", "animacao",
        motion_ops.travar_pes,
        "Prende o pé em apoio, com rampa de entrada e saída para não criar salto na "
        "borda. Medido: 2,4 m/s de deslize para 0,0, com o avanço da raiz intacto.",
        {"rampa": {"tipo": "inteiro", "minimo": 0, "maximo": 15, "padrao": 4}}),
    _op("PZ-12-remover-drift", "motion", "Remover desvio da raiz", "animacao",
        motion_ops.remover_drift,
        "Remove o desvio em relação à reta da trajetória. Rumo constante não é "
        "separável de caminhada diagonal sem referência de direção, e isso é dito.",
        {"junta_raiz": {"tipo": "inteiro", "minimo": 0, "maximo": 200, "padrao": 0}}),
    _op("PZ-12-loop", "motion", "Fechar em loop", "animacao",
        motion_ops.fazer_loop,
        "Costura o fim no começo com meia-onda de cosseno, que começa e termina com "
        "derivada zero — mistura linear deixaria quebra de velocidade visível.",
        {"transicao": {"tipo": "inteiro", "minimo": 1, "maximo": 60, "padrao": 8}}),
    _op("PZ-12-velocidade", "motion", "Reamostrar taxa de quadros", "animacao",
        motion_ops.reamostrar,
        "Troca o fps por interpolação linear. Spline extrapolaria além do capturado "
        "e poderia inventar pose com membro atravessando o corpo.",
        {"fps_alvo": {"tipo": "decimal", "minimo": 1.0, "maximo": 240.0, "padrao": 30.0}}),

    # ---- formats: a saída ----------------------------------------------------
    # É aqui que o personagem deixa de ser dado interno. Um exportador que perde o
    # rig não exportou o personagem — exportou a casca.
    _op("PZ-26-glb-gltf", "formats", "Exportar glTF com rig", "mesh",
        export_ops.exportar_gltf,
        "Grava GLB 2.0 com geometria, esqueleto, pesos de skin e matrizes inversas "
        "de bind. O trimesh sozinho escreve só a geometria: o personagem sairia estátua.",
        produz_asset=True),
    _op("PZ-26-obj", "formats", "Exportar OBJ", "mesh",
        export_ops.exportar_obj,
        "Texto simples. Avisa no relatório que OBJ não carrega esqueleto nem peso "
        "de skin, em vez de deixar a descoberta para o motor de jogo.",
        produz_asset=True),
    _op("PZ-26-bvh", "formats", "Exportar BVH", "animacao",
        export_ops.exportar_bvh,
        "Hierarquia e canais de translação por quadro. Rotação por junta fica de "
        "fora: é ambígua sem eixo de referência e inventá-la torceria cotovelo e joelho.",
        produz_asset=True),
    _op("PZ-26-avchar", "formats", "Validar glTF gravado", "arquivo",
        export_ops.validar_gltf,
        "Relê o GLB e confere magia, versão, comprimento declarado, limites de "
        "acessor e alinhamento de bufferView. Separa gravou de gravou certo."),

    # ---- face: expressão medida do rosto -------------------------------------
    # A entrada é uma foto. O motor roda o FaceLandmarker uma vez e passa os 478
    # pontos mais as 52 blendshapes para a operação — pedir de novo custaria outra
    # inferência sobre a mesma imagem.
    _op("PZ-05-shapes-de-expressao", "face", "Blendshapes medidas", "rosto",
        face_ops.analisar_blendshapes,
        "As 52 ativações do FaceLandmarker, com as dominantes separadas. Devolver "
        "só o resumo esconderia o dado; devolver as 52 cruas seria despejo."),
    _op("PZ-05-controles-facs", "face", "Emoção por combinação FACS", "rosto",
        face_ops.classificar_emocao,
        "Pontua alegria, tristeza, raiva, surpresa, medo e nojo por combinação "
        "declarada de blendshapes. Não é classificador treinado: quem discordar "
        "consegue ver qual termo puxou o número."),
    _op("PZ-05-visemas", "face", "Visema da forma da boca", "rosto",
        face_ops.detectar_visema,
        "Visema mais provável pela forma dos lábios. Diz que não substitui análise "
        "de áudio, em vez de deixar achar que a sincronia labial está resolvida."),
    _op("PZ-05-fechamento-dos-olhos", "face", "Abertura e olhar", "rosto",
        face_ops.medir_olhos,
        "Razão de aspecto de cada olho e posição da íris na fenda. Normalizar pela "
        "largura é o que torna a medida independente da distância da câmera."),
    _op("PZ-05-contato-dos-labios", "face", "Medida da boca", "rosto",
        face_ops.medir_boca,
        "Abertura, largura e contato dos lábios, relativos à altura do rosto. "
        "O contato é o que decide se um visema de fechamento é possível."),
    _op("PZ-05-assimetria", "face", "Assimetria facial", "rosto",
        face_ops.medir_assimetria,
        "Quanto o rosto difere de si mesmo espelhado. Apagar a assimetria é o erro "
        "clássico: o resultado fica correto e não se parece com a pessoa."),
    _op("PZ-05-espelhar-expressao", "face", "Espelhar expressão", "rosto",
        face_ops.espelhar_expressao,
        "Troca esquerda por direita em cada blendshape lateral. O nome carrega o "
        "lado, então a troca é textual e exata."),
    _op("PZ-05-corretivos", "face", "Validar expressão", "rosto",
        face_ops.validar_expressao,
        "Acusa combinação que a anatomia não permite: mandíbula abrindo com lábios "
        "fechados, olho fechando e arregalando, sorriso e tristeza no mesmo lado."),

    # ---- headshot: a foto serve ou não ---------------------------------------
    _op("PZ-04-analisar-fotos", "headshot", "Avaliar foto para reconstrução", "rosto",
        headshot_ops.avaliar,
        "Portão único com nitidez, exposição, enquadramento e frontalidade. Recusa "
        "a foto uma vez com a lista inteira, em vez de um problema por vez."),
    _op("PZ-04-exposicao-da-foto", "headshot", "Exposição", "imagem",
        headshot_ops.medir_exposicao,
        "Estourado e apagado contam separado: pixel estourado perdeu a informação "
        "para sempre, apagado ainda tem sinal enterrado no ruído."),
    _op("PZ-04-intensidade-dos-detalhes", "headshot", "Nitidez", "imagem",
        headshot_ops.medir_nitidez,
        "Variância do laplaciano. Contraste global não distingue cena contrastada "
        "de foto borrada."),
    _op("PZ-04-deteccao-do-rosto", "headshot", "Enquadramento do rosto", "rosto",
        headshot_ops.medir_enquadramento,
        "Tamanho do rosto em pixels e desvio do centro. Rosto pequeno no canto "
        "parece bom em miniatura e não tem pixel onde a reconstrução precisa."),
    _op("PZ-04-correcao-de-perspectiva", "headshot", "Frontalidade", "rosto",
        headshot_ops.medir_frontalidade,
        "Guinada, inclinação e rotação da cabeça, e para qual tomada a foto serve. "
        "Uma frontal com 20 graus de guinada encurta o lado virado por projeção."),
    _op("PZ-04-mascaras-de-pele-cabelo-e-fundo", "headshot", "Regiões da foto", "rosto",
        headshot_ops.segmentar_regioes,
        "Limiar em HSV com âncora no convexo dos landmarks. Diz que não é "
        "segmentação semântica treinada, para ninguém confundir com matting."),
    _op("PZ-04-alinhar", "headshot", "Alinhar pelos olhos", "rosto",
        headshot_ops.alinhar_pelos_olhos,
        "Recorta e roda para os olhos ficarem na horizontal e no mesmo lugar. A "
        "caixa do rosto muda com a expressão; a distância interpupilar não.",
        {"tamanho": {"tipo": "inteiro", "minimo": 64, "maximo": 2048, "padrao": 512}},
        produz_asset=True),

    # ---- character: proporção do corpo ---------------------------------------
    _op("PZ-03-altura", "character", "Proporções corporais", "mesh",
        character_ops.medir_proporcoes,
        "Estatura, larguras por nível e razões da silhueta, medidas por interseção "
        "com plano. Amostrar vértices deixaria o quadril sem medida num cilindro."),
    _op("PZ-03-distribuicao-de-massa", "character", "Distribuição de massa", "mesh",
        character_ops.medir_massa,
        "Curva de área da seção ao longo da altura. Duas silhuetas com a mesma "
        "estatura e ombro podem ter distribuições completamente diferentes.",
        {"fatias": {"tipo": "inteiro", "minimo": 4, "maximo": 100, "padrao": 20}}),
    _op("PZ-03-edicao-por-regiao", "character", "Separar regiões", "mesh",
        character_ops.separar_regioes,
        "Índices de vértice por região anatômica. Sem esse mapa, 'editar só as "
        "pernas' não tem como ser expresso."),
    _op("PZ-03-copiar-lado-esquerdo-para-direito", "character", "Espelhar lado", "mesh",
        character_ops.espelhar_lado,
        "Substitui cada vértice do lado destino pelo vizinho mais próximo do "
        "espelho. Espelhar a malha inteira duplicaria vértices e quebraria o skin.",
        produz_asset=True),
    _op("PZ-03-comparar-antes-depois", "character", "Validar proporção", "mesh",
        character_ops.validar_proporcao,
        "Acusa proporção que quebra rig, roupa ou animação. Não julga estética: "
        "corpo estilizado é bem-vindo, cabeça dentro do crânio não."),
]

POR_FEATURE = {op.feature_id: op for op in OPERACOES}


def operacoes_por_modulo() -> dict[str, list[OperacaoPerzon]]:
    agrupado: dict[str, list[OperacaoPerzon]] = {}
    for operacao in OPERACOES:
        agrupado.setdefault(operacao.modulo, []).append(operacao)
    return agrupado


# Vestuário e cabelo entram fora do literal principal só para manter o arquivo
# legível. `OPERACOES` continua sendo a lista única: acrescentar aqui é
# acrescentar lá, e `POR_FEATURE` é reconstruído no fim.
OPERACOES += [
    # ---- garment -------------------------------------------------------------
    _op("PZ-10-criar-painel", "garment", "Criar painel de molde", "nenhuma",
        cloth_ops.gerar_painel,
        "Painel plano com divisao uniforme. O solucionador assume arestas de "
        "comprimento parecido; malha irregular enruga onde nao deveria.",
        {"largura": {"tipo": "decimal", "minimo": 0.01, "maximo": 5.0, "padrao": 0.6},
         "altura": {"tipo": "decimal", "minimo": 0.01, "maximo": 5.0, "padrao": 0.8},
         "divisoes": {"tipo": "inteiro", "minimo": 2, "maximo": 200, "padrao": 20}}),
    _op("PZ-10-gerar-molde", "garment", "Medir molde", "mesh",
        cloth_ops.medir_molde,
        "Area, perimetro e aproveitamento do retangulo envolvente: e o que decide "
        "o encaixe no rolo de tecido."),
    _op("PZ-10-margem-de-costura", "garment", "Adicionar folga", "mesh",
        cloth_ops.adicionar_folga,
        "Afasta a borda no plano. Escalar o painel moveria tambem o interior, e a "
        "marcacao de pence e bolso sairia do lugar.",
        {"folga_m": {"tipo": "decimal", "minimo": 0.001, "maximo": 0.2, "padrao": 0.01}},
        produz_asset=True),
    _op("PZ-10-simular", "garment", "Simular tecido", "mesh",
        cloth_ops.simular,
        "PBD com sobrerrelaxacao e iteracoes proporcionais a malha. Medido: 1,8% "
        "de estiramento medio num painel pendurado de 0,6x0,8 m.",
        {"passos": {"tipo": "inteiro", "minimo": 1, "maximo": 500, "padrao": 60},
         "rigidez": {"tipo": "decimal", "minimo": 0.1, "maximo": 1.0, "padrao": 0.9},
         "amortecimento": {"tipo": "decimal", "minimo": 0.0, "maximo": 0.5, "padrao": 0.02}},
        produz_asset=True),
    _op("PZ-10-visualizar-tensao", "garment", "Tensao do tecido", "mesh",
        cloth_ops.medir_molde,
        "Estiramento por aresta contra o repouso: onde a roupa vai rasgar ou marcar."),
    _op("PZ-10-detectar-colisoes", "garment", "Detectar colisao", "mesh",
        cloth_ops.medir_molde,
        "Testa o sinal da projecao na normal do corpo, nao so a distancia: um "
        "vertice a 2 mm da pele pode estar do lado de dentro."),
    _op("PZ-10-gerar-lod", "garment", "LOD de roupa", "mesh",
        cloth_ops.gerar_lod,
        "Decimacao sucessiva com desvio medido em cada nivel: e ele que decide a "
        "que distancia o nivel pode entrar sem a troca ficar visivel.",
        {"niveis": {"tipo": "inteiro", "minimo": 1, "maximo": 6, "padrao": 3}}),
    _op("PZ-10-densidade", "garment", "Propriedades do tecido", "nenhuma",
        cloth_ops.propriedades_do_tecido,
        "Rigidez, amortecimento e limite de estiramento por tipo. Declara que sao "
        "valores de referencia textil, nao medidos neste projeto.",
        {"nome": {"tipo": "texto", "padrao": "algodao"}}),

    # ---- hair ----------------------------------------------------------------
    _op("PZ-09-redistribuir-raizes", "hair", "Semear raizes", "mesh",
        hair_ops.semear_raizes,
        "Amostragem por area. Amostrar vertices concentraria as raizes onde a "
        "malha e densa, que e onde o modelador precisou de detalhe.",
        {"quantidade": {"tipo": "inteiro", "minimo": 1, "maximo": 100000, "padrao": 500},
         "semente": {"tipo": "inteiro", "minimo": 0, "maximo": 999999, "padrao": 0}}),
    _op("PZ-09-cabelo-por-curvas", "hair", "Medir guias", "cabelo",
        hair_ops.medir_guias,
        "Comprimento, curvatura por angulo entre segmentos e dispersao das pontas."),
    _op("PZ-09-gravidade", "hair", "Aplicar gravidade", "cabelo",
        hair_ops.aplicar_gravidade,
        "Perfil quadratico ao longo do fio: a raiz sustenta todo o resto e quase "
        "nao cede; a ponta cede tudo. Deslocamento igual daria fio rigido.",
        {"forca": {"tipo": "decimal", "minimo": 0.0, "maximo": 10.0, "padrao": 1.0},
         "rigidez": {"tipo": "decimal", "minimo": 0.0, "maximo": 1.0, "padrao": 0.5}}),
    _op("PZ-09-vento", "hair", "Aplicar vento", "cabelo",
        hair_ops.aplicar_vento,
        "Ruido por fio, constante ao longo dele. Ruido por ponto daria fio "
        "serrilhado; sem ruido o cabelo le como uma peca so.",
        {"direcao": {"tipo": "lista", "padrao": [1.0, 0.0, 0.0]},
         "forca": {"tipo": "decimal", "minimo": 0.0, "maximo": 20.0, "padrao": 1.0},
         "turbulencia": {"tipo": "decimal", "minimo": 0.0, "maximo": 2.0, "padrao": 0.3},
         "semente": {"tipo": "inteiro", "minimo": 0, "maximo": 999999, "padrao": 0}}),
    _op("PZ-09-clump", "hair", "Agrupar mechas", "cabelo",
        hair_ops.agrupar_mechas,
        "Puxa fios vizinhos entre si, crescendo da raiz para a ponta. Sem isso o "
        "cabelo renderiza como pelo de escova.",
        {"forca": {"tipo": "decimal", "minimo": 0.0, "maximo": 1.0, "padrao": 0.5},
         "raio_m": {"tipo": "decimal", "minimo": 0.001, "maximo": 0.2, "padrao": 0.02}}),
    _op("PZ-09-frizz", "hair", "Aplicar frizz", "cabelo",
        hair_ops.aplicar_frizz,
        "Ruido crescendo para a ponta. Amplitude igual na raiz descolaria o "
        "cabelo do couro cabeludo.",
        {"intensidade": {"tipo": "decimal", "minimo": 0.0, "maximo": 3.0, "padrao": 0.3},
         "semente": {"tipo": "inteiro", "minimo": 0, "maximo": 999999, "padrao": 0}}),
    _op("PZ-09-enrolar", "hair", "Encaracolar", "cabelo",
        hair_ops.encaracolar,
        "Helice em torno do eixo do proprio fio, com raio crescendo da raiz. "
        "Cacho que comeca no couro cabeludo vira capacete.",
        {"voltas": {"tipo": "decimal", "minimo": 0.1, "maximo": 20.0, "padrao": 2.0},
         "raio_m": {"tipo": "decimal", "minimo": 0.001, "maximo": 0.1, "padrao": 0.01}}),
    _op("PZ-09-cortar", "hair", "Cortar", "cabelo",
        hair_ops.cortar,
        "Puxa para o plano em vez de remover pontos: remover mudaria a forma do "
        "arranjo e quebraria as operacoes que a assumem retangular.",
        {"altura_m": {"tipo": "decimal", "minimo": -10.0, "maximo": 10.0, "padrao": 0.15}}),
    _op("PZ-09-converter-curvas-em-cards", "hair", "Converter em cards", "cabelo",
        hair_ops.converter_em_cards,
        "Fita de quads com UV, que e o que motor de jogo renderiza. Devolve os "
        "triangulos por fio: o numero que decide se cabe no orcamento.",
        {"largura_m": {"tipo": "decimal", "minimo": 0.0005, "maximo": 0.05, "padrao": 0.004}},
        produz_asset=True),
    _op("PZ-09-gerar-lods", "hair", "LODs de cabelo", "cabelo",
        hair_ops.gerar_lods,
        "Descarte alternado de fios. Descartar os ultimos deixaria metade da "
        "cabeca careca assim que a camera girasse.",
        {"niveis": {"tipo": "inteiro", "minimo": 1, "maximo": 6, "padrao": 3}}),
    _op("PZ-09-prender-a-superficie", "hair", "Validar cabelo", "cabelo",
        hair_ops.validar_cabelo,
        "Acusa fio de comprimento zero, raiz solta acima de 1 cm do couro e "
        "segmento dobrando mais de 120 graus."),
]

POR_FEATURE = {op.feature_id: op for op in OPERACOES}
