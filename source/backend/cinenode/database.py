from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence


MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        r"""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            graph_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
            status TEXT NOT NULL CHECK(status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED')),
            progress REAL NOT NULL DEFAULT 0 CHECK(progress >= 0 AND progress <= 100),
            current_node_id TEXT,
            graph_json TEXT NOT NULL,
            result_json TEXT,
            error_code TEXT,
            error_message TEXT,
            cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK(cancel_requested IN (0,1)),
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

        CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY,
            project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
            job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
            kind TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            original_name TEXT,
            mime_type TEXT,
            size_bytes INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_assets_project ON assets(project_id);

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS governance_tasks (
            id TEXT PRIMARY KEY,
            module_id TEXT NOT NULL,
            module_title TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_line INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL CHECK(status IN ('PENDING','DONE')),
            priority TEXT NOT NULL DEFAULT 'MEDIUM',
            severity TEXT NOT NULL DEFAULT 'LOW',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_governance_tasks_module ON governance_tasks(module_id);
        CREATE INDEX IF NOT EXISTS idx_governance_tasks_status ON governance_tasks(status);

        CREATE TABLE IF NOT EXISTS governance_alerts (
            id TEXT PRIMARY KEY,
            severity TEXT NOT NULL CHECK(severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
            status TEXT NOT NULL CHECK(status IN ('OPEN','RESOLVED')),
            kind TEXT NOT NULL,
            fact TEXT NOT NULL,
            action TEXT NOT NULL,
            module_id TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS governance_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            release TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            source_line INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS governance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('INFO','WARN','ERROR')),
            event TEXT NOT NULL,
            detail_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_governance_logs_created ON governance_logs(created_at DESC);

        CREATE TABLE IF NOT EXISTS governance_documents (
            name TEXT PRIMARY KEY,
            link TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            detail_json TEXT NOT NULL DEFAULT '{}'
        );
        """,
    ),
    (
        2,
        r"""
        CREATE TABLE IF NOT EXISTS engine_checks (
            engine_id TEXT PRIMARY KEY,
            available INTEGER NOT NULL CHECK(available IN (0,1)),
            version TEXT,
            detail TEXT NOT NULL,
            checked_at TEXT NOT NULL
        );
        """,
    ),
    (
        3,
        r"""
        -- Versionamento de projeto: cada snapshot guarda o grafo inteiro daquele
        -- instante. Restaurar é copiar o grafo de volta, sem perder o histórico.
        CREATE TABLE IF NOT EXISTS project_snapshots (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            label TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            graph_json TEXT NOT NULL,
            node_count INTEGER NOT NULL DEFAULT 0,
            edge_count INTEGER NOT NULL DEFAULT 0,
            origin TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_snapshots_project ON project_snapshots(project_id, created_at DESC);

        -- Coleções de assets: bibliotecas e referências montadas pelo usuário.
        CREATE TABLE IF NOT EXISTS asset_collections (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'library',
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS asset_collection_items (
            collection_id TEXT NOT NULL REFERENCES asset_collections(id) ON DELETE CASCADE,
            asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
            position INTEGER NOT NULL DEFAULT 0,
            added_at TEXT NOT NULL,
            PRIMARY KEY (collection_id, asset_id)
        );

        -- A coluna assets.deleted_at é adicionada por COLUMN_ADDITIONS, fora do
        -- executescript: ALTER TABLE ADD COLUMN não é idempotente e abortaria a
        -- migração inteira se a coluna já existisse.
        """,
    ),
    (
        4,
        r"""
        -- JOB-001: cache do resultado de cada nó, para que a retomada não refaça o
        -- que já custou GPU. A chave é o hash das entradas: mudar a configuração de
        -- um nó invalida o cache dele sozinho, sem invalidar os outros.
        CREATE TABLE IF NOT EXISTS node_results (
            job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            node_id TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (job_id, node_id, input_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_node_results_job ON node_results(job_id);

        -- O CHECK antigo de `jobs` não conhece INTERRUPTED, e o SQLite não altera
        -- CHECK: a tabela é reconstruída preservando cada linha. `PRAGMA legacy_alter_table`
        -- não é usado — a cópia explícita é auditável e o índice é recriado depois.
        CREATE TABLE IF NOT EXISTS jobs_v3 (
            id TEXT PRIMARY KEY,
            project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
            graph_json TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN
                ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','INTERRUPTED')),
            progress REAL NOT NULL DEFAULT 0,
            current_node_id TEXT,
            error_code TEXT,
            error_message TEXT,
            result_json TEXT,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT
        );
        INSERT OR IGNORE INTO jobs_v3
            SELECT id, project_id, graph_json, status, progress, current_node_id,
                   error_code, error_message, result_json, cancel_requested,
                   created_at, started_at, finished_at
            FROM jobs;
        DROP TABLE jobs;
        ALTER TABLE jobs_v3 RENAME TO jobs;
        CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        """,
    ),
    (
        5,
        r"""
        -- GOV-001: as superfícies que a governança prometia e não guardava em lugar
        -- nenhum. Cada tabela aqui existe porque havia informação sendo produzida e
        -- perdida: decisão técnica que só vivia em markdown, dependência open source
        -- sem registro de origem, e auditoria cujo resultado não sobrevivia à sessão.

        -- Decisão técnica com identidade permanente. Um ADR em arquivo solto não
        -- aparece no painel e ninguém descobre por que a arquitetura é como é.
        CREATE TABLE IF NOT EXISTS governance_decisions (
            id TEXT PRIMARY KEY,
            titulo TEXT NOT NULL,
            estado TEXT NOT NULL CHECK(estado IN ('PROPOSTA','ACEITA','SUBSTITUIDA','REJEITADA')),
            contexto TEXT NOT NULL,
            decisao TEXT NOT NULL,
            consequencias TEXT NOT NULL DEFAULT '',
            modulos_json TEXT NOT NULL DEFAULT '[]',
            documento TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Componente de terceiro com origem, licença e onde é usado. Sem isto, a
        -- pergunta "o que este produto redistribui" não tem resposta verificável.
        CREATE TABLE IF NOT EXISTS governance_opensource (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            origem TEXT NOT NULL,
            versao TEXT NOT NULL DEFAULT '',
            licenca TEXT NOT NULL,
            spdx TEXT NOT NULL DEFAULT '',
            uso_comercial TEXT NOT NULL DEFAULT 'UNKNOWN',
            integracao TEXT NOT NULL DEFAULT '',
            redistribuido INTEGER NOT NULL DEFAULT 0,
            conferido INTEGER NOT NULL DEFAULT 0,
            observacao TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        );

        -- Histórico de auditoria. Uma auditoria cujo resultado não fica registrado
        -- é uma auditoria que precisa ser refeita do zero na próxima sessão.
        CREATE TABLE IF NOT EXISTS governance_audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            executado_em TEXT NOT NULL,
            sessao TEXT NOT NULL,
            escopo TEXT NOT NULL DEFAULT '',
            itens_auditados INTEGER NOT NULL DEFAULT 0,
            falhas_encontradas INTEGER NOT NULL DEFAULT 0,
            falhas_corrigidas INTEGER NOT NULL DEFAULT 0,
            testes_total INTEGER NOT NULL DEFAULT 0,
            testes_verdes INTEGER NOT NULL DEFAULT 0,
            resultado TEXT NOT NULL CHECK(resultado IN ('APROVADA','REPROVADA','BLOQUEADA')),
            evidencia_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_governance_audits_data
            ON governance_audits(executado_em DESC);
        """,
    ),
]

