from __future__ import annotations

from collections import defaultdict
from typing import Any

from .database import Database
from .util import utc_now


SEED_TASKS: list[dict[str, Any]] = [
    {"id": "OSS-001", "module_id": "OSS", "module_title": "Open source e licenças", "category": "LEGAL", "title": "Auditar repositórios base, licenças e commits", "source_path": "docs/OPEN_SOURCE_INTEGRATION.md", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "OSS-SUPPLY-CHAIN-001", "module_id": "OSS", "module_title": "Open source e licenças", "category": "SECURITY", "title": "Quarentena, varredura de Unicode invisível e promoção atômica de upstreams", "source_path": "scripts/audit_upstream.py", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "ARCH-001", "module_id": "ARCH", "module_title": "Arquitetura", "category": "ARCHITECTURE", "title": "Definir arquitetura local e responsabilidades dos componentes", "source_path": "docs/ARCHITECTURE.md", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "DB-001", "module_id": "CORE", "module_title": "Núcleo e persistência", "category": "BACKEND", "title": "SQLite, migrations, WAL, CRUD e recuperação", "source_path": "source/backend/cinenode/database.py", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "DAG-001", "module_id": "CORE", "module_title": "Núcleo e persistência", "category": "ENGINE", "title": "Validar e executar DAG nodal com fila persistente", "source_path": "source/backend/cinenode/workflow.py", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "ENG-001", "module_id": "ENGINES", "module_title": "Engines locais", "category": "INTEGRATION", "title": "Adaptadores reais para sd.cpp, WanGP, ComfyUI, Real-ESRGAN, RIFE, FFmpeg, Ollama e OpenCode", "source_path": "source/backend/cinenode/engines", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "UI-001", "module_id": "UI", "module_title": "Editor nodal", "category": "FRONTEND", "title": "Editor nodal, projetos, jobs, galeria, engines e configurações", "source_path": "source/frontend/app.js", "status": "DONE", "priority": "HIGH", "severity": "MEDIUM"},
    {"id": "GOV-001", "module_id": "GOV", "module_title": "Governança", "category": "GOVERNANCE", "title": "Snapshot único, polling, SSE, tarefas, alertas, logs e changelog", "source_path": "source/backend/cinenode/governance.py", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "SECURITY-001", "module_id": "SECURITY", "module_title": "Segurança local", "category": "SECURITY", "title": "Host/origin/token, upload, path containment, ZIP restore e subprocessos seguros", "source_path": "docs/SECURITY.md", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "TEST-CORE-001", "module_id": "TEST", "module_title": "Testes automatizados", "category": "TEST", "title": "Executar testes unitários, integração, mídia, segurança e recuperação", "source_path": "TEST_REPORT.md", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "E2E-001", "module_id": "TEST", "module_title": "Testes automatizados", "category": "E2E", "title": "Validar navegador real, persistência, governança e responsividade", "source_path": "docs/screenshots/browser-e2e-report.json", "status": "DONE", "priority": "HIGH", "severity": "MEDIUM"},
    {"id": "WHEEL-001", "module_id": "PACKAGING", "module_title": "Instalação e pacote", "category": "PACKAGING", "title": "Construir e instalar wheel Python do backend", "source_path": "installers/python", "status": "DONE", "priority": "HIGH", "severity": "MEDIUM"},
    {"id": "INSTALL-001", "module_id": "PACKAGING", "module_title": "Instalação e pacote", "category": "INSTALLATION", "title": "Validar instalação de um clique com wheel e fallback automático de dependências", "source_path": "scripts/install.sh", "status": "DONE", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "PKG-001", "module_id": "PACKAGING", "module_title": "Instalação e pacote", "category": "PACKAGING", "title": "Scripts Windows/macOS/Linux, Docker, ZIP e checksum", "source_path": "scripts", "status": "DONE", "priority": "HIGH", "severity": "MEDIUM"},
    {"id": "OSS-SYNC-001", "module_id": "OSS", "module_title": "Open source e licenças", "category": "OPERATIONS", "title": "Materializar backups upstream pinados, audits, lock e checksums no ambiente com rede", "source_path": "Avangard One/opensources", "status": "PENDING", "priority": "HIGH", "severity": "MEDIUM"},
    {"id": "MODEL-001", "module_id": "MODELS", "module_title": "Modelos locais", "category": "OPERATIONS", "title": "Baixar e validar pelo menos um perfil de imagem e um de vídeo no Alienware", "source_path": "docs/MODEL_MATRIX.md", "status": "PENDING", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "GPU-TEST-001", "module_id": "TEST", "module_title": "Validação no hardware-alvo", "category": "TEST", "title": "Executar geração real e benchmark na RTX 4090 24 GB", "source_path": "docs/VALIDATION.md", "status": "PENDING", "priority": "CRITICAL", "severity": "HIGH"},
    {"id": "TAURI-BUILD-001", "module_id": "PACKAGING", "module_title": "Instalação e pacote", "category": "PACKAGING", "title": "Compilar, testar e assinar o instalador Tauri no Windows", "source_path": "source/desktop/src-tauri", "status": "PENDING", "priority": "HIGH", "severity": "MEDIUM"},
]

