"""DNA humano: medidas reais extraídas das fotos, não estimadas por prompt.

Roda MediaPipe local (CPU) sobre cada referência aprovada e produz um `HumanDNA`
com números medidos: 478 pontos de face com malha 3D, 33 de corpo com profundidade,
e as proporções derivadas deles.

O que este módulo NÃO faz, e o docstring existe para não deixar dúvida:
não reconstrói malha 3D, não gera textura, não faz rig. Ele produz a base
paramétrica medida sobre a qual essas etapas podem operar. Cada número tem
proveniência: qual foto, qual landmark, qual confiança.

Unidades: sem uma referência de escala conhecida, uma foto não dá centímetros.
Por isso tudo sai em **proporção** (razões adimensionais) e só vira métrico quando
o usuário informa a altura real. Inventar centímetros a partir de pixels seria
exatamente o tipo de número falso que este projeto recusa.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .common import EngineExecutionError

MODELOS_DIR_PADRAO = "models/mediapipe"
FACE_TASK = "face_landmarker.task"
POSE_TASK = "pose_landmarker_full.task"

# Índices do face mesh do MediaPipe (canônico, 478 pontos com refinamento de íris).
FACE_PONTOS = {
    "queixo": 152,          # mento
    "testa": 10,            # triquio, topo da testa
    "glabela": 9,           # entre as sobrancelhas
    "nasio": 168,           # raiz do nariz, entre os olhos
    "nariz_ponta": 1,       # pronasal
    "nariz_base": 2,        # subnasal, sob a columela
    "olho_esq_ext": 33,
    "olho_esq_int": 133,
    "olho_dir_int": 362,
    "olho_dir_ext": 263,
    "boca_esq": 61,
    "boca_dir": 291,
    "boca_sup": 13,
    "boca_inf": 14,
    "face_esq": 234,
    "face_dir": 454,
    "sobrancelha_esq": 105,
    "sobrancelha_dir": 334,
    "iris_esq": 468,
    "iris_dir": 473,
}

# Índices do pose landmarker (33 pontos, com z relativo ao quadril).
POSE_PONTOS = {
    "nariz": 0, "ombro_esq": 11, "ombro_dir": 12,
    "cotovelo_esq": 13, "cotovelo_dir": 14,
    "pulso_esq": 15, "pulso_dir": 16,
    "quadril_esq": 23, "quadril_dir": 24,
    "joelho_esq": 25, "joelho_dir": 26,
    "tornozelo_esq": 27, "tornozelo_dir": 28,
    "calcanhar_esq": 29, "calcanhar_dir": 30,
}

# Distância entre as íris: a única medida do rosto humano com dispersão pequena o
# suficiente para servir de régua. Média adulta ~63 mm (Dodgson 2004, N=3976).
# É uma referência estatística, não uma medida do indivíduo — por isso a saída
# métrica derivada dela é marcada como `estimada_por_populacao`.
DISTANCIA_INTERPUPILAR_MM = 63.0

# Acima deste desvio angular a projeção 2D do rosto deixa de representar a forma:
# largura encurta por perspectiva e a razão altura/largura dispara. Medida assim
# parece precisa e não é — por isso ela sai da consolidação em vez de entrar torta.
LIMITE_ANGULO_GRAUS = 35.0



def _angulos_da_matriz(matriz) -> tuple[float, float, float]:
    """Extrai yaw, pitch e roll em graus da matriz 4x4 do MediaPipe.

    Rotação intrínseca na ordem Y-X-Z, que é a convenção da matriz devolvida.
    Sem isso não há como saber se o rosto está de frente — e medida de rosto de
    perfil projetada em 2D produz proporção errada com cara de certeza.
    """
    m = matriz
    sy = math.sqrt(m[0][0] ** 2 + m[1][0] ** 2)
    if sy > 1e-6:
        pitch = math.atan2(m[2][1], m[2][2])
        yaw = math.atan2(-m[2][0], sy)
        roll = math.atan2(m[1][0], m[0][0])
    else:
        pitch = math.atan2(-m[1][2], m[1][1])
        yaw = math.atan2(-m[2][0], sy)
        roll = 0.0
    return math.degrees(yaw), math.degrees(pitch), math.degrees(roll)


class DnaError(EngineExecutionError):
    pass


class _Escala:
    """Converte a coordenada normalizada do MediaPipe para pixels reais.

    `x` vem dividido pela largura e `y` pela altura. Numa imagem 5504x3072 isso
    infla toda distância vertical em 1,79x — e a razão altura/largura do rosto
    saía 2,9 quando o valor humano fica entre 1,3 e 1,5. Sem esta conversão a
    medida parece precisa e é fruto do formato do arquivo.
    """

    __slots__ = ("largura", "altura")

    def __init__(self, largura: int, altura: int):
        self.largura = float(largura)
        self.altura = float(altura)

    def px(self, ponto) -> tuple[float, float, float]:
        # z do face mesh vem na mesma escala de x, ou seja, relativo à largura.
        return (ponto.x * self.largura, ponto.y * self.altura, ponto.z * self.largura)

    def dist2d(self, a, b) -> float:
        ax, ay, _ = self.px(a)
        bx, by, _ = self.px(b)
        return math.hypot(ax - bx, ay - by)

    def dist3d(self, a, b) -> float:
        return math.dist(self.px(a), self.px(b))


@dataclass
class MedidaFace:
    """Proporções faciais adimensionais, todas normalizadas pela largura do rosto."""

    largura_rosto: float
    altura_rosto: float
    distancia_interocular: float
    largura_boca: float
    altura_boca: float
    largura_nariz: float
    altura_nariz: float
    largura_olho_esq: float
    largura_olho_dir: float
    diametro_iris: float
    razao_altura_largura: float
    razao_terco_superior: float
    razao_terco_medio: float
    razao_terco_inferior: float
    assimetria_horizontal: float
    inclinacao_cabeca_graus: float

    def as_dict(self) -> dict[str, float]:
        return {k: round(v, 5) for k, v in self.__dict__.items()}


@dataclass
class MedidaCorpo:
    largura_ombros: float
    largura_quadril: float
    razao_ombro_quadril: float
    comprimento_torso: float
    comprimento_braco_esq: float
    comprimento_braco_dir: float
    comprimento_perna_esq: float
    comprimento_perna_dir: float
    razao_perna_altura: float
    razao_torso_altura: float
    envergadura_relativa: float
    altura_em_cabecas: float
    simetria_membros: float

    def as_dict(self) -> dict[str, float]:
        return {k: round(v, 5) for k, v in self.__dict__.items()}


@dataclass
class LeituraReferencia:
    asset_id: str
    arquivo: str
    largura_px: int
    altura_px: int
    face_detectada: bool = False
    corpo_detectado: bool = False
    face: MedidaFace | None = None
    corpo: MedidaCorpo | None = None
    blendshapes: dict[str, float] = field(default_factory=dict)
    matriz_pose_cabeca: list[list[float]] | None = None
    confianca_face: float = 0.0
    confianca_corpo: float = 0.0
    yaw_graus: float = 0.0
    pitch_graus: float = 0.0
    roll_graus: float = 0.0
    medida_confiavel: bool = True
    aviso: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "arquivo": self.arquivo,
            "resolucao": [self.largura_px, self.altura_px],
            "face_detectada": self.face_detectada,
            "corpo_detectado": self.corpo_detectado,
            "face": self.face.as_dict() if self.face else None,
            "corpo": self.corpo.as_dict() if self.corpo else None,
            "blendshapes_ativos": {k: round(v, 4) for k, v in
                                   sorted(self.blendshapes.items(), key=lambda kv: -kv[1])[:12]
                                   if v > 0.05},
            "matriz_pose_cabeca": self.matriz_pose_cabeca,
            "confianca_face": round(self.confianca_face, 4),
            "confianca_corpo": round(self.confianca_corpo, 4),
            "pose_cabeca_graus": {"yaw": round(self.yaw_graus, 1),
                                  "pitch": round(self.pitch_graus, 1),
                                  "roll": round(self.roll_graus, 1)},
            "medida_confiavel": self.medida_confiavel,
            "aviso": self.aviso,
        }


class HumanDnaEngine:
    """Extrai medidas com MediaPipe local. Sem rede, sem GPU, sem prompt."""

    def __init__(self, models_root: Path):
        self.models_root = Path(models_root)
        self._face_landmarker = None
        self._pose_landmarker = None

    # ---- carga preguiçosa ---------------------------------------------------

    def _caminho(self, nome: str) -> Path:
        caminho = self.models_root / MODELOS_DIR_PADRAO / nome
        if not caminho.is_file():
            raise DnaError(
                "MODELO_AUSENTE",
                f"O modelo {nome} não está em {caminho.parent}.",
                "Baixe de https://storage.googleapis.com/mediapipe-models/ "
                "ou rode scripts/install_humandna.py",
            )
        return caminho

    def _face(self):
        if self._face_landmarker is None:
            from mediapipe.tasks import python as mpp
            from mediapipe.tasks.python import vision
            opcoes = vision.FaceLandmarkerOptions(
                base_options=mpp.BaseOptions(model_asset_path=str(self._caminho(FACE_TASK))),
                # As blendshapes vêm do mesmo passe; pedir depois custaria outra inferência.
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                num_faces=1,
            )
            self._face_landmarker = vision.FaceLandmarker.create_from_options(opcoes)
        return self._face_landmarker

    def _pose(self):
        if self._pose_landmarker is None:
            from mediapipe.tasks import python as mpp
            from mediapipe.tasks.python import vision
            opcoes = vision.PoseLandmarkerOptions(
                base_options=mpp.BaseOptions(model_asset_path=str(self._caminho(POSE_TASK))),
                num_poses=1,
            )
            self._pose_landmarker = vision.PoseLandmarker.create_from_options(opcoes)
        return self._pose_landmarker

    # ---- leitura de uma referência -----------------------------------------

    def ler(self, caminho: Path, asset_id: str = "") -> LeituraReferencia:
        import mediapipe as mp
        import numpy as np
        from PIL import Image

        try:
            imagem = Image.open(caminho).convert("RGB")
        except Exception as exc:
            raise DnaError("IMAGEM_ILEGIVEL", f"Não consegui abrir {caminho.name}.",
                           f"{type(exc).__name__}: {exc}") from exc

        matriz = np.asarray(imagem)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=matriz)
        leitura = LeituraReferencia(
            asset_id=asset_id or caminho.stem,
            arquivo=caminho.name,
            largura_px=imagem.width,
            altura_px=imagem.height,
        )

        escala = _Escala(imagem.width, imagem.height)
        resultado_face = self._face().detect(mp_image)
        if resultado_face.face_landmarks:
            pontos = resultado_face.face_landmarks[0]
            leitura.face_detectada = True
            leitura.face = self._medir_face(pontos, escala)
            leitura.confianca_face = self._confianca_face(pontos)
            if resultado_face.face_blendshapes:
                leitura.blendshapes = {
                    cat.category_name: cat.score
                    for cat in resultado_face.face_blendshapes[0]
                }
            if resultado_face.facial_transformation_matrixes:
                matriz = resultado_face.facial_transformation_matrixes[0]
                leitura.matriz_pose_cabeca = [
                    [round(float(v), 5) for v in linha] for linha in matriz
                ]
                leitura.yaw_graus, leitura.pitch_graus, leitura.roll_graus =                     _angulos_da_matriz(matriz)
                leitura.confianca_face *= self._fator_pose(
                    leitura.yaw_graus, leitura.pitch_graus)
                # Além de LIMITE_ANGULO a projeção 2D deixa de representar a forma.
                if (abs(leitura.yaw_graus) > LIMITE_ANGULO_GRAUS
                        or abs(leitura.pitch_graus) > LIMITE_ANGULO_GRAUS):
                    leitura.medida_confiavel = False
                    leitura.aviso = (
                        f"rosto a {leitura.yaw_graus:.0f} graus de guinada e "
                        f"{leitura.pitch_graus:.0f} de inclinação; as proporções "
                        f"medidas nesta foto não representam a forma real e ficam "
                        f"fora da consolidação")

        resultado_pose = self._pose().detect(mp_image)
        if resultado_pose.pose_landmarks:
            pontos = resultado_pose.pose_landmarks[0]
            visiveis = [p for p in pontos if getattr(p, "visibility", 1.0) > 0.5]
            leitura.confianca_corpo = len(visiveis) / len(pontos)
            # Corpo medido com metade dos pontos escondidos produz proporção falsa.
            if leitura.confianca_corpo >= 0.6:
                leitura.corpo_detectado = True
                leitura.corpo = self._medir_corpo(pontos, leitura.face, escala)
            else:
                leitura.aviso = (f"corpo parcialmente visível "
                                 f"({leitura.confianca_corpo:.0%} dos pontos); medidas de "
                                 f"corpo descartadas nesta foto")

        if not leitura.face_detectada and not leitura.corpo_detectado:
            leitura.aviso = "nenhuma face ou corpo detectado nesta imagem"
        return leitura

    @staticmethod
    def _confianca_face(pontos) -> float:
        """O face landmarker não devolve score por detecção; ele devolve os pontos.

        A confiança útil aqui é geométrica: quanto do rosto está dentro do quadro e
        quão plausível é a malha. Um rosto cortado pela borda produz medidas erradas
        com aparência de certeza, e é isso que este número existe para sinalizar.
        """
        dentro = sum(1 for ponto in pontos if 0.0 <= ponto.x <= 1.0 and 0.0 <= ponto.y <= 1.0)
        cobertura = dentro / len(pontos)

        # Rosto ocupando poucos pixels dá landmark impreciso mesmo estando inteiro.
        xs = [ponto.x for ponto in pontos]
        ys = [ponto.y for ponto in pontos]
        area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        escala = min(1.0, area / 0.04)   # 20% x 20% do quadro já é rosto grande

        return round(cobertura * 0.7 + escala * 0.3, 4)

    @staticmethod
    def _fator_pose(yaw: float, pitch: float) -> float:
        """Cosseno do desvio: de frente vale 1, de perfil tende a 0.

        Multiplica a confiança geométrica porque um rosto inteiro no quadro e bem
        iluminado, mas virado, ainda dá medida ruim.
        """
        desvio = math.hypot(yaw, pitch)
        return max(0.0, math.cos(math.radians(min(desvio, 90.0))))

    # ---- medidas ------------------------------------------------------------

    def _medir_face(self, p, escala: _Escala) -> MedidaFace:
        """Tudo normalizado pela largura do rosto: a única forma de comparar fotos
        de distâncias e enquadramentos diferentes."""
        g = lambda nome: p[FACE_PONTOS[nome]]
        largura = escala.dist2d(g("face_esq"), g("face_dir")) or 1e-6
        altura = escala.dist2d(g("testa"), g("queixo"))
        interocular = escala.dist2d(g("olho_esq_int"), g("olho_dir_int"))
        iris = escala.dist2d(p[468], p[469]) * 2 if len(p) > 473 else 0.0

        # Terços faciais clássicos: testa→sobrancelha, sobrancelha→base do nariz,
        # base do nariz→queixo. Proporção usada em antropometria e escultura.
        py = lambda nome: escala.px(g(nome))[1]
        y_testa = py("testa")
        y_glabela = py("glabela")
        y_nariz, y_queixo = py("nariz_base"), py("queixo")
        total = abs(y_queixo - y_testa) or 1e-6

        # Assimetria: distância do eixo dos olhos ao centro geométrico do rosto.
        px = lambda nome: escala.px(g(nome))[0]
        centro_olhos_x = (px("olho_esq_ext") + px("olho_dir_ext")) / 2
        centro_face_x = (px("face_esq") + px("face_dir")) / 2
        assimetria = abs(centro_olhos_x - centro_face_x) / largura

        dx = px("olho_dir_ext") - px("olho_esq_ext")
        dy = py("olho_dir_ext") - py("olho_esq_ext")
        inclinacao = math.degrees(math.atan2(dy, dx))

        return MedidaFace(
            largura_rosto=1.0,
            altura_rosto=altura / largura,
            distancia_interocular=interocular / largura,
            largura_boca=escala.dist2d(g("boca_esq"), g("boca_dir")) / largura,
            altura_boca=escala.dist2d(g("boca_sup"), g("boca_inf")) / largura,
            largura_nariz=escala.dist2d(p[102], p[331]) / largura,
            altura_nariz=escala.dist2d(g("nasio"), g("nariz_base")) / largura,
            largura_olho_esq=escala.dist2d(g("olho_esq_ext"), g("olho_esq_int")) / largura,
            largura_olho_dir=escala.dist2d(g("olho_dir_int"), g("olho_dir_ext")) / largura,
            diametro_iris=iris / largura,
            razao_altura_largura=altura / largura,
            razao_terco_superior=abs(y_glabela - y_testa) / total,
            razao_terco_medio=abs(y_nariz - y_glabela) / total,
            razao_terco_inferior=abs(y_queixo - y_nariz) / total,
            assimetria_horizontal=assimetria,
            inclinacao_cabeca_graus=inclinacao,
        )

    def _medir_corpo(self, p, face: MedidaFace | None, escala: _Escala) -> MedidaCorpo:
        g = lambda nome: p[POSE_PONTOS[nome]]
        ombros = escala.dist3d(g("ombro_esq"), g("ombro_dir")) or 1e-6
        quadril = escala.dist3d(g("quadril_esq"), g("quadril_dir"))
        py = lambda nome: escala.px(g(nome))[1]
        centro_ombros = (py("ombro_esq") + py("ombro_dir")) / 2
        centro_quadril = (py("quadril_esq") + py("quadril_dir")) / 2
        torso = abs(centro_quadril - centro_ombros)

        braco_esq = escala.dist3d(g("ombro_esq"), g("cotovelo_esq")) + escala.dist3d(g("cotovelo_esq"), g("pulso_esq"))
        braco_dir = escala.dist3d(g("ombro_dir"), g("cotovelo_dir")) + escala.dist3d(g("cotovelo_dir"), g("pulso_dir"))
        perna_esq = escala.dist3d(g("quadril_esq"), g("joelho_esq")) + escala.dist3d(g("joelho_esq"), g("tornozelo_esq"))
        perna_dir = escala.dist3d(g("quadril_dir"), g("joelho_dir")) + escala.dist3d(g("joelho_dir"), g("tornozelo_dir"))

        y_topo = min(py("nariz"), py("ombro_esq"), py("ombro_dir"))
        y_base = max(py("tornozelo_esq"), py("tornozelo_dir"))
        altura = abs(y_base - y_topo) or 1e-6
        perna_media = (perna_esq + perna_dir) / 2

        # Cânone de proporção: altura dividida pela altura da cabeça. 7.5 é a média
        # adulta; 8 é o cânone heroico usado em escultura e concept art.
        altura_cabeca = abs(py("nariz") - y_topo) * 2 if face else 0.0
        em_cabecas = altura / altura_cabeca if altura_cabeca > 1e-6 else 0.0

        maior_braco = max(braco_esq, braco_dir) or 1e-6
        maior_perna = max(perna_esq, perna_dir) or 1e-6
        simetria = ((min(braco_esq, braco_dir) / maior_braco) +
                    (min(perna_esq, perna_dir) / maior_perna)) / 2

        return MedidaCorpo(
            largura_ombros=1.0,
            largura_quadril=quadril / ombros,
            razao_ombro_quadril=ombros / (quadril or 1e-6),
            comprimento_torso=torso / ombros,
            comprimento_braco_esq=braco_esq / ombros,
            comprimento_braco_dir=braco_dir / ombros,
            comprimento_perna_esq=perna_esq / ombros,
            comprimento_perna_dir=perna_dir / ombros,
            razao_perna_altura=perna_media / altura,
            razao_torso_altura=torso / altura,
            envergadura_relativa=(braco_esq + braco_dir + ombros) / altura,
            altura_em_cabecas=em_cabecas,
            simetria_membros=simetria,
        )

    # ---- consolidação -------------------------------------------------------

    def consolidar(
        self,
        leituras: list[LeituraReferencia],
        *,
        altura_real_m: float | None = None,
        consentimento: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Funde as leituras numa ficha. Mediana, não média: uma foto com pose
        ruim desloca a média e não desloca a mediana."""
        import statistics

        # Leitura marcada como não confiável entra no relatório, não na estatística.
        com_face = [l for l in leituras if l.face and l.medida_confiavel]
        com_corpo = [l for l in leituras if l.corpo and l.medida_confiavel]
        descartadas = [l for l in leituras if l.face and not l.medida_confiavel]
        if not com_face and not com_corpo:
            if descartadas:
                angulos = ", ".join(f"{l.arquivo} ({l.yaw_graus:.0f} graus)" for l in descartadas[:3])
                raise DnaError(
                    "TODAS_FORA_DE_ANGULO",
                    f"As {len(descartadas)} referências com rosto estão viradas demais: {angulos}.",
                    "Inclua ao menos uma foto de frente, com desvio abaixo de "
                    f"{LIMITE_ANGULO_GRAUS:.0f} graus.",
                )
            raise DnaError(
                "SEM_MEDIDA",
                "Nenhuma das referências produziu medida de face ou corpo.",
                "Use fotos com o rosto visível e desobstruído, ou corpo inteiro enquadrado.",
            )

        def fundir(objetos: list[Any], campo: str) -> dict[str, Any] | None:
            if not objetos:
                return None
            chaves = objetos[0].__dict__.keys()
            saida = {}
            for chave in chaves:
                valores = [getattr(o, chave) for o in objetos]
                saida[chave] = {
                    "mediana": round(statistics.median(valores), 5),
                    "desvio": round(statistics.pstdev(valores), 5) if len(valores) > 1 else 0.0,
                    "amostras": len(valores),
                }
            return saida

        ficha: dict[str, Any] = {
            "versao": 1,
            "representacao": "MEDIDAS_NORMALIZADAS_MEDIAPIPE",
            "unidades": "adimensional (proporção)",
            "referencias": [l.as_dict() for l in leituras],
            "resumo": {
                "total_referencias": len(leituras),
                "com_face": len(com_face),
                "com_corpo": len(com_corpo),
                "confianca_face_media": round(
                    sum(l.confianca_face for l in com_face) / len(com_face), 4) if com_face else 0.0,
                "confianca_corpo_media": round(
                    sum(l.confianca_corpo for l in com_corpo) / len(com_corpo), 4) if com_corpo else 0.0,
                "descartadas_por_angulo": [
                    {"arquivo": l.arquivo, "yaw": round(l.yaw_graus, 1),
                     "pitch": round(l.pitch_graus, 1)} for l in descartadas
                ],
            },
            "face": fundir([l.face for l in com_face], "face"),
            "corpo": fundir([l.corpo for l in com_corpo], "corpo"),
            "consentimento": consentimento,
            # PRIV-001: 478 pontos faciais e 33 corporais são dado biométrico sob
            # LGPD Art. 5º II. Sem esta classificação, nenhuma política de retenção
            # ou exclusão consegue tratá-lo diferente de um PNG qualquer.
            "classificacao": "biometrico",
            "base_legal_declarada": (consentimento or {}).get("base_de_direitos"),
            "procedencia": {
                "motor": "mediapipe",
                "modelos": [FACE_TASK, POSE_TASK],
                "local": True,
                "rede": False,
            },
        }

        # Métrico só existe com régua. Duas réguas possíveis, e cada uma diz de onde veio.
        if altura_real_m and ficha["corpo"]:
            ficha["metrico"] = self._para_metrico(ficha["corpo"], altura_real_m)
            ficha["metrico"]["origem_da_escala"] = "altura informada pelo usuário"
        elif ficha["face"] and ficha["face"]["distancia_interocular"]["mediana"] > 0:
            ficha["metrico_estimado"] = {
                "aviso": "estimativa por média populacional, não medida deste indivíduo",
                "origem_da_escala": f"distância interpupilar média de {DISTANCIA_INTERPUPILAR_MM} mm",
                "largura_rosto_mm": round(
                    DISTANCIA_INTERPUPILAR_MM / ficha["face"]["distancia_interocular"]["mediana"], 1),
                "confiabilidade": "baixa",
            }
        return ficha

    def _para_metrico(self, corpo: dict[str, Any], altura_m: float) -> dict[str, Any]:
        """Com a altura real, as proporções viram centímetros de verdade."""
        razao_perna = corpo["razao_perna_altura"]["mediana"]
        razao_torso = corpo["razao_torso_altura"]["mediana"]
        ombros_por_altura = 1.0 / (corpo["envergadura_relativa"]["mediana"] or 1e-6)
        return {
            "altura_m": round(altura_m, 3),
            "perna_cm": round(razao_perna * altura_m * 100, 1),
            "torso_cm": round(razao_torso * altura_m * 100, 1),
            "largura_ombros_cm": round(ombros_por_altura * altura_m * 100, 1),
            "cabecas": corpo["altura_em_cabecas"]["mediana"],
        }
