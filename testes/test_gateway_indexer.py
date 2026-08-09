"""Gateway de provedores e indexador da biblioteca.

O que importa testar aqui é a decisão, não a rede: qual provedor o gateway escolhe,
o que ele faz quando não há modelo, e se o indexador continua útil sem modelo de visão.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cinenode.gateway import CAPABILITY_SLOTS, AIGateway, GatewayError
from cinenode.indexer import CATEGORIAS, AssetIndexer, _slug, _tokens


# ---- helpers ---------------------------------------------------------------

class FakeStore:
    """Store mínimo: o gateway só precisa de settings e audit."""

    def __init__(self, settings=None):
        self._settings = dict(settings or {})
        self.audits = []

    def get_setting(self, key):
        return self._settings.get(key)

    def set_setting(self, key, value):
        self._settings[key] = value

    def audit(self, *args, **kwargs):
        self.audits.append((args, kwargs))


LOCAIS = [
    {"id": "qwen3:8b-q4_K_M", "provider": "ollama", "local": True},
    {"id": "llava:13b", "provider": "ollama", "local": True},
    {"id": "nomic-embed-text:latest", "provider": "ollama", "local": True},
]
REMOTOS = [
    {"id": "anthropic/claude-sonnet-4.5", "provider": "openrouter", "local": False},
    {"id": "google/gemini-2.5-flash", "provider": "openrouter", "local": False},
]


# ---- gateway ---------------------------------------------------------------

def test_slots_declaram_dicas_locais_e_remotas():
    for slot, spec in CAPABILITY_SLOTS.items():
        assert spec["local_hints"], f"{slot} sem dica local"
        assert spec["remote_hints"], f"{slot} sem dica remota"
        assert spec["label"] and spec["description"], f"{slot} sem texto para a UI"


def test_local_first_prefere_modelo_local_mesmo_com_remoto_disponivel():
    gateway = AIGateway(FakeStore())
    escolha = gateway._resolve("texto.raciocinio", LOCAIS, REMOTOS, gateway.settings())
    assert escolha["provider"] == "ollama"
    assert escolha["local"] is True


def test_local_only_nao_cai_para_remoto():
    """A promessa de local-first vira mentira se ela silenciosamente usar a nuvem."""
    store = FakeStore({"ai_gateway": {"policy": "LOCAL_ONLY"}})
    gateway = AIGateway(store)
    # 'codigo' não tem modelo local nesta lista; com LOCAL_ONLY o resultado é nenhum.
    assert gateway._resolve("codigo", LOCAIS, REMOTOS, gateway.settings()) is None


def test_sem_modelo_local_usa_remoto_quando_permitido():
    gateway = AIGateway(FakeStore())
    escolha = gateway._resolve("codigo", LOCAIS, REMOTOS, gateway.settings())
    assert escolha["provider"] == "openrouter"
    assert "sem modelo local" in escolha["reason"]


def test_escolha_do_usuario_vence_a_heuristica():
    store = FakeStore({"ai_gateway": {
        "bindings": {"visao": {"provider": "ollama", "model": "llava:13b"}}}})
    gateway = AIGateway(store)
    escolha = gateway._resolve("visao", LOCAIS, REMOTOS, gateway.settings())
    assert escolha["model"] == "llava:13b"
    assert escolha["reason"] == "escolha do usuário"


def test_binding_para_modelo_que_sumiu_nao_trava_o_slot():
    """Desinstalar um modelo não pode deixar a capacidade sem resposta."""
    store = FakeStore({"ai_gateway": {
        "bindings": {"visao": {"provider": "ollama", "model": "modelo-que-nao-existe"}}}})
    gateway = AIGateway(store)
    escolha = gateway._resolve("visao", LOCAIS, REMOTOS, gateway.settings())
    assert escolha is not None
    assert escolha["model"] != "modelo-que-nao-existe"


def test_chave_nunca_volta_em_texto_claro():
    """A tela mostra que existe chave; ela nunca devolve a chave."""
    store = FakeStore()
    gateway = AIGateway(store)
    gateway.save_settings({"openrouter_key": "sk-or-segredo", "openrouter_enabled": True})
    exposto = json.dumps(gateway.settings())
    assert "sk-or-segredo" not in exposto
    assert gateway.settings()["openrouter_key_set"] is True


def test_salvar_sem_chave_nao_apaga_a_existente():
    """Salvar a política não pode derrubar a chave por omissão."""
    store = FakeStore()
    gateway = AIGateway(store)
    gateway.save_settings({"openrouter_key": "sk-or-abc", "openrouter_enabled": True})
    gateway.save_settings({"policy": "HYBRID"})
    assert gateway.settings()["openrouter_key_set"] is True


def test_limpar_chave_desliga_o_openrouter():
    store = FakeStore()
    gateway = AIGateway(store)
    gateway.save_settings({"openrouter_key": "sk-or-abc", "openrouter_enabled": True})
    gateway.save_settings({"clear_openrouter_key": True})
    assert gateway.settings()["openrouter_key_set"] is False
    assert gateway.settings()["openrouter_enabled"] is False


def test_erro_do_gateway_sempre_diz_como_corrigir():
    erro = GatewayError("SEM_MODELO", "Nada disponível.", "Rode ollama pull qwen3:4b")
    dados = erro.as_dict()
    assert dados["como_corrigir"], "erro sem instrução é erro inútil"
    assert set(dados) == {"erro", "mensagem", "como_corrigir"}


# ---- indexador -------------------------------------------------------------

def test_slug_e_previsivel_e_sem_acento():
    assert _slug("Fachada à Noite, Chuva") == "fachada-a-noite-chuva"
    assert _slug("///") == "sem-titulo"


def test_tokens_ignoram_acento_e_palavras_curtas():
    assert "fachada" in _tokens("Fachada")
    assert "de" not in _tokens("de casa")


def test_toda_categoria_tem_subcategoria():
    for categoria, subs in CATEGORIAS.items():
        assert subs, f"{categoria} sem subcategoria"
        assert all(isinstance(s, str) and s for s in subs)


def test_normalize_forca_categoria_invalida_de_volta_para_a_lista():
    """Modelo pequeno inventa taxonomia. O normalizador é o que impede a bagunça."""
    indexer = AssetIndexer(FakeStore(), AIGateway(FakeStore()))
    ficha = indexer._normalize(
        {"titulo": "Teste", "categoria": "coisa-inventada", "subcategoria": "outra",
         "etiquetas": ["a", "b"], "descricao": "x"},
        {"kind": "image"}, Path("x.png"), modelo="m", provedor="p",
    )
    assert ficha["categoria"] in CATEGORIAS
    assert ficha["subcategoria"] in CATEGORIAS[ficha["categoria"]]


def test_normalize_limita_etiquetas():
    indexer = AssetIndexer(FakeStore(), AIGateway(FakeStore()))
    ficha = indexer._normalize(
        {"titulo": "T", "categoria": "objeto", "subcategoria": "produto",
         "etiquetas": [f"tag{i}" for i in range(30)], "descricao": "d"},
        {"kind": "image"}, Path("x.png"), modelo="m", provedor="p",
    )
    assert len(ficha["etiquetas"]) <= 8


def test_fallback_deterministico_produz_ficha_utilizavel(tmp_path):
    """Sem modelo de visão a biblioteca ainda precisa ser navegável."""
    indexer = AssetIndexer(FakeStore(), AIGateway(FakeStore()))
    arquivo = tmp_path / "render_final_v2.png"
    arquivo.write_bytes(b"x")
    ficha = indexer._index_deterministic(
        {"kind": "image", "original_name": "render_final_v2.png"}, arquivo)
    assert ficha["origem"] == "deterministico"
    assert ficha["categoria"] in CATEGORIAS
    assert ficha["titulo"]


@pytest.mark.parametrize("slot", sorted(CAPABILITY_SLOTS))
def test_todo_slot_resolve_com_algum_modelo_local_instalado(slot):
    """Com modelos instalados, nenhum slot pode ficar órfão em LOCAL_FIRST."""
    gateway = AIGateway(FakeStore())
    todos = LOCAIS + [{"id": "qwen3-coder:7b", "provider": "ollama", "local": True}]
    assert gateway._resolve(slot, todos, [], gateway.settings()) is not None
