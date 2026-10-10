"""SQLite persistence for fictional clerking sessions."""

import json
import sqlite3
import uuid
from pathlib import Path

import neatlogs

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "quickhealth.sqlite3"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, history TEXT NOT NULL DEFAULT '[]', note TEXT, summary TEXT, urgency TEXT, patient_type TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    connection.commit()
    return connection


@neatlogs.span(kind="TOOL", name="sqlite_state_store_create")
def create_session():
    session_id = str(uuid.uuid4())[:8]
    with _connect() as connection:
        connection.execute("INSERT INTO sessions (id) VALUES (?)", (session_id,))
    return session_id


@neatlogs.span(kind="TOOL", name="sqlite_state_store_get")
def get_session(session_id):
    with _connect() as connection:
        row = connection.execute("SELECT id, history, note, summary, urgency, patient_type FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return row


@neatlogs.span(kind="TOOL", name="sqlite_state_store_list")
def list_sessions():
    with _connect() as connection:
        return connection.execute("SELECT id FROM sessions ORDER BY created_at DESC").fetchall()


@neatlogs.span(kind="TOOL", name="sqlite_state_store_save_answer")
def save_answer(session_id, question, answer):
    with _connect() as connection:
        row = connection.execute("SELECT history FROM sessions WHERE id = ?", (session_id,)).fetchone()
        history = json.loads(row[0]) if row else []
        history.extend([
            {"role": "assistant", "content": question},
            {"role": "user", "content": answer},
        ])
        connection.execute("UPDATE sessions SET history = ? WHERE id = ?", (json.dumps(history), session_id))


@neatlogs.span(kind="TOOL", name="sqlite_state_store_save_result")
def save_result(session_id, note, summary, urgency, patient_type):
    with _connect() as connection:
        connection.execute(
            "UPDATE sessions SET note = ?, summary = ?, urgency = ?, patient_type = ? WHERE id = ?",
            (note, summary, urgency, patient_type, session_id),
        )