SEED_ALERTS: list[dict[str, Any]] = [
    {"id": "OSS-GAP-001", "severity": "HIGH", "status": "RESOLVED", "kind": "DEPENDENCY", "module_id": "OSS", "fact": "Os três repositórios solicitados são complementares, não um motor local completo.", "action": "Resolvido pela separação de responsabilidades e integração de sd.cpp, FFmpeg, Real-ESRGAN, RIFE, Ollama e sidecars opcionais."},
    {"id": "OSS-SUPPLY-CHAIN-001", "severity": "HIGH", "status": "RESOLVED", "kind": "SECURITY", "module_id": "OSS", "fact": "Clones upstream podem carregar código oculto ou scripts de instalação perigosos.", "action": "Clone em quarentena, commit pinado, auditoria estática, relatório, checksum e promoção atômica antes de uso."},
    {"id": "INSTALL-GAP-001", "severity": "HIGH", "status": "RESOLVED", "kind": "INSTALLATION", "module_id": "PACKAGING", "fact": "O instalador dependia de atualização de setuptools e de um índice capaz de fornecer todo o runtime.", "action": "O instalador agora prefere o wheel, evita upgrades desnecessários e usa fallback automático validado para pacotes compatíveis do Python hospedeiro quando o índice está indisponível."},
    {"id": "OSS-SYNC-BLOCK-001", "severity": "MEDIUM", "status": "OPEN", "kind": "ENVIRONMENT", "module_id": "OSS", "fact": "O executor de entrega não possui DNS externo para materializar os clones completos no acervo.", "action": "Executar bootstrap-opensources no Alienware; o processo falha fechado e produz manifest.lock, audits e checksums."},
    {"id": "BUILD-GAP-001", "severity": "HIGH", "status": "OPEN", "kind": "ENVIRONMENT", "module_id": "PACKAGING", "fact": "O executor não possui Rust/Cargo, Windows, certificado de assinatura nem RTX 4090.", "action": "Executar scripts/build-tauri.ps1 -Clean e os gates de GPU no Alienware; não considerar o instalador nativo aprovado antes disso."},
    {"id": "LICENSE-GAP-001", "severity": "HIGH", "status": "OPEN", "kind": "LICENSE", "module_id": "OSS", "fact": "WanGP usa WanGP Community License 2.0, com restrições de incorporação, white-label e monetização.", "action": "Manter WanGP externo, opcional, não redistribuído e exigir aceite explícito."},
    {"id": "MODEL-GAP-001", "severity": "HIGH", "status": "OPEN", "kind": "MODEL", "module_id": "MODELS", "fact": "Pesos multi-GB não foram baixados nem executados neste ambiente.", "action": "Baixar pelos bundles com SHA-256, aceitar licenças aplicáveis e validar geração no hardware-alvo."},
    {"id": "GPU-GAP-001", "severity": "HIGH", "status": "OPEN", "kind": "PERFORMANCE", "module_id": "TEST", "fact": "Tempo, VRAM, temperatura e estabilidade CUDA não foram medidos na RTX 4090 Laptop 24 GB.", "action": "Executar benchmark documentado de imagem, vídeo, upscale e exportação no Alienware."},
]

