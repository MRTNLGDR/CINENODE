"""Sessão GOVERNANÇA de ponta a ponta: banco, domínio, rotas, contrato e tela.

O snapshot já era a fonte única de leitura. O que faltava era tudo o resto: o
caminho de volta (um alerta que ninguém fecha pela UI vira ruído permanente), as
superfícies que a governança prometia e não guardava (decisões, open source,
histórico de auditoria), e os estados de interface — a tela girava o mesmo spinner
tanto para "carregando" quanto para "a ponte caiu".
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cinenode.api import create_app
from cinenode.database import Database
from cinenode.governance import (
    ESTADOS_DECISAO,
    RESULTADOS_AUDITORIA,
    SEVERIDADES,
    read_governance_snapshot,
    registrar_alerta,
    registrar_auditoria,
    registrar_decisao,
    registrar_opensource,
    seed_governance,
    set_alert_status,
)

APP_JS = Path(__file__).resolve().parents[1] / "source" / "backend" / "cinenode" / "frontend" / "app.js"


@pytest.fixture()
def db(config) -> Database:
    banco = Database(config.database)
    banco.initialize()
    seed_governance(banco)
    return banco


# ---- banco: a migração precisa ter deixado as superfícies ------------------

def test_migracao_criou_as_tabelas_de_governanca(db):
    with db.connection() as conexao:
        tabelas = {row[0] for row in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'governance%'")}
    assert {"governance_decisions", "governance_opensource", "governance_audits"} <= tabelas


def test_migracao_adicionou_as_colunas_de_rastreio(db):
    """Um alerta precisa dizer de onde veio, o que causa e qual tarefa o resolve.
    Sem isso ele é um aviso solto que ninguém sabe como fechar."""
    with db.connection() as conexao:
        alertas = {row[1] for row in conexao.execute("PRAGMA table_info(governance_alerts)")}
        tarefas = {row[1] for row in conexao.execute("PRAGMA table_info(governance_tasks)")}
    assert {"origem", "causa", "impacto", "task_id", "arquivos_json", "teste", "resultado"} <= alertas
    assert {"milestone", "depende_de", "camada"} <= tarefas


def test_migracao_e_reexecutavel(config):
    """`initialize` roda a cada boot. Se não fosse idempotente, o segundo start
    do app derrubaria o banco."""
    primeiro = Database(config.database)
    primeiro.initialize()
    segundo = Database(config.database)
    segundo.initialize()
    with segundo.connection() as conexao:
        assert conexao.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] >= 5


# ---- domínio ---------------------------------------------------------------

def test_alerta_com_mesmo_id_atualiza_em_vez_de_duplicar(db):
    """Reexecutar a auditoria não pode inflar o painel. Um painel de alertas que
    cresce a cada rodada deixa de ser lido justamente por ser grande demais."""
    for tentativa in range(3):
        registrar_alerta(db, "GOV-DUP", severity="HIGH", kind="gap",
                         fact=f"medida {tentativa}", action="corrigir")
    linhas = db.query("SELECT fact FROM governance_alerts WHERE id='GOV-DUP'")
    assert len(linhas) == 1
    assert linhas[0]["fact"] == "medida 2"


def test_alerta_resolvido_e_reaberto_quando_a_falha_volta(db):
    registrar_alerta(db, "GOV-VOLTA", severity="MEDIUM", kind="gap", fact="f", action="a")
    set_alert_status(db, "GOV-VOLTA", "RESOLVED", {"nota": "corrigido"})
    assert db.query_one("SELECT status FROM governance_alerts WHERE id='GOV-VOLTA'")["status"] == "RESOLVED"

    resultado = registrar_alerta(db, "GOV-VOLTA", severity="HIGH", kind="gap",
                                 fact="voltou", action="a")
    assert resultado["reaberto"] is True
    assert db.query_one("SELECT status FROM governance_alerts WHERE id='GOV-VOLTA'")["status"] == "OPEN"


def test_alerta_reaberto_preserva_a_evidencia_anterior(db):
    """Ter sido resolvido antes é informação, não ruído."""
    registrar_alerta(db, "GOV-HIST", severity="LOW", kind="gap", fact="f", action="a")
    set_alert_status(db, "GOV-HIST", "RESOLVED", {"nota": "primeira correção"})
    registrar_alerta(db, "GOV-HIST", severity="LOW", kind="gap", fact="f2", action="a")

    evidencia = db.load_json(
        db.query_one("SELECT evidence_json FROM governance_alerts WHERE id='GOV-HIST'")["evidence_json"], [])
    assert any(item["detail"] == {"nota": "primeira correção"} for item in evidencia)


@pytest.mark.parametrize("severidade", SEVERIDADES)
def test_toda_severidade_do_vocabulario_e_aceita(db, severidade):
    registrar_alerta(db, f"GOV-{severidade}", severity=severidade, kind="k", fact="f", action="a")
    assert db.query_one("SELECT severity FROM governance_alerts WHERE id=?",
                        (f"GOV-{severidade}",))["severity"] == severidade


def test_severidade_inventada_e_recusada(db):
    """Valor fora do vocabulário fechado é lacuna, não classificação."""
    with pytest.raises(ValueError, match="severidade inválida"):
        registrar_alerta(db, "GOV-X", severity="URGENTISSIMO", kind="k", fact="f", action="a")


@pytest.mark.parametrize("estado", ESTADOS_DECISAO)
def test_todo_estado_de_decisao_e_aceito(db, estado):
    registrar_decisao(db, f"ADR-{estado}", titulo="t", estado=estado, contexto="c", decisao="d")
    assert db.query_one("SELECT estado FROM governance_decisions WHERE id=?",
                        (f"ADR-{estado}",))["estado"] == estado


def test_estado_de_decisao_invalido_e_recusado(db):
    with pytest.raises(ValueError, match="estado de decisão inválido"):
        registrar_decisao(db, "ADR-X", titulo="t", estado="TALVEZ", contexto="c", decisao="d")


def test_decisao_com_mesmo_id_atualiza(db):
    registrar_decisao(db, "ADR-008", titulo="antes", estado="PROPOSTA", contexto="c", decisao="d")
    registrar_decisao(db, "ADR-008", titulo="depois", estado="ACEITA", contexto="c", decisao="d")
    linhas = db.query("SELECT titulo,estado FROM governance_decisions WHERE id='ADR-008'")
    assert len(linhas) == 1
    assert linhas[0] == {"titulo": "depois", "estado": "ACEITA"}


@pytest.mark.parametrize("resultado", RESULTADOS_AUDITORIA)
def test_todo_resultado_de_auditoria_e_aceito(db, resultado):
    registrar_auditoria(db, sessao="S", resultado=resultado)
    assert db.query("SELECT resultado FROM governance_audits WHERE resultado=?",
                    (resultado,))


def test_resultado_de_auditoria_invalido_e_recusado(db):
    with pytest.raises(ValueError, match="resultado de auditoria inválido"):
        registrar_auditoria(db, sessao="S", resultado="MAIS_OU_MENOS")


def test_auditoria_acumula_historico_em_vez_de_sobrescrever(db):
    """Sem histórico, cada rodada recomeça do zero e regressão nenhuma é detectável."""
    registrar_auditoria(db, sessao="GOVERNANCA", resultado="REPROVADA", falhas_encontradas=10)
    registrar_auditoria(db, sessao="GOVERNANCA", resultado="APROVADA", falhas_corrigidas=10)
    historico = read_governance_snapshot(db)["audits"]
    assert len(historico) == 2
    assert historico[0]["resultado"] == "APROVADA", "o mais recente vem primeiro"


def test_componente_open_source_distingue_redistribuido(db):
    """Usar GPL como processo separado é uma coisa; embutir no pacote é outra
    completamente diferente, e o campo é o que separa as duas."""
    registrar_opensource(db, "comfyui", nome="ComfyUI", origem="https://github.com/comfyanonymous/ComfyUI",
                         licenca="OSS_CODE", spdx="GPL-3.0", redistribuido=False, conferido=True)
    item = read_governance_snapshot(db)["opensource"][0]
    assert item["redistribuido"] is False
    assert item["conferido"] is True


# ---- contrato do snapshot --------------------------------------------------

def test_snapshot_tem_exatamente_as_chaves_do_contrato(db):
    """O frontend lê estas chaves por nome. Renomear uma quebra a tela em silêncio."""
    snapshot = read_governance_snapshot(db)
    assert set(snapshot) == {
        "generatedAt", "state", "summary", "modules", "tasks", "alerts",
        "changelog", "logs", "documents", "decisions", "opensource", "audits"}


def test_resumo_tem_os_campos_que_a_tela_exibe(db):
    resumo = read_governance_snapshot(db)["summary"]
    assert set(resumo) >= {
        "totalTasks", "doneTasks", "pendingTasks", "openAlerts", "documents",
        "progressPercent", "decisions", "opensource", "opensourcePendentes",
        "audits", "lastAudit"}


def test_progresso_e_coerente_com_as_contagens(db):
    resumo = read_governance_snapshot(db)["summary"]
    assert resumo["doneTasks"] + resumo["pendingTasks"] == resumo["totalTasks"]
    esperado = resumo["doneTasks"] / resumo["totalTasks"] * 100
    assert resumo["progressPercent"] == pytest.approx(esperado, abs=0.01)


def test_estado_degradado_quando_ha_alerta_alto_aberto(db):
    registrar_alerta(db, "GOV-CRIT", severity="CRITICAL", kind="k", fact="f", action="a")
    assert read_governance_snapshot(db)["state"] == "DEGRADED"


def test_estado_vazio_quando_nao_ha_tarefa(config):
    """EMPTY e DEGRADED pedem ações diferentes; colapsar os dois num estado só
    esconderia a diferença entre 'sem dados' e 'com problema'."""
    banco = Database(config.database)
    banco.initialize()
    assert read_governance_snapshot(banco)["state"] == "EMPTY"


def test_alerta_do_snapshot_traz_a_rastreabilidade(db):
    registrar_alerta(db, "GOV-RASTRO", severity="HIGH", kind="LICENSE", fact="f",
                     action="a", origem="auditoria", causa="c", impacto="i",
                     task_id="MODEL-002", arquivos=["a.py", "b.py"], teste="tests/x.py")
    alerta = next(a for a in read_governance_snapshot(db)["alerts"] if a["id"] == "GOV-RASTRO")
    assert alerta["origem"] == "auditoria"
    assert alerta["task_id"] == "MODEL-002"
    assert alerta["arquivos"] == ["a.py", "b.py"]
    assert alerta["teste"] == "tests/x.py"


# ---- rotas -----------------------------------------------------------------

def test_snapshot_nunca_e_servido_de_cache(config):
    """Um painel de governança que exibe número velho como se fosse atual é pior
    do que um painel vazio."""
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.get("/api/governance/snapshot")
        assert resposta.status_code == 200
        assert resposta.headers.get("Cache-Control") == "no-store"


def test_alerta_pode_ser_resolvido_pela_rota(config):
    """`set_alert_status` existia sem rota nenhuma — código morto desde sempre."""
    app = create_app(config)
    with TestClient(app) as client:
        registrar_alerta(app.state.db, "GOV-UI", severity="HIGH", kind="k",
                         fact="f", action="a")
        resposta = client.patch("/api/governance/alerts/GOV-UI",
                                json={"status": "RESOLVED", "resultado": "fechado"})
        assert resposta.status_code == 200
        alerta = next(a for a in resposta.json()["alerts"] if a["id"] == "GOV-UI")
        assert alerta["status"] == "RESOLVED"
        assert alerta["resultado"] == "fechado"


def test_alerta_inexistente_devolve_404_com_codigo(config):
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.patch("/api/governance/alerts/NAO_EXISTE", json={"status": "RESOLVED"})
        assert resposta.status_code == 404
        assert resposta.json()["detail"]["code"] == "ALERTA_INEXISTENTE"


def test_status_de_alerta_invalido_devolve_422_com_codigo(config):
    app = create_app(config)
    with TestClient(app) as client:
        registrar_alerta(app.state.db, "GOV-S", severity="LOW", kind="k", fact="f", action="a")
        resposta = client.patch("/api/governance/alerts/GOV-S", json={"status": "FECHADO"})
        assert resposta.status_code == 422
        assert resposta.json()["detail"]["code"] == "STATUS_INVALIDO"


def test_criar_alerta_pela_rota_com_severidade_invalida(config):
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.post("/api/governance/alerts", json={
            "id": "X", "severity": "URGENTE", "kind": "k", "fact": "f", "action": "a"})
        assert resposta.status_code == 422
        assert resposta.json()["detail"]["code"] == "SEVERIDADE_INVALIDA"


def test_decisao_e_auditoria_recusam_vocabulario_invalido(config):
    app = create_app(config)
    with TestClient(app) as client:
        decisao = client.post("/api/governance/decisions", json={
            "id": "A", "titulo": "t", "estado": "QUEM_SABE", "contexto": "c", "decisao": "d"})
        assert decisao.status_code == 422
        assert decisao.json()["detail"]["code"] == "ESTADO_INVALIDO"

        auditoria = client.post("/api/governance/audits", json={
            "sessao": "S", "resultado": "TALVEZ"})
        assert auditoria.status_code == 422
        assert auditoria.json()["detail"]["code"] == "RESULTADO_INVALIDO"


def test_sincronizar_registra_componentes_e_abre_alerta_de_licenca(config):
    """Descobrir a lacuna e não registrá-la é como não tê-la descoberto."""
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.post("/api/governance/sincronizar")
        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["componentes"] > 0

        snapshot = corpo["snapshot"]
        assert snapshot["summary"]["opensource"] == corpo["componentes"]
        # Filtra pela origem, não só pelo tipo: a semente já traz LICENSE-GAP-001,
        # e contar os dois juntos compararia a saída da rota com um número que
        # inclui alerta que ela não criou.
        licencas = [a for a in snapshot["alerts"]
                    if a["origem"] == "/api/governance/sincronizar" and a["status"] == "OPEN"]
        assert len(licencas) == corpo["alertas_abertos"]
        for alerta in licencas:
            assert alerta["task_id"] == "MODEL-002"
            assert alerta["origem"] == "/api/governance/sincronizar"


def test_sincronizar_duas_vezes_nao_duplica(config):
    app = create_app(config)
    with TestClient(app) as client:
        primeiro = client.post("/api/governance/sincronizar").json()
        segundo = client.post("/api/governance/sincronizar").json()
        assert primeiro["componentes"] == segundo["componentes"]
        assert segundo["snapshot"]["summary"]["opensource"] == segundo["componentes"]


def test_toda_mutacao_de_governanca_deixa_log(config):
    """Mudança sem log é mudança que ninguém consegue reconstruir depois."""
    app = create_app(config)
    with TestClient(app) as client:
        registrar_alerta(app.state.db, "GOV-LOG", severity="LOW", kind="k", fact="f", action="a")
        client.patch("/api/governance/alerts/GOV-LOG", json={"status": "RESOLVED"})
        client.post("/api/governance/audits", json={"sessao": "S", "resultado": "APROVADA"})

        eventos = {log["event"] for log in client.get("/api/governance/snapshot").json()["logs"]}
        assert "governance.alert.registered" in eventos
        assert "governance.alert.updated" in eventos
        assert "governance.audit.recorded" in eventos


def test_rotas_de_governanca_exigem_requisicao_local(config):
    """A governança expõe caminhos de arquivo e decisões internas; ela não pode
    responder para origem que não seja a própria máquina."""
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.get("/api/governance/snapshot", headers={"Host": "exemplo.com"})
        assert resposta.status_code == 403


# ---- tela ------------------------------------------------------------------

def _app_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_tela_distingue_carregando_erro_e_vazio():
    """Antes, os três estados mostravam o mesmo spinner girando para sempre."""
    fonte = _app_js()
    assert "governanceErroHtml" in fonte
    assert "governanceVaziaHtml" in fonte
    assert "if (state.governanceError) return governanceErroHtml" in fonte
    assert 'if (data.state === "EMPTY") return governanceVaziaHtml' in fonte


def test_erro_da_ponte_vai_para_o_estado_e_nao_so_para_um_toast():
    """Um toast some em três segundos e a tela continuava girando o spinner."""
    fonte = _app_js()
    trecho = fonte[fonte.index("async function refreshGovernance"):]
    trecho = trecho[:trecho.index("\n}")]
    assert "state.governanceError = error.message" in trecho
    assert "state.governanceError = null" in trecho


def test_snapshot_invalido_e_recusado_no_cliente():
    fonte = _app_js()
    assert "!snapshot?.summary || !Array.isArray(snapshot.modules)" in fonte


def test_polling_foco_e_evento_global_estao_ligados():
    fonte = _app_js()
    assert re.search(r"setInterval\(\(\) => refreshGovernance\([^)]*\), 15000\)", fonte)
    assert 'window.addEventListener("focus"' in fonte
    assert 'window.addEventListener("oraculo:governance-updated"' in fonte
    assert 'source.addEventListener("governance.updated"' in fonte


def test_tela_renderiza_as_superficies_novas():
    fonte = _app_js()
    for funcao in ("decisoesHtml", "opensourceHtml", "auditoriasHtml", "alertaHtml"):
        assert f"function {funcao}(" in fonte, funcao
        # `alertaHtml` é passado por referência em `.map(alertaHtml)`, sem
        # parêntese. Exigir `nome(` daria falso negativo justamente na chamada
        # mais idiomática do arquivo.
        antes = fonte.split(f"function {funcao}(")[0]
        assert funcao in antes, f"{funcao} não é usada em lugar nenhum"


def test_alerta_tem_botao_que_chama_a_rota():
    """Botão sem comportamento é a definição de entrega falsa."""
    fonte = _app_js()
    assert 'data-alert="' in fonte
    assert "resolverAlerta(btn.dataset.alert, btn.dataset.alertStatus)" in fonte
    assert '`/api/governance/alerts/${alertId}`' in fonte


def test_botao_de_sincronizar_existe_e_esta_ligado():
    fonte = _app_js()
    assert "data-action=\"sync-governance\"" in fonte
    assert "sincronizarGovernanca" in fonte
    assert '"/api/governance/sincronizar"' in fonte


def test_governanca_esta_no_menu_e_tem_rota():
    fonte = _app_js()
    assert '["governance", "governance", "Governança"]' in fonte
    assert 'if (state.route === "governance") content = governanceHtml();' in fonte


def test_copia_do_frontend_esta_sincronizada():
    """Duas cópias do app.js divergindo faria o servidor servir uma e o pacote
    empacotar a outra."""
    outra = Path(__file__).resolve().parents[1] / "source" / "frontend" / "app.js"
    assert outra.read_text(encoding="utf-8") == _app_js()
