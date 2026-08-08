"""TEST-002: cobrir a lógica de `workflow.py`, o módulo mais crítico e menos testado.

Medido antes destes testes: 45% de cobertura em 498 declarações, contra 1.036 linhas
que decidem resolução, qualidade, movimento de câmera e validação de grafo. Erro aqui
não trava — produz vídeo no formato errado, e ninguém percebe até o master.
"""
from __future__ import annotations

import math

import pytest

from cinenode.engines.common import EngineExecutionError
from cinenode.workflow import (
    ASPECT_RATIOS,
    CAMERA_LOOKS,
    CAMERA_MOTIONS,
    CATALOG_BY_TYPE,
    IMAGE_RESOLUTIONS,
    NODE_CATALOG,
    QUALITY_PRESETS,
    VIDEO_RESOLUTIONS,
    apply_camera_look,
    apply_camera_motion,
    apply_quality,
    resolve_dimensions,
)


# ---- resolução: onde o formato errado nasce ---------------------------------

@pytest.mark.parametrize("aspecto", sorted(ASPECT_RATIOS))
def test_toda_proporcao_produz_dimensao_multipla_de_8(aspecto):
    """Difusão exige múltiplo do bloco. Um pixel a mais e o engine recusa ou corta."""
    largura, altura = resolve_dimensions(
        {"aspect_ratio": aspecto, "resolution": "4K"}, kind="image", multiple=8)
    assert largura % 8 == 0, f"{aspecto}: largura {largura} não é múltipla de 8"
    assert altura % 8 == 0, f"{aspecto}: altura {altura} não é múltipla de 8"
    assert largura > 0 and altura > 0


@pytest.mark.parametrize("aspecto,esperado", sorted(ASPECT_RATIOS.items()))
def test_proporcao_resultante_bate_com_a_declarada(aspecto, esperado):
    """A razão real entre os lados precisa bater com a proporção pedida.

    O arredondamento para múltiplo de 8 introduz desvio; acima de 1% o usuário
    receberia um formato diferente do que escolheu.
    """
    largura, altura = resolve_dimensions(
        {"aspect_ratio": aspecto, "resolution": "4K"}, kind="image", multiple=8)
    obtido = largura / altura
    assert abs(obtido - esperado) / esperado < 0.01, (
        f"{aspecto}: pedido {esperado:.4f}, obtido {obtido:.4f}")


def test_manual_preserva_os_numeros_do_usuario():
    """Preset não pode sequestrar quem escolheu números exatos."""
    for config in ({"aspect_ratio": "manual", "resolution": "4K", "width": 777, "height": 333},
                   {"aspect_ratio": "16:9", "resolution": "manual", "width": 777, "height": 333}):
        assert resolve_dimensions(config, kind="image", multiple=8) == (777, 333)


def test_combinacao_invalida_falha_com_codigo_acionavel():
    with pytest.raises(EngineExecutionError) as exc:
        resolve_dimensions({"aspect_ratio": "3:7", "resolution": "4K"}, kind="image", multiple=8)
    assert exc.value.code == "INVALID_FORMAT_PRESET"
    assert "3:7" in exc.value.message


def test_resolucao_de_imagem_e_de_video_sao_tabelas_diferentes():
    """`4K` de vídeo é 2160 de altura; `4K` de imagem também, mas `base` difere:
    1024 contra 480. Trocar a tabela produziria vídeo em resolução de imagem."""
    _, altura_imagem = resolve_dimensions(
        {"aspect_ratio": "1:1", "resolution": "base"}, kind="image", multiple=8)
    _, altura_video = resolve_dimensions(
        {"aspect_ratio": "1:1", "resolution": "base"}, kind="video", multiple=8)
    assert altura_imagem == IMAGE_RESOLUTIONS["base"]
    assert altura_video == VIDEO_RESOLUTIONS["base"]
    assert altura_imagem != altura_video


def test_multiplo_maior_ainda_produz_dimensao_valida():
    """Alguns engines de vídeo exigem múltiplo de 16 ou 32."""
    for multiplo in (8, 16, 32, 64):
        largura, altura = resolve_dimensions(
            {"aspect_ratio": "16:9", "resolution": "FHD"}, kind="video", multiple=multiplo)
        assert largura % multiplo == 0 and altura % multiplo == 0
        assert largura >= multiplo and altura >= multiplo