# Colunas adicionadas por migração. São aplicadas com verificação prévia no
# PRAGMA table_info, o que torna a migração segura de reexecutar em bancos que já
# passaram por ela — ao contrário de ALTER TABLE ADD COLUMN puro.
COLUMN_ADDITIONS: dict[int, list[tuple[str, str, str]]] = {
    2: [("assets", "deleted_at", "TEXT")],
    # Um alerta precisa dizer de onde veio, o que causa, e qual tarefa o resolve.
    # Sem isso ele é um aviso solto que ninguém sabe como fechar.
    5: [
        ("governance_alerts", "origem", "TEXT NOT NULL DEFAULT ''"),
        ("governance_alerts", "causa", "TEXT NOT NULL DEFAULT ''"),
        ("governance_alerts", "impacto", "TEXT NOT NULL DEFAULT ''"),
        ("governance_alerts", "task_id", "TEXT NOT NULL DEFAULT ''"),
        ("governance_alerts", "arquivos_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("governance_alerts", "teste", "TEXT NOT NULL DEFAULT ''"),
        ("governance_alerts", "resultado", "TEXT NOT NULL DEFAULT ''"),
        ("governance_tasks", "milestone", "TEXT NOT NULL DEFAULT ''"),
        ("governance_tasks", "depende_de", "TEXT NOT NULL DEFAULT ''"),
        ("governance_tasks", "camada", "TEXT NOT NULL DEFAULT ''"),
    ],
}

# Objetos que cada migração precisa ter deixado no banco. O número da versão sozinho
# não prova nada: executescript emite COMMIT implícito, então uma falha no meio do
# script deixa a migração pela metade com a versão já registrada. Conferir os objetos
# permite reaplicar — e todos os scripts usam IF NOT EXISTS, então reaplicar é seguro.
MIGRATION_OBJECTS: dict[int, list[str]] = {
    3: ["project_snapshots", "asset_collections", "asset_collection_items"],
    4: ["node_results"],
    5: ["governance_decisions", "governance_opensource", "governance_audits"],
}


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._migration_lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.path,
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    def initialize(self) -> None:
        with self._migration_lock, self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT "
                "(strftime('%Y-%m-%dT%H:%M:%fZ','now')))"
            )
            applied = {
                int(row["version"])
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            existing_tables = {
                str(row[0])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            for version, sql in MIGRATIONS:
                missing = [
                    name for name in MIGRATION_OBJECTS.get(version, [])
                    if name not in existing_tables
                ]
                if version in applied and not missing:
                    continue
                connection.executescript(sql)
                for table, column, decl in COLUMN_ADDITIONS.get(version, []):
                    existing = {
                        row[1] for row in connection.execute(f"PRAGMA table_info({table})")
                    }
                    if column not in existing:
                        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
                # executescript emite COMMIT implícito, então esta linha pode rodar de
                # novo após uma falha parcial; OR IGNORE evita quebrar por versão duplicada.
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)", (version,)
                )

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        with self.transaction() as connection:
            cursor = connection.execute(sql, params)
            return cursor.rowcount

    def executescript(self, sql: str) -> None:
        with self.transaction() as connection:
            connection.executescript(sql)

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with self.connection() as connection:
            return [dict(row) for row in connection.execute(sql, params).fetchall()]

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(sql, params).fetchone()
            return dict(row) if row is not None else None

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        with self.connection() as connection:
            row = connection.execute(sql, params).fetchone()
            return row[0] if row is not None else None

    @staticmethod
    def dump_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def load_json(value: str | None, default: Any = None) -> Any:
        if value is None:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