SEVERIDADES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
ESTADOS_DECISAO = ("PROPOSTA", "ACEITA", "SUBSTITUIDA", "REJEITADA")
RESULTADOS_AUDITORIA = ("APROVADA", "REPROVADA", "BLOQUEADA")

SEED_DOCUMENTS = [
    ("README", "/docs/README.md"),
    ("Quickstart", "/docs/QUICKSTART.md"),
    ("API", "/docs/API.md"),
    ("Arquitetura", "/docs/ARCHITECTURE.md"),
    ("Matriz de modelos", "/docs/MODEL_MATRIX.md"),
    ("Integração open source", "/docs/OPEN_SOURCE_INTEGRATION.md"),
    ("Segurança", "/docs/SECURITY.md"),
    ("Recuperação", "/docs/RECOVERY.md"),
    ("Validação", "/docs/VALIDATION.md"),
    ("Relatório de testes", "/docs/TEST_REPORT.md"),
    ("Auditoria final", "/docs/AUDIT_REPORT.md"),
]


def seed_governance(db: Database) -> None:
    now = utc_now()
    with db.transaction() as connection:
        for task in SEED_TASKS:
            connection.execute(
                "INSERT INTO governance_tasks(id,module_id,module_title,category,title,source_path,source_line,status,priority,severity,evidence_json,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                "module_id=excluded.module_id,module_title=excluded.module_title,category=excluded.category,title=excluded.title," 
                "source_path=excluded.source_path,priority=excluded.priority,severity=excluded.severity",
                (
                    task["id"], task["module_id"], task["module_title"], task["category"], task["title"],
                    task["source_path"], 1, task["status"], task["priority"], task["severity"], "[]", now,
                ),
            )
        for alert in SEED_ALERTS:
            connection.execute(
                "INSERT INTO governance_alerts(id,severity,status,kind,fact,action,module_id,evidence_json,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET severity=excluded.severity,kind=excluded.kind,fact=excluded.fact,action=excluded.action,module_id=excluded.module_id",
                (alert["id"], alert["severity"], alert["status"], alert["kind"], alert["fact"], alert["action"], alert["module_id"], "[]", now, now),
            )
        for name, link in SEED_DOCUMENTS:
            connection.execute(
                "INSERT INTO governance_documents(name,link,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET link=excluded.link,updated_at=excluded.updated_at",
                (name, link, now),
            )
        exists = connection.execute("SELECT COUNT(*) FROM governance_changes").fetchone()[0]
        if not exists:
            connection.execute(
                "INSERT INTO governance_changes(release,category,description,source_line,created_at) VALUES(?,?,?,?,?)",
                ("0.1.0", "Added", "Núcleo local, editor nodal, engines, governança e empacotamento inicial.", 1, now),
            )


def log_governance(db: Database, level: str, event: str, detail: Any) -> None:
    db.execute(
        "INSERT INTO governance_logs(created_at,level,event,detail_json) VALUES(?,?,?,?)",
        (utc_now(), level, event, db.dump_json(detail)),
    )


def update_task(db: Database, task_id: str, status: str, evidence: Any | None = None) -> bool:
    row = db.query_one("SELECT evidence_json FROM governance_tasks WHERE id=?", (task_id,))
    if not row:
        return False
    items = db.load_json(row["evidence_json"], [])
    if evidence is not None:
        items.append({"at": utc_now(), "detail": evidence})
    db.execute(
        "UPDATE governance_tasks SET status=?, evidence_json=?, updated_at=? WHERE id=?",
        (status, db.dump_json(items), utc_now(), task_id),
    )
    log_governance(db, "INFO", "governance.task.updated", {"task_id": task_id, "status": status})
    return True


