"""Persistencia del historial de revisiones en SQLite.

Cada conciliación ejecada se guarda como una revisión con su resumen,
de modo que el usuario puede consultar qué se concilió, cuándo y con qué archivos.

Programa creado por Sebastián Romero
"""

import json
import sqlite3
from datetime import datetime

from comofi import config
from comofi.reconciler import ReconciliationResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    bank_file TEXT NOT NULL,
    internal_file TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    detail_json TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def save_revision(result: ReconciliationResult, bank_file: str, internal_file: str) -> int:
    """Guarda una revisión y devuelve su id. Recorta el historial al máximo configurado."""
    detail = {
        "matched": [
            {
                "bank_ref": p.bank_row[config.COL_ID],
                "internal_ref": p.internal_row[config.COL_ID],
                "status": p.status,
                "amount_diff": p.amount_diff,
                "days_diff": p.days_diff,
                "score": round(p.score, 3),
            }
            for p in result.matched + result.discrepancies
        ],
        "pending_bank": len(result.pending_bank),
        "pending_internal": len(result.pending_internal),
        "duplicate_groups": len(result.duplicates),
    }
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO revisions (timestamp, bank_file, internal_file, summary_json, detail_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                bank_file,
                internal_file,
                json.dumps(result.summary()),
                json.dumps(detail),
            ),
        )
        revision_id = cursor.lastrowid
        conn.execute(
            "DELETE FROM revisions WHERE id <= ("
            "SELECT MAX(id) FROM revisions) - ?",
            (config.MAX_REVISIONS_KEPT,),
        )
    return revision_id


def list_revisions(limit: int = 20) -> list[dict]:
    """Últimas revisiones, más recientes primero, con el resumen deserializado."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, timestamp, bank_file, internal_file, summary_json, detail_json "
            "FROM revisions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    revisions = []
    for row in rows:
        revisions.append(
            {
                "id": row[0],
                "timestamp": row[1],
                "bank_file": row[2],
                "internal_file": row[3],
                "summary": json.loads(row[4]),
                "detail": json.loads(row[5]),
            }
        )
    return revisions
