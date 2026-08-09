"""Alerta de conclusão de módulo.

O valor deste sistema está nas regras negativas: um alerta que sempre acende não
informa nada. Estes testes protegem exatamente isso — que `CONCLUIDO` seja difícil.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cinenode.modules import (
    ESTADOS,
    FASES,
    GATE_STATUS,
    MODULOS,
    Gate,
    Modulo,
    ModuleRegistry,
    gates_padrao,
)

TIPOS = {"input.text", "input.asset", "output.preview", "image.generate"}


def _modulo(**kwargs) -> Modulo:
    base = dict(id="M-TESTE", titulo="Teste", icone="fluxo", fase="A")
    base.update(kwargs)
    return Modulo(**base)


def _gates(*status: str) -> list[Gate]:
    return [
        Gate(id=f"G{i}", label=f"G{i}", rule="r", command="c", evidence="e", status=s)
        for i, s in enumerate(status)
    ]


# ---- a regra que dá valor ao alerta ----------------------------------------

def test_concluido_exige_todos_os_gates_aprovados():
    modulo = _modulo(gates=_gates("PASS", "PASS", "FAIL"))
    assert modulo.estado(TIPOS) != "CONCLUIDO"


def test_gate_desconhecido_impede_conclusao():
    """Evidência ausente é UNKNOWN. UNKNOWN nunca pode virar concluído."""
    modulo = _modulo(gates=_gates("PASS", "PASS", "UNKNOWN"))
    assert modulo.estado(TIPOS) == "EM_PROGRESSO"


def test_no_prometido_e_ausente_impede_conclusao():
    """Todos os gates verdes, mas o nó não existe: isso é promessa, não entrega."""
    modulo = _modulo(gates=_gates("PASS", "PASS"), nos=["input.text", "no.que.nao.existe"])
    assert modulo.estado(TIPOS) != "CONCLUIDO"
    assert modulo.nos_faltando(TIPOS) == ["no.que.nao.existe"]


def test_modulo_sem_gate_nao_conclui():
    """Sem portão não há prova. Um módulo sem gates fica parcial, nunca pronto."""
    assert _modulo(gates=[]).estado(TIPOS) == "PARCIAL"


def test_bloqueio_declarado_vence_gates_verdes():
    modulo = _modulo(gates=_gates("PASS", "PASS"), bloqueio="depende de licença")
    assert modulo.estado(TIPOS) == "BLOQUEADO"


def test_conclui_quando_tudo_esta_provado():
    modulo = _modulo(gates=_gates("PASS", "PASS"), nos=["input.text", "output.preview"])
    assert modulo.estado(TIPOS) == "CONCLUIDO"
    assert modulo.progresso(TIPOS) == 100


def test_falha_apos_completo_e_regressao_nao_progresso():
    """Distinguir 'ainda não chegou lá' de 'quebrou o que funcionava'."""
    modulo = _modulo(gates=_gates("PASS", "PASS", "PASS", "FAIL"), nos=["input.text"])
    # 3/4 gates + 1/1 nós = 87%, ainda não é regressão
    assert modulo.estado(TIPOS) == "EM_PROGRESSO"


# ---- progresso --------------------------------------------------------------

def test_progresso_pesa_gates_e_nos_igualmente():
    modulo = _modulo(gates=_gates("PASS", "FAIL"), nos=["input.text", "nao.existe"])
    assert modulo.progresso(TIPOS) == 50   # 0.5*0.5 + 0.5*0.5


def test_progresso_sem_nos_declarados_conta_so_os_gates():
    assert _modulo(gates=_gates("PASS", "PASS")).progresso(TIPOS) == 100
    assert _modulo(gates=_gates("PASS", "FAIL")).progresso(TIPOS) == 75


# ---- integridade do roadmap -------------------------------------------------

def test_ids_de_modulo_sao_unicos():
    ids = [m.id for m in MODULOS]
    assert len(ids) == len(set(ids)), "ID repetido faz dois módulos disputarem a mesma evidência"


def test_toda_dependencia_aponta_para_modulo_existente():
    ids = {m.id for m in MODULOS}
    quebradas = [(m.id, d) for m in MODULOS for d in m.depende_de if d not in ids]
    assert not quebradas, f"dependências para módulos inexistentes: {quebradas}"


def test_toda_fase_usada_tem_titulo():
    sem_titulo = sorted({m.fase for m in MODULOS} - set(FASES))
    assert not sem_titulo, f"fases sem título: {sem_titulo}"


def test_todo_modulo_tem_gates():
    assert not [m.id for m in MODULOS if not m.gates]


def test_gate_declara_comando_e_evidencia():
    for modulo in MODULOS:
        for gate in modulo.gates:
            assert gate.command, f"{modulo.id}/{gate.id} sem comando"
            assert gate.evidence, f"{modulo.id}/{gate.id} sem caminho de evidência"
            assert gate.evidence.startswith("docs/evidence/"), gate.evidence


def test_gates_padrao_usam_o_interpretador_atual():
    """`pytest` cru depende do PATH do shell, que no subprocess não tem o venv."""
    for gate in gates_padrao("M-XX"):
        assert "sys.executable" not in gate.command
        assert gate.command.startswith('"'), f"comando sem caminho absoluto: {gate.command}"


def test_estados_e_status_sao_fechados():
    assert set(ESTADOS) == {"CONCLUIDO", "EM_PROGRESSO", "BLOQUEADO", "REGREDIU", "PARCIAL"}
    assert set(GATE_STATUS) == {"PASS", "FAIL", "BLOCKED", "UNKNOWN"}


# ---- registro contra o disco ------------------------------------------------

def test_evidencia_ausente_e_unknown_nao_pass(tmp_path):
    registro = ModuleRegistry(tmp_path, [{"type": t} for t in TIPOS])
    gate = Gate(id="G", label="G", rule="r", command="c", evidence="docs/evidence/X/nao.json")
    registro._avaliar_gate(gate, executar=False)
    assert gate.status == "UNKNOWN"
    assert "ausente" in gate.detail


def test_evidencia_ilegivel_e_unknown_nao_pass(tmp_path):
    caminho = tmp_path / "docs" / "evidence" / "X"
    caminho.mkdir(parents=True)
    (caminho / "quebrado.json").write_text("{ isso nao e json", encoding="utf-8")
    registro = ModuleRegistry(tmp_path, [])
    gate = Gate(id="G", label="G", rule="r", command="c",
                evidence="docs/evidence/X/quebrado.json")
    registro._avaliar_gate(gate, executar=False)
    assert gate.status == "UNKNOWN"


def test_evidencia_com_status_invalido_vira_unknown(tmp_path):
    """Um arquivo dizendo `status: "otimo"` não pode aprovar nada."""
    caminho = tmp_path / "docs" / "evidence" / "X"
    caminho.mkdir(parents=True)
    (caminho / "e.json").write_text(json.dumps({"status": "otimo"}), encoding="utf-8")
    registro = ModuleRegistry(tmp_path, [])
    gate = Gate(id="G", label="G", rule="r", command="c", evidence="docs/evidence/X/e.json")
    registro._avaliar_gate(gate, executar=False)
    assert gate.status == "UNKNOWN"


def test_gravar_evidencia_recusa_modulo_desconhecido(tmp_path):
    registro = ModuleRegistry(tmp_path, [])
    with pytest.raises(ValueError, match="módulo desconhecido"):
        registro.gravar_evidencia("M-INEXISTENTE", "GATE-TEST", "PASS", "x")


def test_gravar_evidencia_recusa_gate_desconhecido(tmp_path):
    registro = ModuleRegistry(tmp_path, [])
    with pytest.raises(ValueError, match="gate desconhecido"):
        registro.gravar_evidencia(MODULOS[0].id, "GATE-INEXISTENTE", "PASS", "x")


def test_relatorio_marca_fase_completa_apenas_com_todos_concluidos(tmp_path):
    registro = ModuleRegistry(tmp_path, [])
    relatorio = registro.relatorio()   # sem evidência no tmp_path: nada concluído
    assert relatorio["concluidos"] == 0
    assert all(not fase["completa"] for fase in relatorio["fases"].values())
