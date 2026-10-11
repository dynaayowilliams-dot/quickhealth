"""SQLite persistence for fictional clerking sessions."""

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

import neatlogs
from opentelemetry import trace as otel_trace

DB_PATH = Path(os.environ.get("QUICKHEALTH_DB_PATH", Path(__file__).resolve().parents[1] / "data" / "quickhealth.sqlite3"))


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
            ("model_calls", "INTEGER NOT NULL DEFAULT 0"),
            ("case_label", "TEXT"),
        ):
            if name not in columns:
                connection.execute(f"ALTER TABLE sessions ADD COLUMN {name} {definition}")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS daily_model_calls "
            "(utc_date TEXT PRIMARY KEY, calls INTEGER NOT NULL DEFAULT 0)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS session_id_sequence "
            "(singleton INTEGER PRIMARY KEY CHECK(singleton = 1), next_number INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT OR IGNORE INTO session_id_sequence (singleton, next_number) VALUES (1, 1)"
        )
        connection.commit()
        unlabelled = connection.execute(
            "SELECT 1 FROM sessions WHERE case_label IS NULL OR case_label = '' LIMIT 1"
        ).fetchone()
        if unlabelled:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT id FROM sessions WHERE case_label IS NULL OR case_label = '' "
                "ORDER BY created_at, id"
            ).fetchall()
            sequence = connection.execute(
                "SELECT next_number FROM session_id_sequence WHERE singleton = 1"
            ).fetchone()[0]
            labels = connection.execute(
                "SELECT case_label FROM sessions WHERE case_label GLOB 'A[0-9]*'"
            ).fetchall()
            latest_label = max(
                (int(label[0][1:]) for label in labels if label[0][1:].isdigit()),
                default=0,
            )
            sequence = max(sequence, latest_label + 1)
            for (session_id,) in rows:
                connection.execute(
                    "UPDATE sessions SET case_label = ? WHERE id = ?",
                    (f"A{sequence:03d}", session_id),
                )
                sequence += 1
            connection.execute(
                "UPDATE session_id_sequence SET next_number = ? WHERE singleton = 1",
                (sequence,),
            )
            connection.commit()
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def reserve_model_call(session_id, per_session_limit, daily_limit):
    """Atomically reserve one model call; return its limit reason or None."""
    today = datetime.now(timezone.utc).date().isoformat()
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        session = connection.execute(
            "SELECT model_calls FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        # Some unit-level workflow callers use synthetic IDs without creating a
        # stored session. Do not apply production quotas to those test doubles.
        if session is None:
            return None
        daily = connection.execute(
            "SELECT calls FROM daily_model_calls WHERE utc_date = ?", (today,)
        ).fetchone()
        if session[0] >= per_session_limit:
            return "session"
        if daily and daily[0] >= daily_limit:
            return "daily"
        connection.execute(
            "UPDATE sessions SET model_calls = model_calls + 1 WHERE id = ?", (session_id,)
        )
        connection.execute(
            "INSERT INTO daily_model_calls (utc_date, calls) VALUES (?, 1) "
            "ON CONFLICT(utc_date) DO UPDATE SET calls = calls + 1",
            (today,),
        )
    return None


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
    def write():
        with _connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            sequence = connection.execute(
                "SELECT next_number FROM session_id_sequence WHERE singleton = 1"
            ).fetchone()[0]
            labels = connection.execute(
                "SELECT case_label FROM sessions WHERE case_label GLOB 'A[0-9]*'"
            ).fetchall()
            latest_label = max(
                (int(label[0][1:]) for label in labels if label[0][1:].isdigit()),
                default=0,
            )
            sequence = max(sequence, latest_label + 1)
            case_label = f"A{sequence:03d}"
            connection.execute(
                "UPDATE session_id_sequence SET next_number = ? WHERE singleton = 1",
                (sequence + 1,),
            )
            connection.execute(
                "INSERT INTO sessions (id, case_label) VALUES (?, ?)",
                (case_label, case_label),
            )
            return case_label
    return _retry_sqlite_write("create_session", write)


@neatlogs.span(kind="TOOL", name="sqlite_state_store_get", capture_input=False, capture_output=False)
def get_session(session_id):
    with _connect() as connection:
        row = connection.execute("SELECT id, history, note, summary, urgency, patient_type FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return row


@neatlogs.span(kind="TOOL", name="sqlite_state_store_list", capture_input=False, capture_output=False)
def list_sessions():
    with _connect() as connection:
        return connection.execute(
            "SELECT id, case_label FROM sessions ORDER BY created_at DESC, id DESC"
        ).fetchall()


@neatlogs.span(kind="TOOL", name="sqlite_state_store_clear_fictional_sessions", capture_input=False, capture_output=False)
def clear_fictional_sessions():
    """Delete saved fictional sessions from the configured QuickHealth database."""
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM sessions")
        return cursor.rowcount


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