def test_oito_k_de_imagem_nao_estoura_o_limite_do_catalogo():
    """O campo `width` do catálogo declara max 8192. Um preset acima disso seria
    recusado pelo validador depois de o usuário já ter escolhido."""
    campos = {c["key"]: c for c in CATALOG_BY_TYPE["image.generate"]["fields"]}
    for aspecto in ASPECT_RATIOS:
        for resolucao in IMAGE_RESOLUTIONS:
            largura, altura = resolve_dimensions(
                {"aspect_ratio": aspecto, "resolution": resolucao}, kind="image", multiple=8)
            assert largura <= campos["width"]["max"], (
                f"{aspecto} {resolucao} gera {largura}, acima do max {campos['width']['max']}")
            assert altura <= campos["height"]["max"], (
                f"{aspecto} {resolucao} gera {altura}, acima do max {campos['height']['max']}")


# ---- qualidade --------------------------------------------------------------

@pytest.mark.parametrize("perfil", sorted(QUALITY_PRESETS))
def test_perfil_de_qualidade_define_passos_e_cfg(perfil):
    para_imagem = apply_quality({"quality": perfil}, kind="image")
    para_video = apply_quality({"quality": perfil}, kind="video")
    assert para_imagem["steps"] == QUALITY_PRESETS[perfil]["steps_image"]
    assert para_video["steps"] == QUALITY_PRESETS[perfil]["steps_video"]
    assert para_imagem["cfg_scale"] == QUALITY_PRESETS[perfil]["cfg_scale"]


def test_qualidade_manual_nao_toca_em_nada():
    original = {"quality": "manual", "steps": 13, "cfg_scale": 3.5}
    assert apply_quality(dict(original), kind="image") == original


def test_perfis_de_qualidade_sao_monotonicos():
    """Rascunho não pode custar mais que ultra: a ordem é a promessa da UI."""
    ordem = ["rascunho", "padrão", "cinema", "ultra"]
    passos = [QUALITY_PRESETS[p]["steps_image"] for p in ordem]
    assert passos == sorted(passos), f"passos fora de ordem: {dict(zip(ordem, passos))}"
    passos_video = [QUALITY_PRESETS[p]["steps_video"] for p in ordem]
    assert passos_video == sorted(passos_video)


def test_qualidade_nao_apaga_campo_que_nao_gerencia():
    resultado = apply_quality({"quality": "cinema", "seed": 42, "engine": "sd_cpp"}, kind="image")
    assert resultado["seed"] == 42
    assert resultado["engine"] == "sd_cpp"


# ---- câmera -----------------------------------------------------------------

@pytest.mark.parametrize("movimento", sorted(CAMERA_MOTIONS))
def test_movimento_de_camera_anexa_sem_duplicar_pontuacao(movimento):
    resultado = apply_camera_motion("uma cidade à noite.", movimento)
    assert ".." not in resultado
    assert ", ," not in resultado
    if CAMERA_MOTIONS[movimento]:
        assert CAMERA_MOTIONS[movimento] in resultado
    else:
        assert resultado == "uma cidade à noite."


@pytest.mark.parametrize("look", sorted(CAMERA_LOOKS))
def test_acabamento_de_camera_anexa_sem_duplicar_pontuacao(look):
    resultado = apply_camera_look("retrato de estúdio.", look)
    assert ".." not in resultado
    if CAMERA_LOOKS[look]:
        assert CAMERA_LOOKS[look] in resultado


def test_movimento_desconhecido_nao_quebra_o_prompt():
    """Grafo antigo com movimento removido do catálogo não pode derrubar o job."""
    assert apply_camera_motion("cena", "movimento-que-nao-existe") == "cena"


def test_movimento_ignora_acento_e_caixa():
    assert apply_camera_motion("cena", "ÓRBITA 360") == apply_camera_motion("cena", "órbita 360")
    assert apply_camera_motion("cena", "  dolly in  ") != "cena"


