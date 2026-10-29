"""Fonctions simples pour creer et utiliser la base SQLite Govern IA."""

import sqlite3
import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", ROOT_DIR / "dataguard.db")).expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = ROOT_DIR / DB_PATH


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_database():
    """Cree la base et ses tables si elles n'existent pas deja."""
    connection = _connect()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source TEXT NOT NULL,
                file_path TEXT NOT NULL,
                row_count INTEGER NOT NULL DEFAULT 0 CHECK (row_count >= 0),
                column_count INTEGER NOT NULL DEFAULT 0 CHECK (column_count >= 0),
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                agent_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                agent_id INTEGER NOT NULL,
                row_number INTEGER,
                column_name TEXT,
                anomaly_type TEXT NOT NULL,
                original_value TEXT,
                severity TEXT NOT NULL,
                detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id),
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            );

            CREATE TABLE IF NOT EXISTS classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                column_name TEXT NOT NULL,
                classification TEXT NOT NULL,
                confidence REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id)
            );

            CREATE TABLE IF NOT EXISTS security_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                column_name TEXT NOT NULL,
                finding_type TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id)
            );

            CREATE TABLE IF NOT EXISTS lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                action TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id)
            );

            CREATE TABLE IF NOT EXISTS documentations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id)
            );

            CREATE TABLE IF NOT EXISTS validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('PENDING', 'VALIDATED', 'REJECTED')
                ),
                validator_role TEXT NOT NULL,
                rejection_reason TEXT,
                validated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id)
            );

            CREATE INDEX IF NOT EXISTS idx_anomalies_dataset_id_id
                ON anomalies(dataset_id, id);
            CREATE INDEX IF NOT EXISTS idx_anomalies_dataset_type
                ON anomalies(dataset_id, anomaly_type);
            CREATE INDEX IF NOT EXISTS idx_anomalies_dataset_severity
                ON anomalies(dataset_id, severity);
            CREATE INDEX IF NOT EXISTS idx_anomalies_dataset_column
                ON anomalies(dataset_id, column_name);
            CREATE INDEX IF NOT EXISTS idx_classifications_dataset_id
                ON classifications(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_security_findings_dataset_id
                ON security_findings(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_lineage_dataset_id
                ON lineage(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_documentations_dataset_id_id
                ON documentations(dataset_id, id);
            CREATE INDEX IF NOT EXISTS idx_validations_dataset_id_id
                ON validations(dataset_id, id);
            """
        )
        connection.commit()
    finally:
        connection.close()


def _insert(query, values):
    connection = _connect()
    try:
        cursor = connection.execute(query, values)
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def _insert_many(query, rows):
    if not rows:
        return 0
    connection = _connect()
    try:
        cursor = connection.executemany(query, rows)
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


def insert_dataset(name, source, file_path, row_count=0, column_count=0):
    return _insert(
        """
        INSERT INTO datasets (name, source, file_path, row_count, column_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, source, file_path, row_count, column_count),
    )


def insert_anomaly(
    dataset_id,
    agent_id,
    anomaly_type,
    severity,
    row_number=None,
    column_name=None,
    original_value=None,
):
    return _insert(
        """
        INSERT INTO anomalies (
            dataset_id, agent_id, row_number, column_name,
            anomaly_type, original_value, severity
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dataset_id,
            agent_id,
            row_number,
            column_name,
            anomaly_type,
            original_value,
            severity,
        ),
    )


def insert_anomalies(dataset_id, agent_id, issues):
    return _insert_many(
        """
        INSERT INTO anomalies (
            dataset_id, agent_id, row_number, column_name,
            anomaly_type, original_value, severity
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                dataset_id,
                agent_id,
                issue["row_number"],
                issue["column_name"],
                issue["anomaly_type"],
                None
                if issue["original_value"] is None
                else str(issue["original_value"]),
                issue["severity"],
            )
            for issue in issues
        ],
    )


def insert_classification(dataset_id, column_name, classification, confidence=None):
    return _insert(
        """
        INSERT INTO classifications (
            dataset_id, column_name, classification, confidence
        )
        VALUES (?, ?, ?, ?)
        """,
        (dataset_id, column_name, classification, confidence),
    )


def insert_classifications(dataset_id, classifications):
    return _insert_many(
        """
        INSERT INTO classifications (
            dataset_id, column_name, classification, confidence
        )
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                dataset_id,
                item["column_name"],
                item["classification"],
                item["confidence"],
            )
            for item in classifications
        ],
    )


def insert_security_finding(dataset_id, column_name, finding_type, recommendation):
    return _insert(
        """
        INSERT INTO security_findings (
            dataset_id, column_name, finding_type, recommendation
        )
        VALUES (?, ?, ?, ?)
        """,
        (dataset_id, column_name, finding_type, recommendation),
    )


def insert_security_findings(dataset_id, findings):
    return _insert_many(
        """
        INSERT INTO security_findings (
            dataset_id, column_name, finding_type, recommendation
        )
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                dataset_id,
                item["column_name"],
                item["finding_type"],
                item["recommendation"],
            )
            for item in findings
        ],
    )


def insert_lineage(dataset_id, agent_name, action, description):
    return _insert(
        """
        INSERT INTO lineage (dataset_id, agent_name, action, description)
        VALUES (?, ?, ?, ?)
        """,
        (dataset_id, agent_name, action, description),
    )


def insert_lineage_events(dataset_id, agent_name, events):
    return _insert_many(
        """
        INSERT INTO lineage (dataset_id, agent_name, action, description)
        VALUES (?, ?, ?, ?)
        """,
        [
            (dataset_id, agent_name, action, description)
            for action, description in events
        ],
    )


