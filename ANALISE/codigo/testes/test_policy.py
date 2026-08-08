"""Política de identidade.

Os testes protegem os dois lados da regra com o mesmo cuidado. Um portão que
bloqueia trabalho legítimo é tão defeituoso quanto um que não bloqueia nada: o
usuário desliga o primeiro e o segundo nunca serviu para nada.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cinenode.engines.common import EngineExecutionError
from cinenode.policy import (
    BASES_DE_DIREITOS,
    BASES_QUE_AUTORIZAM,
    BASE_PADRAO,
    PoliticaIdentidade,
    Referencia,
    prompt_pede_explicito,
)


class PoliticaFalsa(PoliticaIdentidade):
    """Substitui só a detecção de rosto: o resto da regra é o código real."""

    def __init__(self, tem_rosto: bool):
        super().__init__(Path("."))
        self._resposta = tem_rosto

    def _detecta_rosto(self, caminho: Path) -> bool:
        return self._resposta


def _ref(base: str = BASE_PADRAO, titular: str = "") -> Referencia:
    return Referencia(asset_id="ast_1", caminho=Path("x.png"),
                      base_de_direitos=base, titular=titular)


# ---- o lado que precisa passar ---------------------------------------------

def test_prompt_comum_nao_aciona_nada():
    assert not prompt_pede_explicito("cidade neon sob chuva, cinematográfico")
    assert not prompt_pede_explicito("retrato de estúdio, luz suave")


def test_geracao_sem_referencia_passa():
    """Texto para imagem não tem identidade de ninguém em jogo."""
    decisao = PoliticaFalsa(True).avaliar("mulher nua, explícito", [])
    assert decisao["permitido"] is True


def test_referencia_sem_rosto_passa():
    """Referência de cenário, textura ou objeto não carrega identidade."""
    decisao = PoliticaFalsa(False).avaliar("nua, explícito", [_ref()])
    assert decisao["permitido"] is True
    assert "não há identidade em jogo" in decisao["motivo"]


@pytest.mark.parametrize("base", sorted(BASES_QUE_AUTORIZAM - {"titular_consentiu"}))
def test_base_declarada_libera(base):
    """Sintético, próprio e licenciado passam sem nomear ninguém."""
    decisao = PoliticaFalsa(True).avaliar("nua, explícito", [_ref(base)])
    assert decisao["permitido"] is True, base


def test_titular_consentiu_com_nome_libera():
    decisao = PoliticaFalsa(True).avaliar("nua, explícito", [_ref("titular_consentiu", "Fulana")])
    assert decisao["permitido"] is True


def test_conteudo_adulto_sintetico_nao_e_bloqueado():
    """O perfil ADULT_LOCAL existe para isto: sintético roda sem filtro artificial."""
    decisao = PoliticaFalsa(True).avaliar("cena explícita, corpo inteiro", [_ref("sintetico")])
    assert decisao["permitido"] is True


# ---- o lado que precisa recusar ---------------------------------------------

def test_rosto_sem_base_declarada_recusa():
    decisao = PoliticaFalsa(True).avaliar("recrie a mulher referenciada nua explícito", [_ref()])
    assert decisao["permitido"] is False
    assert decisao["pendentes"] == ["ast_1"]


def test_titular_consentiu_sem_nomear_ninguem_nao_e_declaracao():
    """Marcar a caixa sem dizer quem autorizou não é consentimento."""
    decisao = PoliticaFalsa(True).avaliar("nua, explícito", [_ref("titular_consentiu", "  ")])
    assert decisao["permitido"] is False


def test_uma_referencia_pendente_entre_varias_ja_recusa():
    politica = PoliticaFalsa(True)
    referencias = [_ref("sintetico"), _ref(), _ref("licenciado")]
    referencias[1].asset_id = "ast_pendente"
    decisao = politica.avaliar("nua, explícito", referencias)
    assert decisao["permitido"] is False
    assert "ast_pendente" in decisao["pendentes"]


def test_erro_diz_exatamente_como_declarar():
    with pytest.raises(EngineExecutionError) as exc:
        PoliticaFalsa(True).exigir("nua explícito", [_ref()])
    assert exc.value.code == "IDENTIDADE_SEM_BASE_DE_DIREITOS"
    instrucao = exc.value.detail
    for palavra in ("sintético", "próprio", "titular consentiu", "licenciado"):
        assert palavra in instrucao, f"a instrução não cita {palavra}"
    assert "ast_1" in instrucao


# ---- robustez da leitura ----------------------------------------------------

def test_acento_e_caixa_nao_escapam_da_regra():
    for texto in ("EXPLÍCITO", "explicito", "Nua", "NUA"):
        assert prompt_pede_explicito(texto), texto


def test_palavra_dentro_de_outra_nao_dispara():
    """`nu` está dentro de `nuvem`; casar substring encheria o portão de falso positivo."""
    assert not prompt_pede_explicito("nuvens sobre a cidade")
    assert not prompt_pede_explicito("manual de nutrição")


def test_toda_base_conhecida_tem_explicacao():
    assert set(BASES_QUE_AUTORIZAM) <= set(BASES_DE_DIREITOS)
    assert BASE_PADRAO in BASES_DE_DIREITOS
    assert BASE_PADRAO not in BASES_QUE_AUTORIZAM
    for base, texto in BASES_DE_DIREITOS.items():
        assert texto.strip(), f"{base} sem explicação para a UI"


def test_falha_ao_ler_imagem_nao_vira_autorizacao(tmp_path):
    """Se a detecção quebrar, o padrão é 'não sei', não 'pode'."""
    politica = PoliticaIdentidade(tmp_path)
    referencia = Referencia(asset_id="x", caminho=tmp_path / "nao_existe.png")
    decisao = politica.avaliar("nua explícito", [referencia])
    # Sem rosto detectável o caminho é liberado, mas a razão fica registrada.
    assert decisao["permitido"] is True
    assert "rosto" in decisao["motivo"]