def test_movimento_e_acabamento_compoem_na_ordem():
    prompt = apply_camera_look(apply_camera_motion("praia", "dolly in"), "hora dourada")
    assert CAMERA_MOTIONS["dolly in"] in prompt
    assert CAMERA_LOOKS["hora dourada"] in prompt


def test_nenhum_fragmento_de_camera_esta_vazio_por_engano():
    """Só `nenhum` pode ter fragmento vazio; os outros existem para dizer algo."""
    for nome, fragmento in CAMERA_MOTIONS.items():
        if nome != "nenhum":
            assert fragmento.strip(), f"movimento {nome} sem descrição"
    for nome, fragmento in CAMERA_LOOKS.items():
        if nome != "nenhum":
            assert fragmento.strip(), f"look {nome} sem descrição"


# ---- integridade do catálogo ------------------------------------------------

def test_opcoes_do_catalogo_batem_com_as_tabelas():
    """Opção na UI que não existe na tabela produz erro só na execução."""
    video = CATALOG_BY_TYPE["video.generate"]
    campos = {campo["key"]: campo for campo in video["fields"]}
    assert set(campos["camera_motion"]["options"]) == set(CAMERA_MOTIONS)
    assert set(campos["camera_look"]["options"]) == set(CAMERA_LOOKS)
    assert set(campos["aspect_ratio"]["options"]) == set(ASPECT_RATIOS) | {"manual"}
    assert set(campos["resolution"]["options"]) == set(VIDEO_RESOLUTIONS) | {"manual"}
    assert set(campos["quality"]["options"]) == set(QUALITY_PRESETS) | {"manual"}


def test_imagem_usa_a_tabela_de_resolucao_de_imagem():
    campos = {campo["key"]: campo for campo in CATALOG_BY_TYPE["image.generate"]["fields"]}
    assert set(campos["resolution"]["options"]) == set(IMAGE_RESOLUTIONS) | {"manual"}


def test_todo_default_do_catalogo_e_uma_opcao_valida():
    """Default fora da lista deixa o nó inválido no instante em que é criado."""
    erros = []
    for item in NODE_CATALOG:
        for campo in item.get("fields", []):
            if campo["type"] != "select" or "default" not in campo:
                continue
            opcoes = [str(o) for o in (campo.get("options") or [])]
            if opcoes and str(campo["default"]) not in opcoes:
                erros.append(f"{item['type']}.{campo['key']} = {campo['default']!r}")
    assert not erros, f"defaults fora das opções: {erros}"


def test_todo_numero_com_faixa_tem_default_dentro_dela():
    erros = []
    for item in NODE_CATALOG:
        for campo in item.get("fields", []):
            if campo["type"] != "number" or campo.get("default") is None:
                continue
            minimo, maximo = campo.get("min"), campo.get("max")
            valor = campo["default"]
            if minimo is not None and valor < minimo:
                erros.append(f"{item['type']}.{campo['key']}: {valor} < min {minimo}")
            if maximo is not None and valor > maximo:
                erros.append(f"{item['type']}.{campo['key']}: {valor} > max {maximo}")
    assert not erros, erros


def test_toda_porta_declarada_tem_tipo_conhecido():
    """Porta com tipo inventado nunca conecta, e o usuário não descobre por quê."""
    # A sintaxe real carrega sufixo de cardinalidade: `?` opcional, `*` múltiplo.
    conhecidos = {"text", "image", "video", "audio", "media", "data", "model3d"}
    erros = []
    for item in NODE_CATALOG:
        for lado in ("inputs", "outputs"):
            for porta in item.get(lado) or []:
                tipo = str(porta).split(":")[-1].rstrip("?*")
                if tipo not in conhecidos:
                    erros.append(f"{item['type']}.{lado}: {porta}")
    assert not erros, f"portas com tipo desconhecido: {erros}"


def test_todo_no_gerador_termina_em_algo_visivel():
    """Nó que produz mídia e não tem saída não pode existir: o resultado some."""
    sem_saida = [
        item["type"] for item in NODE_CATALOG
        if item["category"] in {"Imagem", "Vídeo", "3D"} and not item.get("outputs")
    ]
    assert not sem_saida, f"geradores sem saída: {sem_saida}"
