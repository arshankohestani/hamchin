from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # SQLite keeps local development and tests self-contained.
    psycopg = None
    dict_row = None


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = Path(os.environ.get("HAMCHIN_DB_PATH", "/tmp/hamchin-scheduler.db" if os.environ.get("VERCEL") else DATA_DIR / "scheduler.db"))


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "").strip()


def database_provider() -> str:
    return "neon-postgres" if _database_url() else "sqlite-local"


def _pg_connect():
    if psycopg is None:
        raise RuntimeError("برای اتصال Neon بسته psycopg نصب نشده است")
    return psycopg.connect(_database_url(), row_factory=dict_row)


def initialize_database() -> None:
    if _database_url():
        with _pg_connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS revisions (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS demand_history (
                    id BIGSERIAL PRIMARY KEY,
                    academic_term TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    enrolled_count INTEGER NOT NULL,
                    capacity INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS demand_forecasts (
                    academic_term TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    predicted_count INTEGER NOT NULL,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (academic_term, course_id)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS manager_feedback (
                    id BIGSERIAL PRIMARY KEY,
                    revision_id BIGINT NOT NULL REFERENCES revisions(id) ON DELETE CASCADE,
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                    comment TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS manager_preferences (
                    preference_key TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS ml_models (
                    model_key TEXT PRIMARY KEY,
                    metadata JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                score INTEGER NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS demand_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                academic_term TEXT NOT NULL,
                course_id TEXT NOT NULL,
                enrolled_count INTEGER NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS demand_forecasts (
                academic_term TEXT NOT NULL,
                course_id TEXT NOT NULL,
                predicted_count INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                model_version TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (academic_term, course_id)
            );
            CREATE TABLE IF NOT EXISTS manager_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                revision_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS manager_preferences (
                preference_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ml_models (
                model_key TEXT PRIMARY KEY,
                metadata TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)


def save_revision(name: str, score: int, payload: dict[str, Any]) -> int:
    initialize_database()
    if _database_url():
        with _pg_connect() as connection:
            row = connection.execute(
                "INSERT INTO revisions (name, status, score, payload) VALUES (%s, %s, %s, %s::jsonb) RETURNING id",
                (name, "draft", score, json.dumps(payload, ensure_ascii=False)),
            ).fetchone()
            return int(row["id"])
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "INSERT INTO revisions (name, status, score, payload) VALUES (?, ?, ?, ?)",
            (name, "draft", score, json.dumps(payload, ensure_ascii=False)),
        )
        return int(cursor.lastrowid)


def list_revisions() -> list[dict[str, Any]]:
    initialize_database()
    query = "SELECT id, name, status, score, created_at FROM revisions ORDER BY id DESC LIMIT 10"
    if _database_url():
        with _pg_connect() as connection:
            return [dict(row) for row in connection.execute(query).fetchall()]
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query).fetchall()]


def approve_revision(revision_id: int) -> bool:
    initialize_database()
    if _database_url():
        with _pg_connect() as connection:
            connection.execute("UPDATE revisions SET status = 'archived' WHERE status = 'approved'")
            cursor = connection.execute("UPDATE revisions SET status = 'approved' WHERE id = %s", (revision_id,))
            return cursor.rowcount == 1
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("UPDATE revisions SET status = 'archived' WHERE status = 'approved'")
        cursor = connection.execute("UPDATE revisions SET status = 'approved' WHERE id = ?", (revision_id,))
        return cursor.rowcount == 1


def save_demand_history(records: list[dict[str, Any]]) -> int:
    initialize_database()
    values = [(item["academic_term"], item["course_id"], item["enrolled_count"], item.get("capacity", 0)) for item in records]
    if _database_url():
        with _pg_connect() as connection:
            connection.executemany(
                "INSERT INTO demand_history (academic_term, course_id, enrolled_count, capacity) VALUES (%s, %s, %s, %s)", values
            )
    else:
        with sqlite3.connect(DB_PATH) as connection:
            connection.executemany(
                "INSERT INTO demand_history (academic_term, course_id, enrolled_count, capacity) VALUES (?, ?, ?, ?)", values
            )
    return len(values)


def get_demand_forecasts(academic_term: str) -> list[dict[str, Any]]:
    initialize_database()
    query = "SELECT academic_term, course_id, predicted_count, model_name, model_version FROM demand_forecasts WHERE academic_term = "
    if _database_url():
        with _pg_connect() as connection:
            return [dict(row) for row in connection.execute(query + "%s", (academic_term,)).fetchall()]
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query + "?", (academic_term,)).fetchall()]


def demand_training_rows() -> list[dict[str, Any]]:
    initialize_database()
    query = "SELECT academic_term, course_id, enrolled_count, capacity FROM demand_history ORDER BY academic_term, course_id"
    if _database_url():
        with _pg_connect() as connection:
            return [dict(row) for row in connection.execute(query).fetchall()]
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query).fetchall()]


