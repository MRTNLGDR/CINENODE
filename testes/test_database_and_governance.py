from __future__ import annotations


def test_database_initialized_and_integrity(app, client):
    assert app.state.db.scalar("PRAGMA integrity_check") == "ok"
    versions = app.state.db.query("SELECT version FROM schema_migrations ORDER BY version")
    # Lista fixa quebra a cada migration nova e não protege nada. O que importa é
    # que as versões sejam contínuas, únicas e crescentes — isso sim é invariante.
    aplicadas = [item["version"] for item in versions]
    assert aplicadas == sorted(aplicadas), "migrations fora de ordem"
    assert len(aplicadas) == len(set(aplicadas)), f"versão duplicada: {aplicadas}"
    assert aplicadas == list(range(1, len(aplicadas) + 1)), f"buraco na sequência: {aplicadas}"
    assert client.get("/api/health").json()["status"] == "ok"


def test_governance_contract_is_real_and_complete(client):
    response = client.get("/api/governance/snapshot")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    # As três últimas entraram com a sessão GOVERNANÇA: decisão técnica, componente
    # open source e histórico de auditoria eram produzidos e não guardados em lugar
    # nenhum. O contrato exato é conferido em tests/test_governanca_sessao.py.
    assert set(payload) == {"generatedAt", "state", "summary", "modules", "tasks",
                            "alerts", "changelog", "logs", "documents",
                            "decisions", "opensource", "audits"}
    assert payload["state"] in {"READY", "DEGRADED", "EMPTY"}
    assert payload["summary"]["totalTasks"] == len(payload["tasks"])
    assert payload["summary"]["doneTasks"] + payload["summary"]["pendingTasks"] == payload["summary"]["totalTasks"]
    assert any(item["id"] == "GOV-001" for item in payload["tasks"])


def test_governance_task_update_persists(client):
    before = client.get("/api/governance/snapshot").json()
    task = next(item for item in before["tasks"] if item["id"] == "MODEL-001")
    response = client.patch("/api/governance/tasks/MODEL-001", json={"status": "DONE", "evidence": {"test": True}})
    assert response.status_code == 200
    after = response.json()
    updated = next(item for item in after["tasks"] if item["id"] == "MODEL-001")
    assert updated["status"] == "DONE"
    again = client.get("/api/governance/snapshot").json()
    assert next(item for item in again["tasks"] if item["id"] == "MODEL-001")["status"] == "DONE"