def set_alert_status(db: Database, alert_id: str, status: str, evidence: Any | None = None) -> bool:
    row = db.query_one("SELECT evidence_json FROM governance_alerts WHERE id=?", (alert_id,))
    if not row:
        return False
    items = db.load_json(row["evidence_json"], [])
    if evidence is not None:
        items.append({"at": utc_now(), "detail": evidence})
    db.execute(
        "UPDATE governance_alerts SET status=?, evidence_json=?, updated_at=? WHERE id=?",
        (status, db.dump_json(items), utc_now(), alert_id),
    )
    return True


def registrar_alerta(db: Database, alert_id: str, *, severity: str, kind: str,
                     fact: str, action: str, module_id: str = "", origem: str = "",
                     causa: str = "", impacto: str = "", task_id: str = "",
                     arquivos: list[str] | None = None, teste: str = "") -> dict[str, Any]:
    """Registra ou atualiza um alerta com identidade permanente.

    O id é a chave: reexecutar a mesma auditoria atualiza o alerta existente em vez
    de criar um duplicado. Sem isso, um painel de alertas cresce a cada rodada e
    deixa de ser lido justamente por ser grande demais.

    Um alerta reaberto volta a `OPEN` e mantém a evidência anterior — a história de
    ter sido resolvido antes é informação, não ruído.
    """
    if severity not in SEVERIDADES:
        raise ValueError(f"severidade inválida: {severity}")
    agora = utc_now()
    existente = db.query_one("SELECT status,evidence_json FROM governance_alerts WHERE id=?",
                             (alert_id,))
    campos = (severity, kind, fact, action, module_id, origem, causa, impacto,
              task_id, db.dump_json(arquivos or []), teste, agora)

    if existente:
        db.execute(
            "UPDATE governance_alerts SET severity=?,kind=?,fact=?,action=?,module_id=?,"
            "origem=?,causa=?,impacto=?,task_id=?,arquivos_json=?,teste=?,updated_at=?,"
            "status='OPEN' WHERE id=?",
            (*campos, alert_id),
        )
        reaberto = existente["status"] == "RESOLVED"
    else:
        db.execute(
            "INSERT INTO governance_alerts(id,severity,status,kind,fact,action,module_id,"
            "origem,causa,impacto,task_id,arquivos_json,teste,created_at,updated_at,"
            "evidence_json) VALUES(?,?,'OPEN',?,?,?,?,?,?,?,?,?,?,?,?,'[]')",
            (alert_id, severity, kind, fact, action, module_id, origem, causa, impacto,
             task_id, db.dump_json(arquivos or []), teste, agora, agora),
        )
        reaberto = False

    log_governance(db, "WARN" if severity in {"HIGH", "CRITICAL"} else "INFO",
                   "governance.alert.registered",
                   {"alert_id": alert_id, "severity": severity, "reaberto": reaberto})
    return {"id": alert_id, "reaberto": reaberto, "criado": not existente}


def registrar_decisao(db: Database, decisao_id: str, *, titulo: str, estado: str,
                      contexto: str, decisao: str, consequencias: str = "",
                      modulos: list[str] | None = None,
                      documento: str = "") -> dict[str, Any]:
    """Decisão técnica no banco, não só num markdown que ninguém abre.

    O painel precisa responder "por que a arquitetura é assim" sem que alguém
    tenha de saber que existe uma pasta `docs/adr`.
    """
    if estado not in ESTADOS_DECISAO:
        raise ValueError(f"estado de decisão inválido: {estado}")
    agora = utc_now()
    existe = db.query_one("SELECT id FROM governance_decisions WHERE id=?", (decisao_id,))
    if existe:
        db.execute(
            "UPDATE governance_decisions SET titulo=?,estado=?,contexto=?,decisao=?,"
            "consequencias=?,modulos_json=?,documento=?,updated_at=? WHERE id=?",
            (titulo, estado, contexto, decisao, consequencias,
             db.dump_json(modulos or []), documento, agora, decisao_id),
        )
    else:
        db.execute(
            "INSERT INTO governance_decisions(id,titulo,estado,contexto,decisao,"
            "consequencias,modulos_json,documento,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (decisao_id, titulo, estado, contexto, decisao, consequencias,
             db.dump_json(modulos or []), documento, agora, agora),
        )
    log_governance(db, "INFO", "governance.decision.registered",
                   {"decisao_id": decisao_id, "estado": estado})
    return {"id": decisao_id, "criada": not existe}


