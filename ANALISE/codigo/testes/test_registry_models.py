"""MODEL-002: nenhum peso executa sem origem, licença e uso comercial declarados.

A auditoria mediu 33 modelos carregáveis contra 4 governados; a varredura real do
disco e do Ollama achou 44. O registro fecha a lacuna ou aponta com nome o que falta.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from cinenode.api import create_app
from cinenode.registry_models import (
    LICENCAS_QUE_LIBERAM,
    MODELOS,
    TAGS_DE_LICENCA,
    ModelRegistry,
)


# ---- integridade da declaração ----------------------------------------------

def test_toda_licenca_esta_no_vocabulario_fechado():
    """Licença escrita em texto livre não é auditável: cada grafia vira uma tag nova."""
    invalidas = [(m.id, m.licenca) for m in MODELOS if m.licenca not in TAGS_DE_LICENCA]
    assert not invalidas, f"licenças fora do vocabulário: {invalidas}"


def test_todo_modelo_declara_origem_verificavel():
    sem_origem = [m.id for m in MODELOS if not m.origem.strip()]
    assert not sem_origem, f"sem origem declarada: {sem_origem}"


def test_nenhum_id_repetido():
    ids = [m.id for m in MODELOS]
    repetidos = {i for i in ids if ids.count(i) > 1}
    assert not repetidos, f"ids duplicados dariam duas licenças ao mesmo peso: {repetidos}"


def test_licenca_desconhecida_nunca_autoriza_producao():
    """É a regra inteira: o padrão é recusar, não permitir."""
    for modelo in MODELOS:
        if modelo.licenca == "UNKNOWN_BLOCKED":
            assert not modelo.autoriza_producao(), f"{modelo.id} passaria sem licença"


def test_licenca_restritiva_nao_autoriza_producao():
    for tag in ("RESEARCH_ONLY", "NONCOMMERCIAL", "DATA_LICENSE_RESTRICTED"):
        assert tag not in LICENCAS_QUE_LIBERAM, f"{tag} não pode liberar produção"


def test_modelo_autorizado_declara_uso_comercial():
    """Autorizar produção sem dizer se o uso comercial vale é autorizar no escuro."""
    omissos = [m.id for m in MODELOS
               if m.autoriza_producao() and m.uso_comercial == "UNKNOWN"]
    assert not omissos, f"autorizados sem declarar uso comercial: {omissos}"


def test_padroes_sao_minusculos_e_nao_vazios():
    """O casamento normaliza para minúsculas; um padrão maiúsculo nunca casaria."""
    erros = [(m.id, p) for m in MODELOS for p in m.padroes if p != p.lower() or not p.strip()]
    assert not erros, erros


def test_fallback_aponta_para_modelo_que_existe():
    ids = {m.id for m in MODELOS}
    quebrados = [(m.id, m.fallback) for m in MODELOS if m.fallback and m.fallback not in ids]
    assert not quebrados, f"fallback para modelo inexistente: {quebrados}"


# ---- resolução de nomes -----------------------------------------------------

@pytest.mark.parametrize("nome,esperado", [
    ("qwen3:14b", "Qwen/Qwen3"),
    ("qwen3-vl:4b", "Qwen/Qwen3-VL"),
    ("qwen2.5-coder:32b", "Qwen/Qwen2.5"),
    ("deepseek-r1:32b", "deepseek-ai/DeepSeek-R1"),
    ("deepseek-coder:6.7b", "deepseek-ai/DeepSeek-Coder"),
    ("llama3:latest", "meta-llama/Meta-Llama-3"),
    ("nomic-embed-text:latest", "nomic-ai/nomic-embed-text"),
    ("flux1-schnell-Q4_K_S", "black-forest-labs/FLUX.1-schnell"),
    ("t5xxl-Q5_K_M", "google/T5-v1.1-XXL"),
    ("umt5-xxl-encoder-Q5_K_M", "google/T5-v1.1-XXL"),
    ("wan2.1_t2v_1.3B_fp16", "Wan-AI/Wan2.1-weights"),
    ("hunyuan3d-dit-v2_fp16", "tencent/Hunyuan3D-2-weights"),
    ("face_landmarker", "mediapipe/face_landmarker"),
    ("ffmpeg", "FFmpeg/FFmpeg"),
])
def test_nome_real_do_disco_resolve_para_a_declaracao_certa(tmp_path, nome, esperado):
    assert ModelRegistry(tmp_path).resolver(nome).id == esperado


def test_padrao_mais_especifico_ganha(tmp_path):
    """`gpt-oss-cad` é perfil local; `gpt-oss` é a base. Casar com a base perderia
    a informação de que existe um derivado, e com ela a rastreabilidade."""
    registro = ModelRegistry(tmp_path)
    assert registro.resolver("gpt-oss-cad:20b").id == "local/gpt-oss-cad"
    assert registro.resolver("gpt-oss:20b").id == "openai/gpt-oss"


def test_todo_perfil_de_modelo_do_app_tem_licenca_declarada(config, tmp_path):
    """O mesmo peso tem dois nomes: arquivo no disco e perfil no app. Cobrir só um
    deixa metade da superfície fora — foi o que a rota ao vivo pegou e o script não.
    """
    from cinenode.store import _default_model_profiles

    registro = ModelRegistry(tmp_path)
    orfaos = [nome for nome in _default_model_profiles(config)
              if registro.resolver(nome) is None]
    assert not orfaos, f"perfis sem declaração de licença: {orfaos}"


def test_modelo_nunca_visto_nao_e_inventado(tmp_path):
    assert ModelRegistry(tmp_path).resolver("modelo-que-ninguem-declarou:7b") is None


def test_nome_desconhecido_aparece_como_nao_registrado(tmp_path):
    faltando = ModelRegistry(tmp_path).descobrir_nao_registrados(
        ["qwen3:14b", "modelo-fantasma:1b"])
    assert faltando == ["modelo-fantasma:1b"]


def test_relatorio_mapeia_cada_nome_para_sua_declaracao(tmp_path):
    relatorio = ModelRegistry(tmp_path).relatorio(["qwen3:8b", "inexistente:1b"])
    assert relatorio["cobertura"]["qwen3:8b"] == "Qwen/Qwen3"
    assert relatorio["cobertura"]["inexistente:1b"] is None


def test_conferido_no_disco_e_distinto_de_lido_no_card(tmp_path):
    """Tratar pesquisa como evidência é o que transforma o registro em teatro."""
    nao_conferidos = ModelRegistry(tmp_path).nao_conferidos()
    assert "FFmpeg/FFmpeg" not in nao_conferidos, "o build foi medido nesta máquina"
    assert "Qwen/Qwen3" in nao_conferidos, "veio do card upstream, não do disco"


# ---- escopo: o gate não pode acusar quem não tem culpa ----------------------

def test_escopo_limita_o_exame_ao_que_o_modulo_carrega(tmp_path):
    so_video = ModelRegistry(tmp_path, ["video"]).escopo()
    slots = {m.slot for m in so_video}
    assert slots and all(s.startswith("video") for s in slots), slots
    assert len(so_video) < len(MODELOS)


def test_pendencia_de_3d_nao_reprova_o_modulo_de_video(tmp_path):
    """Era o defeito da primeira versão: o gate global reprovava os oito módulos
    por causa de três licenças, e nenhuma delas era de vídeo."""
    video = ModelRegistry(tmp_path, ["video", "media.transform", "upscale.image"])
    assert video.pendencias() == [], [p["id"] for p in video.pendencias()]

    tresde = ModelRegistry(tmp_path, ["model3d"])
    assert [p["id"] for p in tresde.pendencias()] == ["tencent/Hunyuan3D-2-weights"]


def test_escopo_vazio_olha_tudo(tmp_path):
    assert len(ModelRegistry(tmp_path).escopo()) == len(MODELOS)
    assert ModelRegistry(tmp_path).relatorio([])["escopo"] == ["*"]


def test_peso_orfao_so_e_cobrado_no_exame_global(tmp_path):
    """Peso que ninguém declarou também não tem slot: imputá-lo a um módulo
    específico seria inventar a atribuição."""
    orfao = ["peso-sem-dono:1b"]
    assert ModelRegistry(tmp_path, ["video"]).descobrir_nao_registrados(orfao) == []
    assert ModelRegistry(tmp_path).descobrir_nao_registrados(orfao) == orfao


# ---- evidência --------------------------------------------------------------

def test_evidencia_falha_quando_ha_peso_nao_declarado(tmp_path):
    destino = tmp_path / "modelos.json"
    ModelRegistry(tmp_path).gravar_evidencia(destino, ["peso-sem-dono:1b"])
    conteudo = json.loads(destino.read_text(encoding="utf-8"))
    assert conteudo["gate_id"] == "GATE-LICENSE"
    assert conteudo["status"] == "FAIL"
    assert "peso-sem-dono:1b" in conteudo["nao_registrados"]


def test_evidencia_nomeia_o_que_falta_em_cada_pendencia(tmp_path):
    """Evidência que só diz "FAIL" não fecha lacuna nenhuma."""
    relatorio = ModelRegistry(tmp_path).relatorio([])
    for pendente in relatorio["pendentes"]:
        assert pendente["origem"].strip(), f"{pendente['id']} sem onde ler a licença"
        assert pendente["o_que_falta"].strip()


# ---- rota -------------------------------------------------------------------

def test_rota_do_registro_responde_com_pendencias(config):
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.get("/api/models/registry")
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["total_registrado"] == len(MODELOS)
        assert corpo["autorizados"] <= corpo["total_registrado"]
        assert isinstance(corpo["pendentes"], list)
        assert resposta.headers.get("Cache-Control") == "no-store"


def test_rota_do_registro_nao_vaza_chave_de_provedor(config):
    """O relatório passa perto da configuração do gateway; nada de segredo nele."""
    app = create_app(config)
    with TestClient(app) as client:
        texto = client.get("/api/models/registry").text
        assert "openrouter_key" not in texto
        assert "sk-or-" not in texto
