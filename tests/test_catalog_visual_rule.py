"""A regra "todo nó é visual" só vale se estiver testada.

Sem isto, o próximo campo adicionado ao catálogo volta a ser uma lista suspensa
e ninguém percebe até abrir a tela.
"""
from __future__ import annotations

import pytest

from cinenode.workflow import CATALOG_BY_TYPE, NODE_CATALOG

# Controles que a UI desenha de forma visual sem precisar de dica explícita.
TIPOS_VISUAIS_POR_NATUREZA = {"textarea", "asset", "model_profile"}
UI_CONHECIDAS = {"chips", "ratio", "seed", "picker", "slider"}
# Texto livre é legítimo: nome de arquivo, separador, caminho. Não há controle
# visual honesto para eles, e inventar um seria pior que um campo de texto.
TIPOS_TEXTO_LIVRE = {"text", "path", "json"}
CHIP_LIMIT = 8


def campos():
    for item in NODE_CATALOG:
        for field in item.get("fields", []):
            yield item["type"], field


def test_todo_select_tem_controle_visual():
    cruas = [
        f"{tipo}.{field['key']} ({len(field.get('options') or [])} opções)"
        for tipo, field in campos()
        if field["type"] == "select" and field.get("ui") not in UI_CONHECIDAS
    ]
    assert not cruas, f"selects sem controle visual: {cruas}"


def test_select_curto_vira_chips_e_longo_vira_picker():
    erros = []
    for tipo, field in campos():
        if field["type"] != "select":
            continue
        total = len(field.get("options") or [])
        esperado = "chips" if total <= CHIP_LIMIT else "picker"
        if field.get("ui") != esperado and field.get("ui") != "ratio":
            erros.append(f"{tipo}.{field['key']}: {total} opções deveria ser {esperado}, é {field.get('ui')}")
    assert not erros, erros


def test_numero_tem_faixa_para_virar_slider():
    """Número sem faixa vira caixa de digitar. Só escapa quem tem controle próprio,
    como `seed`, que usa o botão de sortear em vez de uma régua."""
    sem_faixa = [
        f"{tipo}.{field['key']}"
        for tipo, field in campos()
        if field["type"] == "number"
        and not field.get("ui")
        and (field.get("min") is None or field.get("max") is None)
    ]
    assert not sem_faixa, f"números sem min/max não viram slider: {sem_faixa}"


def test_nenhum_campo_fica_sem_forma_de_desenho():
    orfaos = []
    for tipo, field in campos():
        if field.get("ui") in UI_CONHECIDAS:
            continue
        if field["type"] in TIPOS_VISUAIS_POR_NATUREZA | TIPOS_TEXTO_LIVRE:
            continue
        if field["type"] == "number":
            continue
        orfaos.append(f"{tipo}.{field['key']} tipo={field['type']}")
    assert not orfaos, orfaos


def test_show_if_referencia_campo_que_existe():
    """Regra de visibilidade apontando para um campo inexistente esconderia o campo para sempre."""
    erros = []
    for item in NODE_CATALOG:
        chaves = {field["key"] for field in item.get("fields", [])}
        for field in item.get("fields", []):
            regra = field.get("show_if")
            if not regra:
                continue
            clausulas = regra.get("any") or regra.get("all") or [regra]
            for clausula in clausulas:
                for chave in clausula:
                    if chave not in chaves:
                        erros.append(f"{item['type']}.{field['key']} depende de {chave!r}, que não existe no nó")
    assert not erros, erros


@pytest.mark.parametrize("tipo", sorted(CATALOG_BY_TYPE))
def test_todo_no_declara_portas_e_rotulo(tipo):
    item = CATALOG_BY_TYPE[tipo]
    assert item.get("label"), f"{tipo} sem rótulo"
    assert item.get("category"), f"{tipo} sem categoria"
    assert item.get("description"), f"{tipo} sem descrição"
    assert item.get("inputs") is not None and item.get("outputs") is not None, f"{tipo} sem portas declaradas"
