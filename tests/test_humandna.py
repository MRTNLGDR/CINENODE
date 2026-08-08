"""DNA humano: as medidas precisam ser geometricamente corretas, não plausíveis.

Cada teste aqui nasceu de um erro real encontrado ao rodar o motor sobre imagens
de verdade. Os números batiam com a expectativa e estavam errados por motivo
técnico — que é a pior categoria de erro num sistema que promete medida.
"""
from __future__ import annotations

import math

import pytest

from cinenode.engines.humandna import (
    DISTANCIA_INTERPUPILAR_MM,
    FACE_PONTOS,
    LIMITE_ANGULO_GRAUS,
    POSE_PONTOS,
    DnaError,
    HumanDnaEngine,
    LeituraReferencia,
    MedidaFace,
    _angulos_da_matriz,
    _Escala,
)


class Ponto:
    """Landmark do MediaPipe: coordenada normalizada, x por largura e y por altura."""

    def __init__(self, x: float, y: float, z: float = 0.0, visibility: float = 1.0):
        self.x, self.y, self.z, self.visibility = x, y, z, visibility


# ---- escala: o defeito que inflava toda medida vertical ---------------------

def test_escala_corrige_imagem_nao_quadrada():
    """Numa imagem 2:1, x e y normalizados não são comparáveis.

    Este é o defeito que fazia a razão altura/largura do rosto sair 2.9 quando o
    valor humano fica entre 1.3 e 1.5.
    """
    escala = _Escala(2000, 1000)
    horizontal = escala.dist2d(Ponto(0.0, 0.5), Ponto(0.1, 0.5))   # 10% da largura
    vertical = escala.dist2d(Ponto(0.5, 0.0), Ponto(0.5, 0.1))     # 10% da altura
    assert horizontal == pytest.approx(200.0)
    assert vertical == pytest.approx(100.0)
    # Sem a conversão, ambos dariam 0.1 e a razão sairia 1:1 numa imagem 2:1.
    assert horizontal / vertical == pytest.approx(2.0)


def test_escala_quadrada_nao_distorce():
    escala = _Escala(1024, 1024)
    a = escala.dist2d(Ponto(0.0, 0.0), Ponto(0.1, 0.0))
    b = escala.dist2d(Ponto(0.0, 0.0), Ponto(0.0, 0.1))
    assert a == pytest.approx(b)


def test_escala_z_usa_a_largura():
    """O z do face mesh vem na mesma escala de x. Usar altura distorceria a profundidade."""
    escala = _Escala(2000, 1000)
    assert escala.px(Ponto(0.0, 0.0, 0.1))[2] == pytest.approx(200.0)


# ---- ângulos da cabeça ------------------------------------------------------

def test_matriz_identidade_e_rosto_de_frente():
    identidade = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    yaw, pitch, roll = _angulos_da_matriz(identidade)
    assert (abs(yaw), abs(pitch), abs(roll)) == pytest.approx((0.0, 0.0, 0.0), abs=1e-6)


def test_rotacao_de_30_graus_em_yaw_e_lida_como_30():
    a = math.radians(30)
    matriz = [
        [math.cos(a), 0, math.sin(a), 0],
        [0, 1, 0, 0],
        [-math.sin(a), 0, math.cos(a), 0],
        [0, 0, 0, 1],
    ]
    yaw, pitch, roll = _angulos_da_matriz(matriz)
    assert yaw == pytest.approx(30.0, abs=0.5)
    assert abs(pitch) < 0.5 and abs(roll) < 0.5


def test_fator_pose_penaliza_rosto_virado():
    """Rosto de frente vale 1; de perfil tende a zero. Sem isso, uma foto de costas
    marcava confiança 0.99 porque estava inteira no quadro."""
    assert HumanDnaEngine._fator_pose(0, 0) == pytest.approx(1.0)
    assert HumanDnaEngine._fator_pose(60, 0) < 0.55
    assert HumanDnaEngine._fator_pose(90, 0) == pytest.approx(0.0, abs=1e-6)
    assert HumanDnaEngine._fator_pose(45, 45) < HumanDnaEngine._fator_pose(45, 0)


def test_fator_pose_nunca_e_negativo():
    assert HumanDnaEngine._fator_pose(179, 179) >= 0.0


# ---- confiança --------------------------------------------------------------

def test_confianca_cai_com_rosto_cortado_pela_borda():
    dentro = [Ponto(0.4 + i * 0.001, 0.4 + i * 0.001) for i in range(100)]
    fora = [Ponto(-0.3, 0.5) for _ in range(50)] + dentro
    assert HumanDnaEngine._confianca_face(fora) < HumanDnaEngine._confianca_face(dentro)


def test_confianca_cai_com_rosto_pequeno_no_quadro():
    grande = [Ponto(0.3, 0.3), Ponto(0.7, 0.7)]
    pequeno = [Ponto(0.49, 0.49), Ponto(0.51, 0.51)]
    assert HumanDnaEngine._confianca_face(pequeno) < HumanDnaEngine._confianca_face(grande)


# ---- índices antropométricos ------------------------------------------------

def test_nariz_base_e_subnasal_nao_o_nasio():
    """168 é a raiz do nariz, entre os olhos. Usá-lo como base fazia o terço
    inferior sair 0.71 quando os três terços somam 1 e ficam perto de 0.33."""
    assert FACE_PONTOS["nasio"] == 168
    assert FACE_PONTOS["nariz_base"] == 2
    assert FACE_PONTOS["nariz_base"] != FACE_PONTOS["nasio"]