def registrar_opensource(db: Database, componente_id: str, *, nome: str, origem: str,
                         licenca: str, versao: str = "", spdx: str = "",
                         uso_comercial: str = "UNKNOWN", integracao: str = "",
                         redistribuido: bool = False, conferido: bool = False,
                         observacao: str = "") -> dict[str, Any]:
    """Componente de terceiro com origem e licença rastreáveis.

    `redistribuido` é o campo que muda o risco: usar GPL como processo separado é
    uma coisa, embutir no pacote é outra completamente diferente.
    """
    agora = utc_now()
    existe = db.query_one("SELECT id FROM governance_opensource WHERE id=?", (componente_id,))
    valores = (nome, origem, versao, licenca, spdx, uso_comercial, integracao,
               int(redistribuido), int(conferido), observacao, agora)
    if existe:
        db.execute(
            "UPDATE governance_opensource SET nome=?,origem=?,versao=?,licenca=?,spdx=?,"
            "uso_comercial=?,integracao=?,redistribuido=?,conferido=?,observacao=?,"
            "updated_at=? WHERE id=?", (*valores, componente_id))
    else:
        db.execute(
            "INSERT INTO governance_opensource(nome,origem,versao,licenca,spdx,"
            "uso_comercial,integracao,redistribuido,conferido,observacao,updated_at,id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (*valores, componente_id))
    return {"id": componente_id, "criado": not existe}


def registrar_auditoria(db: Database, *, sessao: str, resultado: str, escopo: str = "",
                        itens_auditados: int = 0, falhas_encontradas: int = 0,
                        falhas_corrigidas: int = 0, testes_total: int = 0,
                        testes_verdes: int = 0,
                        evidencia: Any | None = None) -> dict[str, Any]:
    """Grava o resultado de uma auditoria.

    Uma auditoria cujo resultado não fica registrado precisa ser refeita do zero na
    próxima sessão, e a comparação entre rodadas — que é o que mostra regressão —
    fica impossível.
    """
    if resultado not in RESULTADOS_AUDITORIA:
        raise ValueError(f"resultado de auditoria inválido: {resultado}")
    db.execute(
        "INSERT INTO governance_audits(executado_em,sessao,escopo,itens_auditados,"
        "falhas_encontradas,falhas_corrigidas,testes_total,testes_verdes,resultado,"
        "evidencia_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (utc_now(), sessao, escopo, itens_auditados, falhas_encontradas,
         falhas_corrigidas, testes_total, testes_verdes, resultado,
         db.dump_json(evidencia or {})),
    )
    log_governance(db, "INFO" if resultado == "APROVADA" else "WARN",
                   "governance.audit.recorded",
                   {"sessao": sessao, "resultado": resultado,
                    "falhas": falhas_encontradas})
    return {"sessao": sessao, "resultado": resultado}


