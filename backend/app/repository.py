from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = Path(
    os.environ.get(
        "HAMCHIN_DB_PATH",
        "/tmp/hamchin-scheduler.db" if os.environ.get("VERCEL") else DATA_DIR / "scheduler.db",
    )
)


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                score INTEGER NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_revision(name: str, score: int, payload: dict[str, Any]) -> int:
    initialize_database()
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "INSERT INTO revisions (name, status, score, payload) VALUES (?, ?, ?, ?)",
            (name, "draft", score, json.dumps(payload, ensure_ascii=False)),
        )
        return int(cursor.lastrowid)


def list_revisions() -> list[dict[str, Any]]:
    initialize_database()
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, name, status, score, created_at FROM revisions ORDER BY id DESC LIMIT 10"
        ).fetchall()
        return [dict(row) for row in rows]


def approve_revision(revision_id: int) -> bool:
    initialize_database()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("UPDATE revisions SET status = 'archived' WHERE status = 'approved'")
        cursor = connection.execute(
            "UPDATE revisions SET status = 'approved' WHERE id = ?", (revision_id,)
        )
        return cursor.rowcount == 1