def upsert_demand_forecasts(records: list[dict[str, Any]]) -> int:
    initialize_database()
    values = [
        (item["academic_term"], item["course_id"], item["predicted_count"], item["model_name"], item["model_version"])
        for item in records
    ]
    if _database_url():
        with _pg_connect() as connection:
            connection.executemany("""
                INSERT INTO demand_forecasts (academic_term, course_id, predicted_count, model_name, model_version)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (academic_term, course_id) DO UPDATE SET
                    predicted_count = EXCLUDED.predicted_count, model_name = EXCLUDED.model_name,
                    model_version = EXCLUDED.model_version, created_at = CURRENT_TIMESTAMP
            """, values)
    else:
        with sqlite3.connect(DB_PATH) as connection:
            connection.executemany("""
                INSERT INTO demand_forecasts (academic_term, course_id, predicted_count, model_name, model_version)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(academic_term, course_id) DO UPDATE SET
                    predicted_count = excluded.predicted_count, model_name = excluded.model_name,
                    model_version = excluded.model_version, created_at = CURRENT_TIMESTAMP
            """, values)
    return len(values)


def save_model_metadata(model_key: str, metadata: dict[str, Any]) -> None:
    initialize_database()
    serialized = json.dumps(metadata, ensure_ascii=False)
    if _database_url():
        with _pg_connect() as connection:
            connection.execute("""
                INSERT INTO ml_models (model_key, metadata) VALUES (%s, %s::jsonb)
                ON CONFLICT (model_key) DO UPDATE SET metadata = EXCLUDED.metadata, updated_at = CURRENT_TIMESTAMP
            """, (model_key, serialized))
    else:
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("""
                INSERT INTO ml_models (model_key, metadata) VALUES (?, ?)
                ON CONFLICT(model_key) DO UPDATE SET metadata = excluded.metadata, updated_at = CURRENT_TIMESTAMP
            """, (model_key, serialized))


def save_feedback(revision_id: int, rating: int, comment: str) -> bool:
    initialize_database()
    if _database_url():
        with _pg_connect() as connection:
            exists = connection.execute("SELECT 1 FROM revisions WHERE id = %s", (revision_id,)).fetchone()
            if not exists:
                return False
            connection.execute(
                "INSERT INTO manager_feedback (revision_id, rating, comment) VALUES (%s, %s, %s)",
                (revision_id, rating, comment),
            )
    else:
        with sqlite3.connect(DB_PATH) as connection:
            exists = connection.execute("SELECT 1 FROM revisions WHERE id = ?", (revision_id,)).fetchone()
            if not exists:
                return False
            connection.execute(
                "INSERT INTO manager_feedback (revision_id, rating, comment) VALUES (?, ?, ?)",
                (revision_id, rating, comment),
            )
    _refresh_slot_preferences()
    return True


def _refresh_slot_preferences() -> None:
    rows = feedback_training_rows()
    weighted: dict[str, float] = {}
    totals: dict[str, float] = {}
    for row in rows:
        payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
        for assignment in payload.get("assignments", []):
            slot_id = assignment.get("slot", {}).get("id")
            if slot_id:
                weighted[slot_id] = weighted.get(slot_id, 0) + float(row["rating"])
                totals[slot_id] = totals.get(slot_id, 0) + 1
    preferences = {slot_id: round(20 * weighted[slot_id] / totals[slot_id]) for slot_id in weighted}
    save_preference("slot_scores", preferences)


def save_preference(key: str, payload: dict[str, Any]) -> None:
    initialize_database()
    serialized = json.dumps(payload, ensure_ascii=False)
    if _database_url():
        with _pg_connect() as connection:
            connection.execute("""
                INSERT INTO manager_preferences (preference_key, payload) VALUES (%s, %s::jsonb)
                ON CONFLICT (preference_key) DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
            """, (key, serialized))
    else:
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("""
                INSERT INTO manager_preferences (preference_key, payload) VALUES (?, ?)
                ON CONFLICT(preference_key) DO UPDATE SET payload = excluded.payload, updated_at = CURRENT_TIMESTAMP
            """, (key, serialized))


def get_preference(key: str) -> dict[str, Any]:
    initialize_database()
    if _database_url():
        with _pg_connect() as connection:
            row = connection.execute("SELECT payload FROM manager_preferences WHERE preference_key = %s", (key,)).fetchone()
    else:
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT payload FROM manager_preferences WHERE preference_key = ?", (key,)).fetchone()
    if not row:
        return {}
    payload = row["payload"]
    return payload if isinstance(payload, dict) else json.loads(payload)


def feedback_training_rows() -> list[dict[str, Any]]:
    initialize_database()
    query = """
        SELECT f.rating, f.comment, r.id AS revision_id, r.name, r.score, r.payload
        FROM manager_feedback f JOIN revisions r ON r.id = f.revision_id ORDER BY f.id
    """
    if _database_url():
        with _pg_connect() as connection:
            return [dict(row) for row in connection.execute(query).fetchall()]
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query).fetchall()]
