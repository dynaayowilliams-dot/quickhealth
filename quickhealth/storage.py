"""SQLite persistence for fictional clerking sessions."""

import json
import sqlite3
import time
import uuid
from pathlib import Path
from contextlib import contextmanager

import neatlogs
from opentelemetry import trace as otel_trace

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "quickhealth.sqlite3"


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, history TEXT NOT NULL DEFAULT '[]', note TEXT, summary TEXT, urgency TEXT, patient_type TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
        for name, definition in (
            ("input_tokens", "INTEGER NOT NULL DEFAULT 0"),
            ("output_tokens", "INTEGER NOT NULL DEFAULT 0"),
            ("model_latency_ms", "REAL NOT NULL DEFAULT 0"),
        ):
            if name not in columns:
                connection.execute(f"ALTER TABLE sessions ADD COLUMN {name} {definition}")
        connection.commit()
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@neatlogs.span(kind="TOOL", name="sqlite_write_recovery", capture_input=False, capture_output=False)
def _retry_sqlite_write(operation, write):
    """Retry only transient SQLite lock/busy errors; never expose database text to traces."""
    span = otel_trace.get_current_span()
    attempts = 0
    recovered = False
    status = "not_needed"
    try:
        for attempts in range(1, 4):
            try:
                value = write()
                recovered = attempts > 1
                status = "recovered" if recovered else "not_needed"
                return value
            except sqlite3.OperationalError as exc:
                message = str(exc).casefold()
                if "locked" not in message and "busy" not in message:
                    status = "failed"
                    raise
                if attempts == 3:
                    status = "failed"
                    raise
                if span and span.is_recording():
                    span.add_event("sqlite_write_retry", {"attempt": attempts, "error_category": "sqlite_busy"})
                time.sleep(0.05 * attempts)
        raise RuntimeError("SQLite retry loop ended unexpectedly")
    finally:
        if span and span.is_recording():
            span.set_attribute("quickhealth.storage.operation", operation)
            span.set_attribute("quickhealth.storage.attempt_count", attempts)
            span.set_attribute("quickhealth.storage.retry_count", max(0, attempts - 1))
            span.set_attribute("quickhealth.storage.recovered", recovered)
            span.set_attribute("quickhealth.storage.recovery_status", status)


def record_model_usage(session_id, input_tokens, output_tokens, latency_ms):
    """Persist only aggregate usage metrics; no prompts or response text are stored here."""
    with _connect() as connection:
        connection.execute(
            "UPDATE sessions SET input_tokens = input_tokens + ?, output_tokens = output_tokens + ?, "
            "model_latency_ms = model_latency_ms + ? WHERE id = ?",
            (max(0, int(input_tokens)), max(0, int(output_tokens)), max(0.0, float(latency_ms)), session_id),
        )


def completed_usage_totals():
    """Return token/time totals for completed sessions only."""
    with _connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0), "
            "COALESCE(SUM(model_latency_ms),0) FROM sessions WHERE note IS NOT NULL "
            "AND (input_tokens > 0 OR output_tokens > 0)"
        ).fetchone()
    return {"sessions": row[0], "input_tokens": row[1], "output_tokens": row[2], "latency_ms": row[3]}


@neatlogs.span(kind="TOOL", name="sqlite_state_store_create", capture_input=False, capture_output=False)
def create_session():
    session_id = str(uuid.uuid4())[:8]
    def write():
        with _connect() as connection:
            connection.execute("INSERT INTO sessions (id) VALUES (?)", (session_id,))
    _retry_sqlite_write("create_session", write)
    return session_id


@neatlogs.span(kind="TOOL", name="sqlite_state_store_get", capture_input=False, capture_output=False)
def get_session(session_id):
    with _connect() as connection:
        row = connection.execute("SELECT id, history, note, summary, urgency, patient_type FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return row


@neatlogs.span(kind="TOOL", name="sqlite_state_store_list", capture_input=False, capture_output=False)
def list_sessions():
    with _connect() as connection:
        return connection.execute("SELECT id FROM sessions ORDER BY created_at DESC").fetchall()


@neatlogs.span(kind="TOOL", name="sqlite_state_store_save_answer", capture_input=False, capture_output=False)
def save_answer(session_id, question, answer):
    def write():
        with _connect() as connection:
            row = connection.execute("SELECT history FROM sessions WHERE id = ?", (session_id,)).fetchone()
            history = json.loads(row[0]) if row else []
            history.extend([
                {"role": "assistant", "content": question},
                {"role": "user", "content": answer},
            ])
            connection.execute("UPDATE sessions SET history = ? WHERE id = ?", (json.dumps(history), session_id))
    _retry_sqlite_write("save_answer", write)


@neatlogs.span(kind="TOOL", name="sqlite_state_store_save_result", capture_input=False, capture_output=False)
def save_result(session_id, note, summary, urgency, patient_type):
    def write():
        with _connect() as connection:
            connection.execute(
                "UPDATE sessions SET note = ?, summary = ?, urgency = ?, patient_type = ? WHERE id = ?",
                (note, summary, urgency, patient_type, session_id),
            )
    _retry_sqlite_write("save_result", write)


@neatlogs.span(kind="TOOL", name="sqlite_state_store_verification_get", capture_input=False, capture_output=False)
def get_verification_state(session_id):
    with _connect() as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
        if "verification_state" not in columns:
            connection.execute("ALTER TABLE sessions ADD COLUMN verification_state TEXT NOT NULL DEFAULT '{}'")
        row = connection.execute("SELECT verification_state FROM sessions WHERE id = ?", (session_id,)).fetchone()
    try:
        value = json.loads(row[0]) if row and row[0] else {}
        return value if isinstance(value, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


@neatlogs.span(kind="TOOL", name="sqlite_state_store_verification_save", capture_input=False, capture_output=False)
def save_verification_state(session_id, state):
    with _connect() as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
        if "verification_state" not in columns:
            connection.execute("ALTER TABLE sessions ADD COLUMN verification_state TEXT NOT NULL DEFAULT '{}'")
        connection.execute(
            "UPDATE sessions SET verification_state = ? WHERE id = ?",
            (json.dumps(state, ensure_ascii=True), session_id),
        )