def read_governance_snapshot(db: Database) -> dict[str, Any]:
    tasks = db.query(
        "SELECT id,category,title,source_path,source_line,status,module_id,module_title,"
        "priority,severity,milestone,depende_de,camada FROM governance_tasks "
        "ORDER BY status DESC, priority DESC, id"
    )
    alerts = db.query(
        "SELECT id,severity,status,kind,fact,action,module_id,origem,causa,impacto,"
        "task_id,arquivos_json,teste,resultado,created_at,updated_at "
        "FROM governance_alerts ORDER BY CASE severity WHEN 'CRITICAL' THEN 4 WHEN 'HIGH' THEN 3 WHEN 'MEDIUM' THEN 2 ELSE 1 END DESC, updated_at DESC"
    )
    changes = db.query(
        "SELECT release,category,description,source_line FROM governance_changes ORDER BY id DESC LIMIT 100"
    )
    log_rows = db.query(
        "SELECT created_at,level,event,detail_json FROM governance_logs ORDER BY id DESC LIMIT 200"
    )
    documents = db.query("SELECT name,link,updated_at FROM governance_documents ORDER BY name")
    decisoes = db.query(
        "SELECT id,titulo,estado,contexto,decisao,consequencias,modulos_json,documento,"
        "updated_at FROM governance_decisions ORDER BY id"
    )
    for item in decisoes:
        item["modulos"] = db.load_json(item.pop("modulos_json"), [])
    opensource = db.query(
        "SELECT id,nome,origem,versao,licenca,spdx,uso_comercial,integracao,"
        "redistribuido,conferido,observacao,updated_at FROM governance_opensource "
        "ORDER BY nome"
    )
    for item in opensource:
        item["redistribuido"] = bool(item["redistribuido"])
        item["conferido"] = bool(item["conferido"])
    auditorias = db.query(
        "SELECT executado_em,sessao,escopo,itens_auditados,falhas_encontradas,"
        "falhas_corrigidas,testes_total,testes_verdes,resultado,evidencia_json "
        "FROM governance_audits ORDER BY id DESC LIMIT 50"
    )
    for item in auditorias:
        item["evidencia"] = db.load_json(item.pop("evidencia_json"), {})

    for alerta in alerts:
        alerta["arquivos"] = db.load_json(alerta.pop("arquivos_json"), [])

    grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"done": 0, "total": 0})
    for task in tasks:
        key = (task.pop("module_id"), task.pop("module_title"))
        grouped[key]["total"] += 1
        grouped[key]["done"] += int(task["status"] == "DONE")

    modules = [
        {"module_id": key[0], "module_title": key[1], "done": value["done"], "total": value["total"]}
        for key, value in sorted(grouped.items())
    ]
    total = len(tasks)
    done = sum(1 for task in tasks if task["status"] == "DONE")
    pending = total - done
    open_alerts = sum(1 for alert in alerts if alert["status"] == "OPEN")
    critical_or_high = any(
        alert["status"] == "OPEN" and alert["severity"] in {"CRITICAL", "HIGH"}
        for alert in alerts
    )
    state = "EMPTY" if total == 0 else ("DEGRADED" if critical_or_high else "READY")
    logs = [
        {"created_at": row["created_at"], "level": row["level"], "event": row["event"], "detail": db.load_json(row["detail_json"], {})}
        for row in log_rows
    ]
    return {
        "generatedAt": utc_now(),
        "state": state,
        "summary": {
            "totalTasks": total,
            "doneTasks": done,
            "pendingTasks": pending,
            "openAlerts": open_alerts,
            "documents": len(documents),
            "progressPercent": round((done / total * 100.0) if total else 0.0, 2),
            "decisions": len(decisoes),
            "opensource": len(opensource),
            # Componente sem licença permissiva conferida é risco não declarado;
            # ele aparece como número no resumo em vez de ficar escondido na lista.
            "opensourcePendentes": sum(
                1 for item in opensource if not item["conferido"]),
            "audits": len(auditorias),
            "lastAudit": auditorias[0]["resultado"] if auditorias else None,
        },
        "modules": modules,
        "tasks": tasks,
        "alerts": alerts,
        "changelog": changes,
        "logs": logs,
        "documents": documents,
        "decisions": decisoes,
        "opensource": opensource,
        "audits": auditorias,
    }
