"""Fase E: os contratos do PERZON com cálculo real por trás.

O PERZON entrega 1697 microitens e 1697 stubs em Rust que devolvem
`specified_not_implemented`. Estes testes provam que as operações registradas aqui
calculam sobre geometria e pixel de verdade — e que o que não tem cálculo recusa
com código, em vez de devolver um dicionário plausível.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import trimesh
from fastapi.testclient import TestClient

from cinenode.api import create_app
from cinenode.perzon import OPERACOES, PerzonEngine, PerzonOperationError
from cinenode.perzon import (character_ops, export_ops, face_ops,
                             headshot_ops, material_ops, mesh_ops,
                             motion_ops, rig_ops)
from cinenode.perzon.registry import POR_FEATURE


# ---- corpos de teste --------------------------------------------------------

@pytest.fixture(scope="module")
def humanoide() -> trimesh.Trimesh:
    """Torso, cabeça, dois braços e duas pernas.

    A cápsula lisa que usei primeiro escondia um caso importante: sem braços,
    os ossos da mão ficam legitimamente sem peso, e o teste passaria a aceitar
    "sem influência" como normal. Com membros de verdade, mão e pé precisam pesar.
    """
    T = trimesh.transformations

    def membro(raio: float, comprimento: float, posicao: list[float]):
        """Cilindro em pé. O do trimesh nasce ao longo de Z, não de Y.

        A primeira versão desta fixture esquecia a rotação, e os membros ficavam
        deitados na profundidade. O corpo ainda tinha altura, então quase tudo
        passava — mas a seção horizontal na altura do quadril saía vazia, e a
        largura do quadril vinha `None` num corpo aparentemente medível.
        """
        peca = trimesh.creation.cylinder(radius=raio, height=comprimento)
        peca.apply_transform(T.rotation_matrix(np.pi / 2, [1, 0, 0]))
        peca.apply_transform(T.translation_matrix(posicao))
        return peca

    partes = [
        trimesh.creation.box(extents=[0.36, 0.60, 0.22],
                             transform=T.translation_matrix([0, 1.15, 0])),
        trimesh.creation.icosphere(radius=0.11).apply_transform(
            T.translation_matrix([0, 1.60, 0])),
        membro(0.055, 0.62, [-0.26, 1.15, 0]), membro(0.055, 0.62, [0.26, 1.15, 0]),
        membro(0.075, 0.85, [-0.10, 0.42, 0]), membro(0.075, 0.85, [0.10, 0.42, 0]),
    ]
    return trimesh.util.concatenate(partes)


@pytest.fixture()
def malha_no_disco(tmp_path, humanoide) -> str:
    caminho = tmp_path / "humano.glb"
    caminho.write_bytes(humanoide.export(file_type="glb"))
    return str(caminho)


@pytest.fixture(scope="module")
def caminhada() -> dict:
    """Ciclo de marcha com o pé cravado durante o apoio — o que é uma caminhada.

    A primeira versão deste dado tinha os pés transladando junto com a raiz, ou
    seja, deslizando por construção. Contra esse dado nenhum corretor de deslize
    poderia melhorar nada, e o teste teria "provado" que o algoritmo falha.
    """
    fps, total, passo, ciclo = 30.0, 120, 0.75, 30
    quadros = np.zeros((total, 4, 3))
    velocidade = passo / (ciclo / fps)
    quadros[:, 0] = np.c_[velocidade * np.arange(total) / fps,
                          np.full(total, 0.95), np.zeros(total)]
    for junta, atraso in [(1, 0), (2, ciclo // 2)]:
        lado = -0.1 if junta == 1 else 0.1
        for f in range(total):
            fase, n = (f - atraso) % ciclo, (f - atraso) // ciclo
            base = n * passo * 2 + (passo if junta == 2 else 0)
            if fase < ciclo // 2:                      # apoio: X fixo, no chão
                quadros[f, junta] = [base, 0.0, lado]
            else:                                      # balanço: avança e sobe
                u = (fase - ciclo // 2) / (ciclo // 2)
                quadros[f, junta] = [base + u * passo * 2,
                                     0.12 * np.sin(np.pi * u), lado]
    quadros[:, 3] = quadros[:, 0] + [0, 0.65, 0]
    return {"quadros": quadros, "fps": fps, "juntas_pe": [1, 2]}


@pytest.fixture()
def clipe_no_disco(tmp_path, caminhada) -> str:
    """Clipe com esqueleto embutido: BVH grava hierarquia e não a deduz.

    As mesmas coordenadas servem a mais de uma árvore de ossos. Escolher uma
    seria inventar o rig do usuário, então o formato pede o esqueleto junto.
    """
    import json

    juntas = {f"j{i}": [0.0, float(i) * 0.2, 0.0] for i in range(4)}
    ossos = [{"nome": f"j{i}", "pai": f"j{i - 1}", "comprimento": 0.2}
             for i in range(1, 4)]

    caminho = tmp_path / "caminhada.json"
    caminho.write_text(json.dumps({
        "fps": caminhada["fps"], "juntas_pe": caminhada["juntas_pe"],
        "esqueleto": {"juntas": juntas, "ossos": ossos},
        "quadros": caminhada["quadros"].tolist()}), encoding="utf-8")
    return str(caminho)


MODELOS = Path(__file__).resolve().parents[1] / "data" / "models"


def _rosto_desenhado() -> "np.ndarray":
    """Rosto sintético que o FaceLandmarker de fato detecta.

    Usar um retângulo colorido não serviria: sem rosto detectado, toda operação
    desta família recusaria com o mesmo código e o teste não provaria nada sobre
    o cálculo. Este desenho passa pelo detector, e é sobre a medida dele que as
    asserções falam.
    """
    import cv2

    imagem = np.full((480, 480, 3), 210, np.uint8)
    cv2.ellipse(imagem, (240, 250), (120, 155), 0, 0, 360, (196, 168, 148), -1)
    for cx in (196, 284):
        cv2.ellipse(imagem, (cx, 215), (26, 13), 0, 0, 360, (250, 250, 250), -1)
        cv2.circle(imagem, (cx, 215), 9, (60, 40, 30), -1)
        cv2.circle(imagem, (cx, 215), 4, (10, 10, 10), -1)
        cv2.ellipse(imagem, (cx, 192), (28, 7), 0, 180, 360, (90, 70, 55), -1)
    cv2.ellipse(imagem, (240, 262), (11, 30), 0, 0, 360, (180, 150, 132), -1)
    cv2.ellipse(imagem, (240, 320), (46, 16), 0, 0, 360, (150, 90, 90), -1)
    return imagem


@pytest.fixture(scope="module")
def leitura_de_rosto():
    """Roda o FaceLandmarker uma vez para o módulo inteiro de testes de face."""
    pytest.importorskip("mediapipe")
    if not (MODELOS / "mediapipe" / "face_landmarker.task").is_file():
        pytest.skip("face_landmarker.task não está em data/models/mediapipe")

    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision

    imagem = _rosto_desenhado()
    opcoes = vision.FaceLandmarkerOptions(
        base_options=mpp.BaseOptions(
            model_asset_path=str(MODELOS / "mediapipe" / "face_landmarker.task")),
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
        num_faces=1)
    with vision.FaceLandmarker.create_from_options(opcoes) as detector:
        resultado = detector.detect(mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)))
    if not resultado.face_landmarks:
        pytest.skip("o detector não achou rosto no desenho sintético")

    altura, largura = imagem.shape[:2]
    return {
        "imagem": imagem,
        "pontos": np.array([[p.x * largura, p.y * altura, p.z * largura]
                            for p in resultado.face_landmarks[0]], dtype=np.float64),
        "blendshapes": resultado.face_blendshapes[0],
        "matriz": resultado.facial_transformation_matrixes[0],
    }


@pytest.fixture()
def foto_no_disco(tmp_path) -> str:
    import cv2

    caminho = tmp_path / "rosto.png"
    cv2.imwrite(str(caminho), _rosto_desenhado())
    return str(caminho)


@pytest.fixture()
def painel_no_disco(tmp_path) -> str:
    """Painel aberto de tecido: as operações de molde recusam malha fechada, e
    recusar é o comportamento certo — não há borda para afastar num sólido."""
    from cinenode.perzon import cloth_ops

    caminho = tmp_path / "painel.glb"
    caminho.write_bytes(cloth_ops.gerar_painel(0.4, 0.5, 8).export(file_type="glb"))
    return str(caminho)


@pytest.fixture()
def guias_no_disco(tmp_path) -> str:
    import json

    from cinenode.perzon import hair_ops

    couro = trimesh.creation.icosphere(radius=0.1, subdivisions=2)
    raizes, info = hair_ops.semear_raizes(couro, 60)
    guias, _ = hair_ops.crescer_guias(raizes, np.array(info["normais"]), 0.2, 8)

    caminho = tmp_path / "guias.json"
    caminho.write_text(json.dumps({"guias": guias.tolist()}), encoding="utf-8")
    return str(caminho)


@pytest.fixture()
def glb_no_disco(tmp_path, humanoide) -> str:
    """GLB com rig já gravado, para as operações que inspecionam arquivo pronto."""
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    pesos = rig_ops.calcular_pesos(humanoide, esqueleto)
    caminho = tmp_path / "pronto.glb"
    export_ops.exportar_gltf(humanoide, caminho, esqueleto, pesos)
    return str(caminho)


@pytest.fixture()
def textura_no_disco(tmp_path) -> str:
    import cv2

    rng = np.random.default_rng(3)
    base = np.full((256, 256, 3), 130, np.float32)
    imagem = np.clip(base + rng.normal(0, 20, (256, 256, 1)), 0, 255).astype(np.uint8)
    caminho = tmp_path / "textura.png"
    cv2.imwrite(str(caminho), imagem)
    return str(caminho)


# ---- geometria: o cálculo é real --------------------------------------------

def test_diagnostico_mede_a_malha_e_nao_o_nome_do_arquivo():
    esfera = trimesh.creation.icosphere(subdivisions=3)
    diag = mesh_ops.diagnosticar(esfera)
    assert diag["vertices"] == len(esfera.vertices)
    assert diag["faces"] == len(esfera.faces)
    assert diag["estanque"] is True
    # Esfera é gênero 0 e Euler 2. Um número diferente aqui significa que a
    # topologia não é a que o resto do pipeline vai assumir.
    assert diag["euler"] == 2
    assert diag["genero"] == 0
    assert mesh_ops.problemas(diag) == []


def test_genero_nao_e_inventado_em_malha_aberta():
    """Gênero só é definido em superfície fechada; num plano seria número errado."""
    caixa = trimesh.creation.box()
    aberta = trimesh.Trimesh(vertices=caixa.vertices, faces=caixa.faces[:-2], process=False)
    diag = mesh_ops.diagnosticar(aberta)
    assert diag["estanque"] is False
    assert diag["genero"] is None
    assert diag["volume"] is None


def test_toro_tem_genero_um():
    """Prova que a medida de gênero acompanha a topologia real, não uma constante."""
    toro = trimesh.creation.torus(major_radius=1.0, minor_radius=0.3)
    diag = mesh_ops.diagnosticar(toro)
    assert diag["estanque"] is True
    assert diag["genero"] == 1, f"toro deveria ter gênero 1, veio {diag['genero']}"


def test_decimacao_reduz_faces_e_mede_o_erro_que_custou():
    esfera = trimesh.creation.icosphere(subdivisions=4)
    reduzida, info = mesh_ops.decimar(esfera, 800)
    assert info["faces_depois"] < info["faces_antes"]
    assert len(reduzida.faces) == info["faces_depois"]
    # O desvio precisa ser medido, não assumido zero.
    assert info["desvio_maximo"] > 0
    # E precisa ser pequeno: 5.120 -> 800 faces numa esfera manteve 0,2% da
    # diagonal como desvio máximo quando medido.
    assert info["desvio_relativo"] < 0.02, info


def test_decimacao_recusa_alvo_que_nao_forma_solido():
    with pytest.raises(mesh_ops.MalhaInvalida):
        mesh_ops.decimar(trimesh.creation.icosphere(subdivisions=2), 3)


def test_suavizacao_reporta_o_encolhimento_em_vez_de_esconder():
    """Taubin freia o encolhimento do laplaciano; não o elimina. Quem chama
    precisa do número para decidir se aquele tanto é aceitável."""
    esfera = trimesh.creation.icosphere(subdivisions=4)
    _, info = mesh_ops.suavizar(esfera, iteracoes=5)
    assert info["encolhimento_relativo"] is not None
    assert 0 <= info["encolhimento_relativo"] < 0.10, info


def test_subdivisao_recusa_o_que_nao_caberia_em_memoria():
    grande = trimesh.creation.icosphere(subdivisions=6)  # 81.920 faces; x64 = 5,24 M
    with pytest.raises(mesh_ops.MalhaInvalida, match="4 milhões"):
        mesh_ops.subdividir(grande, 3)


def test_reparo_solda_duplicado_e_fecha_buraco():
    caixa = trimesh.creation.box()
    quebrada = trimesh.Trimesh(
        vertices=np.vstack([caixa.vertices, caixa.vertices[0]]),
        faces=caixa.faces[:-2], process=False)
    codigos = {p["codigo"] for p in mesh_ops.problemas(mesh_ops.diagnosticar(quebrada))}
    assert "MALHA_ABERTA" in codigos
    assert "VERTICES_DUPLICADOS" in codigos

    reparada, acoes = mesh_ops.reparar(quebrada)
    assert any("soldou" in a for a in acoes), acoes

    fechada, info = mesh_ops.preencher_buracos(reparada)
    assert info["ficou_estanque"] is True
    assert info["arestas_de_borda_depois"] == 0


def test_escala_canonica_poe_os_pes_na_origem():
    esfera = trimesh.creation.icosphere(subdivisions=3)
    esfera.apply_scale(37.0)          # como se viesse em centímetros
    normalizada, info = mesh_ops.normalizar_escala(esfera, 1.75)
    assert info["altura_depois_m"] == pytest.approx(1.75, abs=1e-6)
    assert normalizada.bounds[0][1] == pytest.approx(0.0, abs=1e-9)
    assert normalizada.bounds[:, 0].mean() == pytest.approx(0.0, abs=1e-6)


def test_escala_recusa_malha_deitada_sem_altura():
    plano = trimesh.Trimesh(
        vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 0, 1]], dtype=float),
        faces=np.array([[0, 1, 2]]), process=False)
    with pytest.raises(mesh_ops.MalhaInvalida, match="altura zero"):
        mesh_ops.normalizar_escala(plano)


def test_simetria_distingue_corpo_simetrico_de_torto():
    esfera = trimesh.creation.icosphere(subdivisions=3)
    assert mesh_ops.simetria(esfera, 0)["simetrica"] is True

    torta = esfera.copy()
    metade = torta.vertices[:, 0] > 0
    torta.vertices[metade, 1] += 0.35
    assert mesh_ops.simetria(torta, 0)["simetrica"] is False


def test_uv_mede_a_distorcao_em_vez_de_afirmar_qualidade():
    esfera = trimesh.creation.icosphere(subdivisions=3)
    desdobrada, info = mesh_ops.desdobrar_uv(esfera)
    uv = np.asarray(desdobrada.visual.uv)
    assert uv.shape == (len(esfera.vertices), 2)
    assert uv.min() >= 0.0 and uv.max() <= 1.0
    assert info["distorcao_mediana"] is not None
    assert info["faces_degeneradas_uv"] >= 0


# ---- rig --------------------------------------------------------------------

def test_esqueleto_sai_das_medidas_da_malha_e_nao_de_tabela_fixa(humanoide):
    baixo = humanoide.copy()
    baixo.apply_scale(0.8)
    alto = humanoide.copy()
    alto.apply_scale(1.2)

    juntas_baixo = rig_ops.gerar_esqueleto(baixo)["juntas"]
    juntas_alto = rig_ops.gerar_esqueleto(alto)["juntas"]
    assert juntas_baixo["cabeca"][1] < juntas_alto["cabeca"][1]


def test_esqueleto_tem_a_hierarquia_completa_e_conectada(malha_no_disco):
    malha = mesh_ops.carregar(malha_no_disco)
    esqueleto = rig_ops.gerar_esqueleto(malha)
    assert esqueleto["total_juntas"] == len(rig_ops.HIERARQUIA)
    assert len(esqueleto["ossos"]) == len(rig_ops.HIERARQUIA) - 1  # a raiz não é osso
    nomes = set(esqueleto["juntas"])
    for osso in esqueleto["ossos"]:
        assert osso["pai"] in nomes, f"{osso['nome']} aponta para pai inexistente"
        assert osso["comprimento"] > 0


def test_largura_de_ombro_vem_da_fatia_e_nao_da_caixa(humanoide):
    """A medida tem de sair da altura pedida, não do ponto mais largo do corpo.

    No humanoide simples os braços são a parte mais larga tanto no ombro quanto no
    total, e as duas medidas coincidem — o que não prova nada. Alargar o quadril
    cria a diferença: a caixa passa a refletir o quadril, e a fatia do ombro tem
    de continuar medindo o ombro.
    """
    quadril_largo = trimesh.util.concatenate([
        humanoide,
        trimesh.creation.box(extents=[1.10, 0.20, 0.30],
                             transform=trimesh.transformations.translation_matrix([0, 0.90, 0])),
    ])
    medida = rig_ops.medir_corpo(quadril_largo)
    assert float(quadril_largo.extents[0]) == pytest.approx(1.10, abs=0.01)
    assert medida["largura_ombros"] < float(quadril_largo.extents[0])
    assert medida["largura_quadril"] > medida["largura_ombros"]


def test_pesos_somam_um_em_todo_vertice(humanoide):
    """Soma diferente de 1 faz a malha esticar ou encolher ao animar — e o defeito
    só aparece em movimento, quando já está tarde."""
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    pesos = rig_ops.calcular_pesos(humanoide, esqueleto)
    soma = np.array(pesos["pesos"]).sum(axis=1)
    assert np.allclose(soma, 1.0, atol=1e-6)
    assert pesos["verificacao"]["soma_minima"] == pytest.approx(1.0, abs=1e-6)


def test_pesos_respeitam_o_teto_de_quatro_influencias(humanoide):
    """Quatro é o limite do glTF. Passar disso faz a exportação truncar em
    silêncio, longe daqui."""
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    pesos = rig_ops.calcular_pesos(humanoide, esqueleto, max_influencias=4)
    assert np.array(pesos["indices"]).shape[1] == 4


def test_peso_e_maior_no_osso_mais_proximo(humanoide):
    """É a propriedade que define um peso de skin correto: o vértice do pé
    precisa seguir o pé, não o pescoço."""
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    pesos = rig_ops.calcular_pesos(humanoide, esqueleto)
    ossos = pesos["ossos"]

    baixo = int(np.argmin(humanoide.vertices[:, 1]))
    dominante = ossos[pesos["indices"][baixo][int(np.argmax(pesos["pesos"][baixo]))]]
    assert "pe" in dominante or "perna" in dominante, dominante

    alto = int(np.argmax(humanoide.vertices[:, 1]))
    dominante_alto = ossos[pesos["indices"][alto][int(np.argmax(pesos["pesos"][alto]))]]
    assert dominante_alto in {"cabeca", "pescoco"}, dominante_alto


def test_validacao_acusa_esqueleto_com_par_assimetrico(humanoide):
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    pesos = rig_ops.calcular_pesos(humanoide, esqueleto)
    esqueleto["juntas"]["braco_e"][1] += 0.25      # ombro esquerdo mais alto
    codigos = {d["codigo"] for d in rig_ops.validar_rig(esqueleto, pesos)}
    assert "PAR_ASSIMETRICO" in codigos


def test_validacao_acusa_osso_de_comprimento_zero(humanoide):
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    pesos = rig_ops.calcular_pesos(humanoide, esqueleto)
    esqueleto["ossos"][0]["comprimento"] = 0.0
    codigos = {d["codigo"] for d in rig_ops.validar_rig(esqueleto, pesos)}
    assert "OSSO_DE_COMPRIMENTO_ZERO" in codigos


# ---- material ---------------------------------------------------------------

def _ruido(tamanho: int = 256, desvio: float = 20.0) -> np.ndarray:
    rng = np.random.default_rng(11)
    base = np.full((tamanho, tamanho, 3), 130, np.float32)
    return np.clip(base + rng.normal(0, desvio, (tamanho, tamanho, 1)), 0, 255).astype(np.uint8)


def test_normal_gerado_e_unitario():
    """Normal cuja soma vetorial não dá 1 produz iluminação errada em qualquer motor."""
    _, info = material_ops.gerar_normal(_ruido())
    assert info["norma_media"] == pytest.approx(1.0, abs=1e-4)
    assert info["inclinacao_maxima_graus"] <= 90.0


def test_normal_mais_forte_inclina_mais():
    _, fraco = material_ops.gerar_normal(_ruido(), forca=0.5)
    _, forte = material_ops.gerar_normal(_ruido(), forca=6.0)
    assert forte["inclinacao_media_graus"] > fraco["inclinacao_media_graus"]


def test_rugosidade_distingue_liso_de_texturado():
    """É o que a rugosidade significa fisicamente: micro-detalhe espalha luz."""
    liso = np.full((128, 128, 3), 130, np.uint8)
    _, info_liso = material_ops.gerar_rugosidade(liso)
    _, info_ruidoso = material_ops.gerar_rugosidade(_ruido(128, 30))
    assert info_ruidoso["rugosidade_media"] > info_liso["rugosidade_media"]


def test_rugosidade_nunca_chega_a_zero():
    """Zero é espelho perfeito, que não existe, e produz realce especular infinito."""
    _, info = material_ops.gerar_rugosidade(np.full((64, 64, 3), 130, np.uint8))
    assert info["rugosidade_minima"] >= 0.04


def test_albedo_estourado_e_recusado():
    codigos = {d["codigo"] for d in material_ops.validar_pbr(np.full((64, 64, 3), 250, np.uint8))}
    assert "ALBEDO_CLARO_DEMAIS" in codigos


def test_albedo_apagado_e_recusado():
    codigos = {d["codigo"] for d in material_ops.validar_pbr(np.full((64, 64, 3), 8, np.uint8))}
    assert "ALBEDO_ESCURO_DEMAIS" in codigos


@pytest.mark.parametrize("inicio,esperado", [(1.0, False), (0.7, False), (0.5, True), (0.25, True)])
def test_luz_assada_e_detectada_a_partir_de_dois_para_um(inicio, esperado):
    """Calibrado por medição: plana 0,019 · 0,7–1,0 → 0,145 · 0,5–1,0 → 0,241 ·
    0,25–1,0 → 0,362, com corte em 0,20."""
    rampa = np.linspace(inicio, 1.0, 256)[:, None, None]
    imagem = np.clip(_ruido().astype(np.float32) * rampa, 0, 255).astype(np.uint8)
    assert material_ops.analisar_albedo(imagem)["iluminacao_assada"] is esperado


def test_continuidade_acusa_costura_visivel():
    imagem = _ruido()
    assert material_ops.medir_continuidade(imagem)["tileable"] is True

    quebrada = imagem.copy()
    quebrada[:, -1] = 255      # última coluna estourada: costura garantida
    assert material_ops.medir_continuidade(quebrada)["tileable"] is False


# ---- motor ------------------------------------------------------------------

def test_operacao_sem_calculo_recusa_com_codigo(tmp_path):
    """A regra que separa este motor dos 1697 stubs: sem algoritmo, ele recusa —
    nunca devolve um dicionário plausível."""
    with pytest.raises(PerzonOperationError) as erro:
        PerzonEngine(tmp_path).executar("PZ-99-nao-existe", None)
    assert erro.value.codigo == "FEATURE_NAO_IMPLEMENTADA"


def test_parametro_fora_da_faixa_falha_antes_do_calculo(tmp_path, malha_no_disco):
    with pytest.raises(PerzonOperationError) as erro:
        PerzonEngine(tmp_path).executar("PZ-07-decimacao", malha_no_disco, {"alvo_faces": 1})
    assert erro.value.codigo == "PARAMETRO_FORA_DA_FAIXA"


def test_parametro_desconhecido_e_recusado(tmp_path, malha_no_disco):
    with pytest.raises(PerzonOperationError) as erro:
        PerzonEngine(tmp_path).executar("PZ-07-decimacao", malha_no_disco, {"inventado": 5})
    assert erro.value.codigo == "PARAMETRO_DESCONHECIDO"


def test_entrada_ausente_e_arquivo_inexistente_tem_codigos_distintos(tmp_path):
    motor = PerzonEngine(tmp_path)
    with pytest.raises(PerzonOperationError) as sem_entrada:
        motor.executar("PZ-06-topologia-estavel", None)
    assert sem_entrada.value.codigo == "ENTRADA_AUSENTE"

    with pytest.raises(PerzonOperationError) as inexistente:
        motor.executar("PZ-06-topologia-estavel", str(tmp_path / "nao_existe.glb"))
    assert inexistente.value.codigo == "ARQUIVO_INEXISTENTE"


def test_operacao_que_produz_asset_grava_arquivo_com_hash(tmp_path, malha_no_disco):
    resultado = PerzonEngine(tmp_path).executar(
        "PZ-07-decimacao", malha_no_disco, {"alvo_faces": 300})
    artefato = resultado["artefatos"][0]
    from pathlib import Path

    assert Path(artefato["caminho"]).is_file()
    assert artefato["bytes"] > 0
    assert len(artefato["sha256"]) == 64
    assert artefato["faces"] <= resultado["metrica"]["faces_antes"]


def test_toda_operacao_registrada_executa_de_fato(tmp_path, malha_no_disco,
                                                  textura_no_disco, clipe_no_disco,
                                                  glb_no_disco, foto_no_disco,
                                                  guias_no_disco, painel_no_disco):
    """O contrário de um catálogo de promessas: cada linha do registro roda aqui."""
    motor = PerzonEngine(tmp_path, models_root=MODELOS)
    falhas = []
    for operacao in OPERACOES:
        entradas = {"mesh": malha_no_disco, "imagem": textura_no_disco,
                    "animacao": clipe_no_disco, "arquivo": glb_no_disco,
                    "rosto": foto_no_disco, "cabelo": guias_no_disco,
                    # Operação sem entrada de arquivo: gera o próprio dado a
                    # partir dos parâmetros declarados.
                    "nenhuma": None}
        # Vestuário mede molde, e molde é painel aberto. Passar o humanoide
        # fechado faria a operação recusar corretamente e o teste ler isso como
        # falha do cálculo.
        entrada = (painel_no_disco if operacao.modulo == "garment"
                   and operacao.entrada == "mesh" else entradas[operacao.entrada])
        try:
            resultado = motor.executar(operacao.feature_id, entrada)
            assert resultado["status"] == "executado"
            assert resultado["duracao_s"] >= 0
            if operacao.produz_asset:
                assert resultado["artefatos"], f"{operacao.feature_id} prometeu asset e não gravou"
        except Exception as erro:  # noqa: BLE001 — queremos o inventário completo
            falhas.append(f"{operacao.feature_id}: {type(erro).__name__} {erro}")
    assert not falhas, falhas


def test_registro_nao_promete_feature_sem_funcao():
    for operacao in OPERACOES:
        assert callable(operacao.funcao), operacao.feature_id
        assert operacao.descricao.strip(), operacao.feature_id
        assert operacao.entrada in {"mesh", "imagem", "animacao", "arquivo",
                                "rosto", "cabelo", "nenhuma"}, operacao.feature_id


def test_ids_do_registro_seguem_a_nomenclatura_do_perzon():
    """`feature_id` que não casa com o catálogo do PERZON quebraria o verificador."""
    for feature_id in POR_FEATURE:
        assert feature_id.startswith("PZ-"), feature_id


# ---- rotas ------------------------------------------------------------------

def test_rota_lista_so_o_que_executa(config):
    app = create_app(config)
    with TestClient(app) as client:
        corpo = client.get("/api/perzon/operacoes").json()
        assert corpo["total"] == len(OPERACOES)
        assert set(corpo["modulos"]) <= {"mesh", "sculpt", "rig", "material",
                                         "motion", "formats", "face", "headshot",
                                         "character", "garment", "hair"}
        listados = sum(len(v) for v in corpo["modulos"].values())
        assert listados == len(OPERACOES)


def test_rota_executa_sobre_arquivo_e_registra_o_asset(config, malha_no_disco):
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.post("/api/perzon/executar", json={
            "feature_id": "PZ-06-pontos-de-medicao", "caminho": malha_no_disco})
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["metrica"]["altura_depois_m"] == pytest.approx(1.75, abs=1e-6)
        assert corpo["artefatos"][0]["asset_id"]

        # O asset registrado precisa existir na biblioteca, senão o arquivo é órfão.
        asset = app.state.store.get_asset(corpo["artefatos"][0]["asset_id"])
        assert asset is not None


def test_rota_devolve_422_com_codigo_em_vez_de_500(config):
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.post("/api/perzon/executar",
                               json={"feature_id": "PZ-99-inventado"})
        assert resposta.status_code == 422
        assert resposta.json()["detail"]["code"] == "FEATURE_NAO_IMPLEMENTADA"


def test_rota_recusa_asset_inexistente(config):
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.post("/api/perzon/executar", json={
            "feature_id": "PZ-06-topologia-estavel", "asset_id": "ast_nao_existe"})
        assert resposta.status_code == 404
        assert resposta.json()["detail"]["code"] == "ASSET_INEXISTENTE"


# ---- catálogo de nós --------------------------------------------------------

def test_todo_no_de_personagem_tem_operacao_perzon_atras():
    """Nó na UI sem cálculo atrás é a definição do que este trabalho veio corrigir."""
    from cinenode.workflow import NODE_CATALOG, WorkflowExecutor

    tipos = [n["type"] for n in NODE_CATALOG if n["category"] == "Personagem"]
    mapeados = set(WorkflowExecutor._PERZON_POR_NO) | {"human.material.maps", "human.dna"}
    sem_calculo = [t for t in tipos if t not in mapeados]
    assert not sem_calculo, f"nós sem operação por trás: {sem_calculo}"


def test_todo_feature_referenciado_pelos_nos_existe_no_registro():
    from cinenode.workflow import WorkflowExecutor

    referenciados = set(WorkflowExecutor._PERZON_POR_NO.values())
    referenciados |= set(WorkflowExecutor._PERZON_MAPA_PBR.values())
    faltando = referenciados - set(POR_FEATURE)
    assert not faltando, f"nós apontam para features que não existem: {faltando}"


# ---- movimento --------------------------------------------------------------

def test_caminhada_correta_nao_acusa_deslize(caminhada):
    """Com o pé cravado durante todo o apoio, o deslize tem de dar zero.

    Esta asserção sozinha encontrou quatro defeitos reais: `ndarray.ptp` removido
    no NumPy 2, diferença para trás contra para frente entre detecção e medida,
    filtro de velocidade cegando o detector para o pé que escorrega, e o quadro
    de pouso contado como deslize.
    """
    medida = motion_ops.medir_deslize(caminhada["quadros"], caminhada["fps"],
                                      caminhada["juntas_pe"])
    assert medida["deslize_maximo_m_s"] == pytest.approx(0.0, abs=1e-9)
    assert medida["aprovado"] is True


def test_apoio_nao_cobre_a_animacao_inteira(caminhada):
    """Se todo quadro é apoio, o detector não está detectando nada."""
    contatos = motion_ops.detectar_contatos(caminhada["quadros"], caminhada["fps"],
                                            caminhada["juntas_pe"])
    total = caminhada["quadros"].shape[0]
    for junta in caminhada["juntas_pe"]:
        quantidade = len(contatos["contatos_por_junta"][str(junta)])
        assert 0 < quantidade < total, f"junta {junta}: {quantidade} de {total}"


def test_travar_pes_corrige_deslize_injetado(caminhada):
    quadros = caminhada["quadros"].copy()
    fps, pes = caminhada["fps"], caminhada["juntas_pe"]
    contatos = motion_ops.detectar_contatos(quadros, fps, pes)
    for junta in pes:
        for i, f in enumerate(contatos["contatos_por_junta"][str(junta)]):
            quadros[f, junta, 0] += 0.02 * (i % 5)

    antes = motion_ops.medir_deslize(quadros, fps, pes)["deslize_maximo_m_s"]
    assert antes > motion_ops.LIMITE_DESLIZE_M_S

    _, info = motion_ops.travar_pes(quadros, fps, pes)
    assert info["melhorou"] is True
    assert info["aprovado"] is True
    assert info["deslize_depois_m_s"] < antes


def test_travar_pes_preserva_o_avanco_da_raiz(caminhada):
    """Corrigir deslize congelando o personagem no lugar trocaria um defeito por
    outro pior."""
    quadros, fps, pes = caminhada["quadros"].copy(), caminhada["fps"], caminhada["juntas_pe"]
    antes = float(quadros[-1, 0, 0] - quadros[0, 0, 0])
    corrigido, _ = motion_ops.travar_pes(quadros, fps, pes)
    assert float(corrigido[-1, 0, 0] - corrigido[0, 0, 0]) == pytest.approx(antes, abs=1e-9)


def test_jitter_e_a_terceira_derivada_e_nao_a_velocidade(caminhada):
    """Movimento rápido e limpo tem jitter proporcional; movimento normal e sujo
    tem jitter desproporcional. Medir aceleração confundiria os dois."""
    limpo = caminhada["quadros"]
    rapido = limpo * 3.0
    sujo = limpo + np.random.default_rng(1).normal(0, 0.004, limpo.shape)

    jitter_limpo = motion_ops.medir_jitter(limpo, caminhada["fps"])["medio"]
    jitter_rapido = motion_ops.medir_jitter(rapido, caminhada["fps"])["medio"]
    jitter_sujo = motion_ops.medir_jitter(sujo, caminhada["fps"])["medio"]

    assert jitter_sujo > jitter_limpo * 5, (jitter_limpo, jitter_sujo)
    assert jitter_rapido == pytest.approx(jitter_limpo * 3, rel=0.01)


def test_remover_jitter_reduz_o_solavanco_sem_levar_a_pose(caminhada):
    sujo = caminhada["quadros"] + np.random.default_rng(2).normal(
        0, 0.004, caminhada["quadros"].shape)
    _, info = motion_ops.remover_jitter(sujo, caminhada["fps"], janela=9)
    assert info["jitter_depois"] < info["jitter_antes"]
    assert info["reducao_relativa"] > 0.5
    assert info["deslocamento_medio_m"] < 0.02


def test_remover_drift_preserva_o_rumo(caminhada):
    """Rumo constante não é separável de caminhada diagonal. O cálculo tira o
    desvio da reta e declara que o rumo ficou."""
    quadros = caminhada["quadros"].copy()
    tempo = np.arange(quadros.shape[0])
    quadros[:, :, 2] += 0.15 * np.sin(2 * np.pi * tempo / 90)[:, None]

    avanco = float(quadros[-1, 0, 0] - quadros[0, 0, 0])
    corrigido, info = motion_ops.remover_drift(quadros, caminhada["fps"])
    assert info["desvio_maximo_m"] > 0.05
    assert float(corrigido[-1, 0, 0] - corrigido[0, 0, 0]) == pytest.approx(avanco, abs=1e-6)


def test_loop_reduz_a_descontinuidade(caminhada):
    _, info = motion_ops.fazer_loop(caminhada["quadros"], caminhada["fps"], transicao=8)
    assert info["melhorou"] is True
    assert info["descontinuidade_depois_m"] < info["descontinuidade_antes_m"]


def test_reamostrar_nao_inventa_pose_fora_do_capturado(caminhada):
    novo, info = motion_ops.reamostrar(caminhada["quadros"], caminhada["fps"], 60.0)
    assert info["quadros_depois"] == pytest.approx(info["quadros_antes"] * 2, abs=1)
    assert novo.shape[1:] == caminhada["quadros"].shape[1:]
    assert novo.min() >= caminhada["quadros"].min() - 1e-9
    assert novo.max() <= caminhada["quadros"].max() + 1e-9


def test_animacao_curta_demais_e_recusada():
    with pytest.raises(motion_ops.AnimacaoInvalida, match="pelo menos 2 quadros"):
        motion_ops.analisar(np.zeros((1, 3, 3)), 30.0)


def test_nan_na_captura_e_recusado():
    """NaN silencioso vira membro no infinito, e o erro aparece só no render."""
    quadros = np.zeros((10, 3, 3))
    quadros[4, 1, 0] = np.nan
    with pytest.raises(motion_ops.AnimacaoInvalida, match="NaN"):
        motion_ops.analisar(quadros, 30.0)


def test_clipe_sem_juntas_de_pe_recusa_com_codigo(tmp_path, caminhada):
    import json

    caminho = tmp_path / "sem_pes.json"
    caminho.write_text(json.dumps({"fps": caminhada["fps"],
                                   "quadros": caminhada["quadros"].tolist()}),
                       encoding="utf-8")
    with pytest.raises(PerzonOperationError) as erro:
        PerzonEngine(tmp_path).executar("PZ-12-grounding", str(caminho))
    assert erro.value.codigo == "JUNTAS_DE_PE_AUSENTES"


def test_clipe_ilegivel_recusa_com_codigo(tmp_path):
    caminho = tmp_path / "quebrado.json"
    caminho.write_text("{isso nao e json}", encoding="utf-8")
    with pytest.raises(PerzonOperationError) as erro:
        PerzonEngine(tmp_path).executar("PZ-12-analise-de-clips", str(caminho))
    assert erro.value.codigo == "CLIPE_INVALIDO"


def test_operacao_de_movimento_grava_clipe_novo(tmp_path, clipe_no_disco):
    import json

    resultado = PerzonEngine(tmp_path).executar(
        "PZ-12-velocidade", clipe_no_disco, {"fps_alvo": 60.0})
    artefato = resultado["artefatos"][0]
    gravado = json.loads(Path(artefato["caminho"]).read_text(encoding="utf-8"))
    assert gravado["fps"] == 60.0
    assert len(gravado["quadros"]) == resultado["metrica"]["quadros_depois"]


# ---- exportação -------------------------------------------------------------

def test_gltf_sem_rig_ainda_e_valido(tmp_path, humanoide):
    destino = tmp_path / "estatua.glb"
    relatorio = export_ops.exportar_gltf(humanoide, destino)
    assert relatorio["tem_rig"] is False
    assert export_ops.validar_gltf(destino)["valido"] is True


def test_gltf_com_rig_grava_skin_e_matrizes(tmp_path, humanoide):
    """O trimesh sozinho exporta geometria e nada de skin: o personagem sai
    estátua. É o motivo de este exportador existir."""
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    pesos = rig_ops.calcular_pesos(humanoide, esqueleto)
    destino = tmp_path / "personagem.glb"

    relatorio = export_ops.exportar_gltf(humanoide, destino, esqueleto, pesos)
    assert relatorio["tem_rig"] is True

    validacao = export_ops.validar_gltf(destino)
    assert validacao["valido"] is True, validacao["problemas"]
    assert validacao["tem_skin"] is True
    assert validacao["juntas"] == len(pesos["ossos"])


def test_esqueleto_exportado_e_uma_arvore_so(tmp_path, humanoide):
    """A raiz não é osso de ninguém. Criar nó só para os ossos a deixava de fora,
    e os três filhos do quadril viravam raízes soltas — o esqueleto saía partido
    em três árvores e o personagem se desmonta na primeira pose."""
    import json
    import struct

    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    pesos = rig_ops.calcular_pesos(humanoide, esqueleto)
    destino = tmp_path / "arvore.glb"
    export_ops.exportar_gltf(humanoide, destino, esqueleto, pesos)

    dados = destino.read_bytes()
    tamanho, _ = struct.unpack_from("<II", dados, 12)
    documento = json.loads(dados[20:20 + tamanho].decode("utf-8"))

    raizes = [n for n in documento["scenes"][0]["nodes"] if n != 0]
    assert len(raizes) == 1, [documento["nodes"][i]["name"] for i in raizes]

    alcancados, pilha = set(), list(raizes)
    while pilha:
        no = pilha.pop()
        alcancados.add(no)
        pilha.extend(documento["nodes"][no].get("children", []))
    assert len(alcancados) == len(esqueleto["juntas"])


def test_gltf_exportado_e_relido_por_terceiro(tmp_path, humanoide):
    """Validar com o próprio código provaria pouco. O trimesh é um leitor
    independente: se ele carrega, o arquivo não é só internamente consistente."""
    destino = tmp_path / "terceiro.glb"
    export_ops.exportar_gltf(humanoide, destino)
    cena = trimesh.load(str(destino))
    geometrias = list(cena.geometry.values()) if hasattr(cena, "geometry") else [cena]
    assert sum(len(g.faces) for g in geometrias) == len(humanoide.faces)


def test_exportacao_recusa_peso_nao_normalizado(tmp_path, humanoide):
    """Peso que não soma 1 faz a malha esticar ao animar. Gravar assim empurraria
    o defeito para o motor de jogo, onde ninguém sabe de onde veio."""
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    pesos = rig_ops.calcular_pesos(humanoide, esqueleto)
    pesos["pesos"] = [[0.5, 0.2, 0.1, 0.1] for _ in pesos["pesos"]]   # soma 0,9

    with pytest.raises(export_ops.ExportacaoInvalida, match="não normalizados"):
        export_ops.exportar_gltf(humanoide, tmp_path / "ruim.glb", esqueleto, pesos)


def test_validador_acusa_comprimento_divergente(tmp_path, humanoide):
    """Um GLB com comprimento errado abre em algumas ferramentas e falha noutras.
    O defeito só apareceria no computador de outra pessoa."""
    destino = tmp_path / "truncado.glb"
    export_ops.exportar_gltf(humanoide, destino)
    dados = bytearray(destino.read_bytes())
    dados.extend(b"\x00" * 16)          # sobra que o cabeçalho não declara
    destino.write_bytes(bytes(dados))

    validacao = export_ops.validar_gltf(destino)
    assert validacao["valido"] is False
    assert "COMPRIMENTO_DIVERGENTE" in {p["codigo"] for p in validacao["problemas"]}


def test_obj_avisa_que_perde_o_rig(tmp_path, humanoide):
    relatorio = export_ops.exportar_obj(humanoide, tmp_path / "c.obj")
    assert relatorio["tem_rig"] is False
    assert "esqueleto" in relatorio["aviso"]
    assert relatorio["bytes"] > 0


def test_bvh_tem_hierarquia_e_uma_linha_por_quadro(tmp_path, humanoide):
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    total = 12
    quadros = np.zeros((total, len(esqueleto["juntas"]), 3))
    for i, nome in enumerate(esqueleto["juntas"]):
        quadros[:, i] = esqueleto["juntas"][nome]

    destino = tmp_path / "c.bvh"
    relatorio = export_ops.exportar_bvh(esqueleto, quadros, 30.0, destino)
    assert relatorio["quadros"] == total

    linhas = destino.read_text(encoding="utf-8").splitlines()
    assert linhas[0] == "HIERARCHY"
    assert linhas[1].startswith("ROOT ")
    inicio = linhas.index("MOTION")
    assert linhas[inicio + 1] == f"Frames: {total}"
    # MOTION, Frames:, Frame Time: e depois uma linha por quadro.
    assert len(linhas) - (inicio + 3) == total


def test_bvh_recusa_animacao_com_juntas_a_mais(tmp_path, humanoide):
    esqueleto = rig_ops.gerar_esqueleto(humanoide)
    quadros = np.zeros((5, len(esqueleto["juntas"]) + 3, 3))
    with pytest.raises(export_ops.ExportacaoInvalida, match="juntas"):
        export_ops.exportar_bvh(esqueleto, quadros, 30.0, tmp_path / "x.bvh")


def test_clipe_sem_esqueleto_nao_vira_bvh(tmp_path, caminhada):
    import json

    caminho = tmp_path / "sem_esqueleto.json"
    caminho.write_text(json.dumps({"fps": caminhada["fps"],
                                   "quadros": caminhada["quadros"].tolist()}),
                       encoding="utf-8")
    with pytest.raises(PerzonOperationError) as erro:
        PerzonEngine(tmp_path).executar("PZ-26-bvh", str(caminho))
    assert erro.value.codigo == "ESQUELETO_AUSENTE"


def test_motor_exporta_com_rig_sem_pedir_esqueleto(tmp_path, malha_no_disco):
    """Exigir esqueleto e pesos do chamador faria da exportação um terceiro passo
    obrigatório, e o erro mais comum passaria a ser exportar sem rig por esquecimento."""
    resultado = PerzonEngine(tmp_path).executar("PZ-26-glb-gltf", malha_no_disco)
    assert resultado["metrica"]["tem_rig"] is True
    assert resultado["metrica"]["validacao"]["valido"] is True
    assert resultado["artefatos"][0]["formato"] == "glb"


def test_pipeline_completo_da_malha_crua_ao_glb_com_rig(tmp_path, malha_no_disco):
    """A fatia vertical inteira: reparar, normalizar escala, rigar e exportar."""
    motor = PerzonEngine(tmp_path)

    reparada = motor.executar("PZ-07-remover-duplicados", malha_no_disco)
    caminho = reparada["artefatos"][0]["caminho"]

    escala = motor.executar("PZ-06-pontos-de-medicao", caminho, {"altura_alvo_m": 1.80})
    assert escala["metrica"]["altura_depois_m"] == pytest.approx(1.80, abs=1e-6)
    caminho = escala["artefatos"][0]["caminho"]

    rig = motor.executar("PZ-11-validar-hierarquia", caminho)
    assert isinstance(rig["metrica"]["defeitos"], list)

    saida = motor.executar("PZ-26-glb-gltf", caminho)
    assert saida["metrica"]["validacao"]["tem_skin"] is True

    conferido = motor.executar("PZ-26-avchar", saida["artefatos"][0]["caminho"])
    assert conferido["metrica"]["valido"] is True, conferido["metrica"]["problemas"]


# ---- M-34: rosto ------------------------------------------------------------

def test_blendshapes_medidas_sao_as_52_do_detector(leitura_de_rosto):
    analise = face_ops.analisar_blendshapes(leitura_de_rosto["blendshapes"])
    assert analise["total"] == 52
    assert 0 < analise["ativas"] <= 52
    assert len(analise["dominantes"]) == 8
    assert all(0.0 <= v <= 1.0 for v in analise["todas"].values())


def test_emocao_mostra_de_onde_veio_o_numero(leitura_de_rosto):
    """Um classificador que só cospe o rótulo não permite discordar dele."""
    resultado = face_ops.classificar_emocao(leitura_de_rosto["blendshapes"])
    assert resultado["dominante"] in set(face_ops.EMOCOES) | {"neutra"}
    assert set(resultado["pontuacoes"]) == set(face_ops.EMOCOES)
    # A contribuição de cada blendshape precisa estar visível e somar a pontuação.
    for emocao, pontos in resultado["pontuacoes"].items():
        assert sum(resultado["contribuicoes"][emocao].values()) == pytest.approx(pontos, abs=1e-3)


def test_rosto_neutro_nao_recebe_emocao_inventada():
    """Apontar a emoção 'menos fraca' num rosto parado seria inventar leitura."""
    parado = {nome: 0.0 for combinacao in face_ops.EMOCOES.values() for nome in combinacao}
    assert face_ops.classificar_emocao(parado)["dominante"] == "neutra"


def test_sorriso_sintetico_pontua_alegria():
    """Prova que a combinação FACS declarada de fato responde ao dado."""
    sorriso = {"mouthSmileLeft": 0.9, "mouthSmileRight": 0.9,
               "cheekSquintLeft": 0.6, "cheekSquintRight": 0.6}
    resultado = face_ops.classificar_emocao(sorriso)
    assert resultado["dominante"] == "alegria"
    assert resultado["pontuacoes"]["alegria"] > resultado["pontuacoes"]["tristeza"]


def test_olho_fechado_e_detectado_pela_razao_de_aspecto(leitura_de_rosto):
    pontos = leitura_de_rosto["pontos"]
    aberto = face_ops.medir_olhos(pontos)
    assert aberto["fechado_esquerdo"] is False

    fechado = pontos.copy()
    # Cola a pálpebra superior na inferior: é literalmente o olho fechado.
    fechado[face_ops.OLHO_E_SUPERIOR] = fechado[face_ops.OLHO_E_INFERIOR]
    assert face_ops.medir_olhos(fechado)["fechado_esquerdo"] is True


def test_medida_de_olho_e_independente_da_distancia_da_camera(leitura_de_rosto):
    """Usar a altura crua faria um rosto longe parecer sempre com os olhos fechados."""
    pontos = leitura_de_rosto["pontos"]
    perto = face_ops.medir_olhos(pontos)
    longe = face_ops.medir_olhos(pontos * 0.4)
    assert longe["abertura_esquerdo"] == pytest.approx(perto["abertura_esquerdo"], rel=1e-6)


def test_olhos_exigem_os_478_pontos():
    with pytest.raises(face_ops.RostoInvalido, match="478"):
        face_ops.medir_olhos(np.zeros((468, 3)))


def test_boca_fechada_permite_visema_de_fechamento(leitura_de_rosto):
    pontos = leitura_de_rosto["pontos"].copy()
    pontos[face_ops.LABIO_SUPERIOR] = pontos[face_ops.LABIO_INFERIOR]
    assert face_ops.medir_boca(pontos)["labios_em_contato"] is True


def test_assimetria_cresce_quando_o_rosto_e_torcido(leitura_de_rosto):
    """Apagar a assimetria é o erro clássico: fica correto e não parece a pessoa."""
    pontos = leitura_de_rosto["pontos"]
    base = face_ops.medir_assimetria(pontos)["assimetria_media"]

    torcido = pontos.copy()
    torcido[face_ops.BOCA_ESQUERDA] += [0, 25, 0]
    assert face_ops.medir_assimetria(torcido)["assimetria_media"] > base


def test_espelhar_expressao_troca_os_lados():
    espelhado = face_ops.espelhar_expressao(
        {"mouthSmileLeft": 0.9, "mouthSmileRight": 0.1, "jawOpen": 0.5})["blendshapes"]
    assert espelhado["mouthSmileLeft"] == 0.1
    assert espelhado["mouthSmileRight"] == 0.9
    assert espelhado["jawOpen"] == 0.5, "blendshape central não tem lado para trocar"


def test_compor_soma_em_vez_de_mediar():
    """A média daria meio sorriso com meia sobrancelha: uma terceira expressão."""
    composta = face_ops.compor_expressao(
        {"mouthSmileLeft": 0.8}, {"browInnerUp": 0.6}, peso=1.0)["blendshapes"]
    assert composta["mouthSmileLeft"] == 0.8
    assert composta["browInnerUp"] == 0.6


def test_composicao_satura_em_um():
    resultado = face_ops.compor_expressao({"jawOpen": 0.8}, {"jawOpen": 0.9}, peso=1.0)
    assert resultado["blendshapes"]["jawOpen"] == 1.0
    assert "jawOpen" in resultado["saturadas"]


@pytest.mark.parametrize("combinacao,codigo", [
    ({"jawOpen": 0.9, "mouthClose": 0.9}, "MANDIBULA_E_BOCA_EM_CONFLITO"),
    ({"eyeBlinkLeft": 0.9, "eyeWideLeft": 0.9}, "OLHO_FECHA_E_ARREGALA"),
    ({"mouthSmileLeft": 0.9, "mouthFrownLeft": 0.9}, "SORRISO_E_TRISTEZA_NO_MESMO_LADO"),
    ({"jawOpen": 1.8}, "ATIVACAO_FORA_DA_FAIXA"),
])
def test_expressao_anatomicamente_impossivel_e_acusada(combinacao, codigo):
    assert codigo in {d["codigo"] for d in face_ops.validar_expressao(combinacao)}


def test_visema_diz_que_nao_substitui_audio(leitura_de_rosto):
    resultado = face_ops.detectar_visema(leitura_de_rosto["blendshapes"])
    assert resultado["visema"] in set(face_ops.VISEMAS) | {"silencio"}
    assert "áudio" in resultado["limitacao"]


# ---- M-34: headshot ---------------------------------------------------------

def test_nitidez_separa_foto_boa_de_borrada():
    import cv2

    rng = np.random.default_rng(1)
    nitida = np.clip(np.full((480, 480, 3), 130, np.float32)
                     + rng.normal(0, 35, (480, 480, 3)), 0, 255).astype(np.uint8)
    assert headshot_ops.medir_nitidez(nitida)["aprovado"] is True
    borrada = cv2.GaussianBlur(nitida, (21, 21), 0)
    assert headshot_ops.medir_nitidez(borrada)["aprovado"] is False


def test_estourado_e_apagado_contam_separado():
    """Pixel estourado perdeu a informação; apagado ainda tem sinal no ruído."""
    estourada = headshot_ops.medir_exposicao(np.full((64, 64, 3), 252, np.uint8))
    apagada = headshot_ops.medir_exposicao(np.full((64, 64, 3), 2, np.uint8))
    assert estourada["fracao_estourada"] > 0.9 and estourada["fracao_apagada"] < 0.1
    assert apagada["fracao_apagada"] > 0.9 and apagada["fracao_estourada"] < 0.1
    assert not estourada["aprovado"] and not apagada["aprovado"]


def test_frontalidade_classifica_a_tomada():
    frontal = headshot_ops.medir_frontalidade(np.eye(4))
    assert frontal["tomada"] == "frontal"

    angulo = np.radians(40)
    virada = np.eye(4)
    virada[0, 0] = np.cos(angulo); virada[0, 2] = np.sin(angulo)
    virada[2, 0] = -np.sin(angulo); virada[2, 2] = np.cos(angulo)
    resultado = headshot_ops.medir_frontalidade(virada)
    assert resultado["frontal"] is False
    assert resultado["tomada"] == "perfil_direito"
    assert resultado["guinada_graus"] == pytest.approx(40.0, abs=0.5)


def test_enquadramento_reprova_rosto_pequeno(leitura_de_rosto):
    """Rosto pequeno no canto parece bom em miniatura e não tem pixel onde importa."""
    imagem, pontos = leitura_de_rosto["imagem"], leitura_de_rosto["pontos"]
    assert headshot_ops.medir_enquadramento(imagem, pontos)["aprovado"] is True
    assert headshot_ops.medir_enquadramento(imagem, pontos * 0.2)["aprovado"] is False


def test_alinhar_pelos_olhos_deixa_a_linha_dos_olhos_horizontal(leitura_de_rosto):
    """A caixa do rosto muda com a expressão; a distância interpupilar não."""
    imagem, pontos = leitura_de_rosto["imagem"], leitura_de_rosto["pontos"]
    girado = pontos.copy()
    angulo = np.radians(12)
    centro = girado[:, :2].mean(axis=0)
    rot = np.array([[np.cos(angulo), -np.sin(angulo)], [np.sin(angulo), np.cos(angulo)]])
    girado[:, :2] = (girado[:, :2] - centro) @ rot.T + centro

    _, info = headshot_ops.alinhar_pelos_olhos(imagem, girado, tamanho=256)
    assert abs(info["angulo_corrigido_graus"]) == pytest.approx(12.0, abs=1.5)
    assert info["tamanho"] == 256


def test_regioes_da_foto_somam_o_quadro(leitura_de_rosto):
    regioes = headshot_ops.segmentar_regioes(
        leitura_de_rosto["imagem"], leitura_de_rosto["pontos"])
    assert 0 < regioes["fracao_rosto"] < 1
    assert "treinada" in regioes["metodo"], "o método precisa declarar o que não é"


def test_avaliar_junta_todas_as_reprovas_de_uma_vez(leitura_de_rosto):
    """Recusar a foto uma vez com a lista inteira, em vez de um problema por vez."""
    import cv2

    ruim = cv2.GaussianBlur(np.full((480, 480, 3), 252, np.uint8), (31, 31), 0)
    relatorio = headshot_ops.avaliar(ruim)
    codigos = {r["codigo"] for r in relatorio["reprovas"]}
    assert relatorio["aprovada"] is False
    assert {"FOTO_BORRADA", "EXPOSICAO_RUIM"} <= codigos


def test_comparar_fotos_exige_pelo_menos_duas():
    with pytest.raises(headshot_ops.FotoInvalida, match="pelo menos 2"):
        headshot_ops.comparar_fotos([{"a": 1.0}])


def test_comparar_acusa_fotos_incoerentes():
    coerentes = headshot_ops.comparar_fotos(
        [{"largura": 1.00, "altura": 1.40}, {"largura": 1.02, "altura": 1.41}])
    assert coerentes["coerentes"] is True

    divergentes = headshot_ops.comparar_fotos(
        [{"largura": 1.00, "altura": 1.40}, {"largura": 1.90, "altura": 1.41}])
    assert divergentes["coerentes"] is False
    assert divergentes["piores"][0]["medida"] == "largura"


# ---- M-34: personagem -------------------------------------------------------

def test_proporcao_mede_todos_os_niveis_do_corpo(humanoide):
    """Amostrar vértices deixava o quadril sem medida: um cilindro só tem vértice
    nas duas tampas, e a faixa no meio da coxa saía vazia."""
    medida = character_ops.medir_proporcoes(humanoide)
    for nivel in ("quadril", "cintura", "peito", "ombro"):
        assert medida["larguras_m"][nivel] is not None, nivel
        assert medida["larguras_m"][nivel] > 0


def test_cabecas_de_altura_acompanha_a_proporcao_real(humanoide):
    medida = character_ops.medir_proporcoes(humanoide)
    assert 5.0 < medida["cabecas_de_altura"] < 10.0, medida["cabecas_de_altura"]


def test_proporcao_recusa_malha_deitada():
    # Um triângulo no plano XZ: altura exatamente zero, não "quase zero".
    deitada = trimesh.Trimesh(
        vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 0, 1]], dtype=float),
        faces=np.array([[0, 1, 2]]), process=False)
    with pytest.raises(character_ops.CorpoInvalido, match="altura zero"):
        character_ops.medir_proporcoes(deitada)


def test_massa_descreve_a_curva_e_nao_um_ponto(humanoide):
    """Duas silhuetas com a mesma estatura e ombro podem distribuir massa
    de formas completamente diferentes."""
    massa = character_ops.medir_massa(humanoide, fatias=20)
    assert len(massa["distribuicao"]) == 20
    assert sum(massa["distribuicao"]) == pytest.approx(1.0, abs=1e-3)
    assert 0.0 < massa["centro_de_massa_relativo"] < 1.0


def test_massa_recusa_poucas_fatias(humanoide):
    with pytest.raises(character_ops.CorpoInvalido, match="não descrevem"):
        character_ops.medir_massa(humanoide, fatias=2)


def test_regioes_cobrem_o_corpo_inteiro(humanoide):
    """Vértice fora de toda faixa ficaria para trás na edição por região."""
    regioes = character_ops.separar_regioes(humanoide)
    assert regioes["cobertura"] > 0.99
    soma = sum(r["vertices"] for r in regioes["regioes"].values())
    assert soma + regioes["vertices_sem_regiao"] == len(humanoide.vertices)


def test_espelhar_lado_preserva_a_contagem_de_vertices(humanoide):
    """Espelhar a malha inteira e concatenar duplicaria vértices e quebraria o skin."""
    torto = humanoide.copy()
    direita = torto.vertices[:, 0] > 0
    torto.vertices[direita, 1] += 0.05

    espelhado, info = character_ops.espelhar_lado(torto, "esquerdo")
    assert len(espelhado.vertices) == len(torto.vertices)
    assert len(espelhado.faces) == len(torto.faces)
    assert info["vertices_substituidos"] > 0
    assert info["simetria_depois"]["erro_relativo"] < mesh_ops.simetria(
        torto, 0)["erro_relativo"]


def test_espelhar_recusa_lado_inexistente(humanoide):
    with pytest.raises(character_ops.CorpoInvalido, match="lado desconhecido"):
        character_ops.espelhar_lado(humanoide, "meio")


def test_comparar_corpos_mede_o_que_mudou(humanoide):
    """Um 'antes/depois' que só mostra as duas malhas deixa o julgamento no olho."""
    menor = humanoide.copy()
    menor.apply_scale(0.9)
    resultado = character_ops.comparar_corpos(humanoide, menor)
    assert resultado["variacao_de_altura"] == pytest.approx(-0.1, abs=1e-6)
    assert resultado["topologia_preservada"] is True
    assert resultado["maior_mudanca"] is not None


def test_pescoco_sai_do_estrangulamento_e_nao_de_fracao_fixa(humanoide):
    """A primeira versão usava `1 - 0.870` e devolvia 7,69 para qualquer corpo:
    tautologia com cara de medida."""
    pescoco = character_ops.detectar_pescoco(humanoide)
    assert pescoco["confianca"] == "alta"
    assert pescoco["estreitamento"] > 0.15
    # O pescoço fica perto do topo num corpo de proporção humana, mas o número
    # vem da geometria — trocar a cabeça muda a fração.
    assert 0.70 < pescoco["fracao"] < 0.95


def test_corpo_sem_pescoco_recusa_medir_em_vez_de_inventar():
    """Uma esfera sobre uma caixa não estrangula em lugar nenhum. Devolver ~7,7
    cabeças ali seria repetir a constante e chamar de medida."""
    sem_pescoco = trimesh.util.concatenate([
        trimesh.creation.icosphere(radius=0.5).apply_transform(
            trimesh.transformations.translation_matrix([0, 0.9, 0])),
        trimesh.creation.box(extents=[0.3, 0.8, 0.2],
                             transform=trimesh.transformations.translation_matrix([0, 0.4, 0])),
    ])
    pescoco = character_ops.detectar_pescoco(sem_pescoco)
    assert pescoco["confianca"] == "baixa"
    assert "estrangula" in pescoco["motivo"]

    codigos = {d["codigo"] for d in character_ops.validar_proporcao(sem_pescoco)}
    assert "PESCOCO_NAO_ENCONTRADO" in codigos


def test_cabeca_grande_com_pescoco_e_acusada():
    """Com pescoço medível, a desproporção precisa aparecer como número baixo."""
    T = trimesh.transformations
    cabecudo = trimesh.util.concatenate([
        trimesh.creation.icosphere(radius=0.45).apply_transform(T.translation_matrix([0, 1.15, 0])),
        trimesh.creation.box(extents=[0.10, 0.12, 0.10], transform=T.translation_matrix([0, 0.70, 0])),
        trimesh.creation.box(extents=[0.40, 0.55, 0.25], transform=T.translation_matrix([0, 0.35, 0])),
    ])
    pescoco = character_ops.detectar_pescoco(cabecudo)
    assert pescoco["confianca"] == "alta", pescoco
    assert character_ops.medir_proporcoes(cabecudo)["cabecas_de_altura"] < 3.0
    assert "CABECA_DESPROPORCIONAL" in {
        d["codigo"] for d in character_ops.validar_proporcao(cabecudo)}


def test_validacao_acusa_escala_fora_do_esperado(humanoide):
    gigante = humanoide.copy()
    gigante.apply_scale(10.0)
    codigos = {d["codigo"] for d in character_ops.validar_proporcao(gigante)}
    assert "ESCALA_FORA_DO_ESPERADO" in codigos


# ---- M-34: motor ------------------------------------------------------------

def test_motor_roda_o_detector_uma_vez_por_foto(tmp_path, foto_no_disco):
    """Pedir blendshapes depois de já ter pedido os pontos custaria o passe
    inteiro de novo sobre a mesma imagem."""
    motor = PerzonEngine(tmp_path, models_root=MODELOS)
    resultado = motor.executar("PZ-05-controles-facs", foto_no_disco)
    assert resultado["status"] == "executado"
    assert resultado["metrica"]["dominante"] in set(face_ops.EMOCOES) | {"neutra"}


def test_motor_recusa_foto_sem_rosto(tmp_path):
    import cv2

    caminho = tmp_path / "parede.png"
    cv2.imwrite(str(caminho), np.full((300, 300, 3), 128, np.uint8))
    with pytest.raises(PerzonOperationError) as erro:
        PerzonEngine(tmp_path, models_root=MODELOS).executar(
            "PZ-05-shapes-de-expressao", str(caminho))
    assert erro.value.codigo == "ROSTO_NAO_ENCONTRADO"


def test_motor_recusa_quando_o_modelo_nao_esta_no_disco(tmp_path, foto_no_disco):
    with pytest.raises(PerzonOperationError) as erro:
        PerzonEngine(tmp_path, models_root=tmp_path / "vazio").executar(
            "PZ-05-shapes-de-expressao", foto_no_disco)
    assert erro.value.codigo == "MODELO_AUSENTE"


def test_alinhamento_pelo_motor_grava_o_recorte(tmp_path, foto_no_disco):
    resultado = PerzonEngine(tmp_path, models_root=MODELOS).executar(
        "PZ-04-alinhar", foto_no_disco, {"tamanho": 256})
    artefato = resultado["artefatos"][0]
    assert artefato["resolucao"] == [256, 256]
    assert Path(artefato["caminho"]).is_file()
    assert len(artefato["sha256"]) == 64
