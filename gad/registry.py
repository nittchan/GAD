"""
SQLite registry for trigger definitions and basis risk reports (Phase 2).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from gad._models_legacy import BasisRiskReport, TriggerDef


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: str | Path) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS triggers (
                id TEXT PRIMARY KEY,
                definition_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                trigger_id TEXT PRIMARY KEY,
                report_json TEXT NOT NULL,
                computed_at TEXT NOT NULL,
                FOREIGN KEY (trigger_id) REFERENCES triggers(id)
            )
            """
        )
        conn.commit()


def upsert_trigger(conn: sqlite3.Connection, trigger: TriggerDef) -> None:
    now = _utc_now()
    payload = trigger.model_dump_json()
    conn.execute(
        """
        INSERT INTO triggers (id, definition_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            definition_json = excluded.definition_json,
            updated_at = excluded.updated_at
        """,
        (trigger.id, payload, now, now),
    )
    conn.commit()


def save_report(conn: sqlite3.Connection, trigger_id: str, report: BasisRiskReport) -> None:
    now = _utc_now()
    payload = report.model_dump_json()
    conn.execute(
        """
        INSERT INTO reports (trigger_id, report_json, computed_at)
        VALUES (?, ?, ?)
        ON CONFLICT(trigger_id) DO UPDATE SET
            report_json = excluded.report_json,
            computed_at = excluded.computed_at
        """,
        (trigger_id, payload, now),
    )
    conn.commit()


def get_trigger(conn: sqlite3.Connection, trigger_id: str) -> TriggerDef | None:
    row = conn.execute(
        "SELECT definition_json FROM triggers WHERE id = ?",
        (trigger_id,),
    ).fetchone()
    if not row:
        return None
    return TriggerDef.model_validate_json(row[0])


def get_report(conn: sqlite3.Connection, trigger_id: str) -> BasisRiskReport | None:
    row = conn.execute(
        "SELECT report_json FROM reports WHERE trigger_id = ?",
        (trigger_id,),
    ).fetchone()
    if not row:
        return None
    return BasisRiskReport.model_validate_json(row[0])


def list_trigger_ids(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT id FROM triggers ORDER BY id").fetchall()
    return [r[0] for r in rows]


def list_trigger_ids_with_reports(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT t.id FROM triggers t INNER JOIN reports r ON t.id = r.trigger_id ORDER BY t.id"
    ).fetchall()
    return [r[0] for r in rows]


def delete_trigger(conn: sqlite3.Connection, trigger_id: str) -> None:
    conn.execute("DELETE FROM reports WHERE trigger_id = ?", (trigger_id,))
    conn.execute("DELETE FROM triggers WHERE id = ?", (trigger_id,))
    conn.commit()


class Registry:
    """Context manager for registry DB; use as default path when path not provided."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def __enter__(self) -> sqlite3.Connection:
        init_db(self.db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        return self._conn

    def __exit__(self, *args) -> None:
        self._conn.close()