def insert_documentation(dataset_id, summary):
    return _insert(
        "INSERT INTO documentations (dataset_id, summary) VALUES (?, ?)",
        (dataset_id, summary),
    )


def insert_validation(
    dataset_id, status, validator_role, rejection_reason=None
):
    return _insert(
        """
        INSERT INTO validations (
            dataset_id, status, validator_role, rejection_reason
        )
        VALUES (?, ?, ?, ?)
        """,
        (dataset_id, status, validator_role, rejection_reason),
    )


def get_dataset(dataset_id):
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        connection.close()


def get_agent_id(agent_name):
    """Retourne l'identifiant SQLite d'un agent déjà initialisé."""
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT id FROM agents WHERE name = ?", (agent_name,)
        ).fetchone()
        if row is None:
            raise ValueError(
                f"Agent introuvable dans SQLite : {agent_name}. "
                "Lancez initialize_agents() avant le pipeline."
            )
        return row["id"]
    finally:
        connection.close()


def get_anomalies(dataset_id):
    connection = _connect()
    try:
        rows = connection.execute(
            """
            SELECT * FROM anomalies
            WHERE dataset_id = ?
            ORDER BY id
            """,
            (dataset_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_anomalies_page(
    dataset_id,
    page=1,
    page_size=50,
    anomaly_type="",
    severity="",
    column_search="",
):
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 100)
    conditions = ["dataset_id = ?"]
    values = [dataset_id]
    if anomaly_type:
        conditions.append("anomaly_type = ?")
        values.append(anomaly_type)
    if severity:
        conditions.append("severity = ?")
        values.append(severity)
    if column_search:
        conditions.append("COALESCE(column_name, '') LIKE ?")
        values.append(f"%{column_search}%")

    where_clause = " AND ".join(conditions)
    connection = _connect()
    try:
        total = connection.execute(
            f"SELECT COUNT(*) FROM anomalies WHERE {where_clause}", values
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT * FROM anomalies
            WHERE {where_clause}
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            [*values, page_size, (page - 1) * page_size],
        ).fetchall()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    finally:
        connection.close()


def get_anomaly_filter_options(dataset_id):
    connection = _connect()
    try:
        anomaly_types = connection.execute(
            "SELECT DISTINCT anomaly_type FROM anomalies "
            "WHERE dataset_id = ? ORDER BY anomaly_type",
            (dataset_id,),
        ).fetchall()
        severities = connection.execute(
            "SELECT DISTINCT severity FROM anomalies "
            "WHERE dataset_id = ? ORDER BY severity",
            (dataset_id,),
        ).fetchall()
        return {
            "types": [row[0] for row in anomaly_types],
            "severities": [row[0] for row in severities],
        }
    finally:
        connection.close()


def get_dataset_counts(dataset_id):
    connection = _connect()
    try:
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM anomalies WHERE dataset_id = ?) AS anomaly_count,
                (SELECT COUNT(*) FROM classifications WHERE dataset_id = ?) AS classification_count,
                (SELECT COUNT(*) FROM security_findings WHERE dataset_id = ?) AS security_count,
                (SELECT COUNT(*) FROM lineage WHERE dataset_id = ?) AS lineage_count
            """,
            (dataset_id, dataset_id, dataset_id, dataset_id),
        ).fetchone()
        return dict(row)
    finally:
        connection.close()


def get_dashboard_distributions(dataset_id):
    connection = _connect()
    try:
        return {
            "anomaly_types": [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT anomaly_type AS label, COUNT(*) AS count
                    FROM anomalies WHERE dataset_id = ?
                    GROUP BY anomaly_type ORDER BY count DESC, label
                    """,
                    (dataset_id,),
                ).fetchall()
            ],
            "severities": [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT severity AS label, COUNT(*) AS count
                    FROM anomalies WHERE dataset_id = ?
                    GROUP BY severity ORDER BY count DESC, label
                    """,
                    (dataset_id,),
                ).fetchall()
            ],
            "classifications": [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT classification AS label, COUNT(*) AS count
                    FROM classifications WHERE dataset_id = ?
                    GROUP BY classification ORDER BY count DESC, label
                    """,
                    (dataset_id,),
                ).fetchall()
            ],
        }
    finally:
        connection.close()


def _get_rows(query, values=()):
    connection = _connect()
    try:
        rows = connection.execute(query, values).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_datasets(limit=None):
    """Retourne les datasets, du plus récent au plus ancien."""
    if limit is None:
        return _get_rows("SELECT * FROM datasets ORDER BY id DESC")
    return _get_rows(
        "SELECT * FROM datasets ORDER BY id DESC LIMIT ?",
        (max(int(limit), 1),),
    )


def get_classifications(dataset_id):
    return _get_rows(
        """
        SELECT * FROM classifications
        WHERE dataset_id = ?
        ORDER BY id
        """,
        (dataset_id,),
    )


def get_security_findings(dataset_id):
    return _get_rows(
        """
        SELECT * FROM security_findings
        WHERE dataset_id = ?
        ORDER BY id
        """,
        (dataset_id,),
    )


def get_lineage(dataset_id):
    return _get_rows(
        "SELECT * FROM lineage WHERE dataset_id = ? ORDER BY id",
        (dataset_id,),
    )


def get_documentation(dataset_id):
    rows = _get_rows(
        """
        SELECT * FROM documentations
        WHERE dataset_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (dataset_id,),
    )
    return rows[0] if rows else None


def get_validation(dataset_id):
    rows = _get_rows(
        """
        SELECT * FROM validations
        WHERE dataset_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (dataset_id,),
    )
    return rows[0] if rows else None