def test_pontos_de_face_sao_indices_validos_do_mesh():
    """O face mesh canônico tem 478 pontos com refinamento de íris."""
    for nome, indice in FACE_PONTOS.items():
        assert 0 <= indice < 478, f"{nome} fora do mesh: {indice}"


def test_pontos_de_pose_sao_indices_validos():
    for nome, indice in POSE_PONTOS.items():
        assert 0 <= indice < 33, f"{nome} fora do modelo de pose: {indice}"


def test_indices_de_face_nao_se_repetem():
    """Dois nomes no mesmo ponto produziriam medida zero sem avisar."""
    repetidos = [i for i in FACE_PONTOS.values() if list(FACE_PONTOS.values()).count(i) > 1]
    assert not repetidos, f"índices repetidos: {set(repetidos)}"


# ---- consolidação -----------------------------------------------------------

def _leitura(nome: str, *, confiavel: bool = True, yaw: float = 0.0) -> LeituraReferencia:
    face = MedidaFace(
        largura_rosto=1.0, altura_rosto=1.4, distancia_interocular=0.3,
        largura_boca=0.35, altura_boca=0.05, largura_nariz=0.25, altura_nariz=0.4,
        largura_olho_esq=0.18, largura_olho_dir=0.18, diametro_iris=0.07,
        razao_altura_largura=1.4, razao_terco_superior=0.33, razao_terco_medio=0.33,
        razao_terco_inferior=0.34, assimetria_horizontal=0.01, inclinacao_cabeca_graus=0.5,
    )
    return LeituraReferencia(
        asset_id=nome, arquivo=f"{nome}.png", largura_px=1024, altura_px=1024,
        face_detectada=True, face=face, confianca_face=0.9,
        yaw_graus=yaw, medida_confiavel=confiavel,
    )


def test_consolidar_usa_mediana_nao_media(tmp_path):
    """Uma foto com pose ruim desloca a média e não desloca a mediana."""
    motor = HumanDnaEngine(tmp_path)
    leituras = [_leitura(f"a{i}") for i in range(3)]
    leituras[0].face.razao_altura_largura = 9.0     # discrepante
    ficha = motor.consolidar(leituras)
    assert ficha["face"]["razao_altura_largura"]["mediana"] == pytest.approx(1.4)


def test_leitura_fora_de_angulo_nao_entra_na_estatistica(tmp_path):
    motor = HumanDnaEngine(tmp_path)
    leituras = [_leitura("boa"), _leitura("virada", confiavel=False, yaw=-50)]
    ficha = motor.consolidar(leituras)
    assert ficha["resumo"]["com_face"] == 1
    assert ficha["resumo"]["descartadas_por_angulo"][0]["arquivo"] == "virada.png"
    assert ficha["face"]["razao_altura_largura"]["amostras"] == 1
    # Mas ela continua no relatório: descartar não é apagar.
    assert len(ficha["referencias"]) == 2


def test_todas_fora_de_angulo_da_erro_com_instrucao(tmp_path):
    motor = HumanDnaEngine(tmp_path)
    leituras = [_leitura("v1", confiavel=False, yaw=-60), _leitura("v2", confiavel=False, yaw=55)]
    with pytest.raises(DnaError) as exc:
        motor.consolidar(leituras)
    assert exc.value.code == "TODAS_FORA_DE_ANGULO"
    assert str(int(LIMITE_ANGULO_GRAUS)) in exc.value.detail
    assert "v1.png" in exc.value.message


def test_sem_leitura_alguma_da_erro_acionavel(tmp_path):
    motor = HumanDnaEngine(tmp_path)
    vazia = LeituraReferencia(asset_id="x", arquivo="x.png", largura_px=10, altura_px=10)
    with pytest.raises(DnaError) as exc:
        motor.consolidar([vazia])
    assert exc.value.code == "SEM_MEDIDA"
    assert exc.value.detail, "erro sem instrução é erro inútil"


def test_metrico_so_existe_com_regua(tmp_path):
    """Sem altura informada não há centímetro medido — só estimativa populacional,
    e ela precisa dizer que é estimativa."""
    motor = HumanDnaEngine(tmp_path)
    ficha = motor.consolidar([_leitura("a")])
    assert "metrico" not in ficha
    assert ficha["metrico_estimado"]["confiabilidade"] == "baixa"
    assert "não medida deste indivíduo" in ficha["metrico_estimado"]["aviso"]
    assert str(DISTANCIA_INTERPUPILAR_MM) in ficha["metrico_estimado"]["origem_da_escala"]


def test_procedencia_declara_execucao_local(tmp_path):
    motor = HumanDnaEngine(tmp_path)
    ficha = motor.consolidar([_leitura("a")])
    assert ficha["procedencia"]["local"] is True
    assert ficha["procedencia"]["rede"] is False


def test_consentimento_viaja_na_ficha(tmp_path):
    motor = HumanDnaEngine(tmp_path)
    consentimento = {"titular": "Fulano", "base_de_direitos": "titular consentiu"}
    ficha = motor.consolidar([_leitura("a")], consentimento=consentimento)
    assert ficha["consentimento"] == consentimento


def test_modelo_ausente_diz_onde_baixar(tmp_path):
    motor = HumanDnaEngine(tmp_path)
    with pytest.raises(DnaError) as exc:
        motor._caminho("nao_existe.task")
    assert exc.value.code == "MODELO_AUSENTE"
    assert "storage.googleapis.com" in exc.value.detail
