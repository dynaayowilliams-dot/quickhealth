import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quickhealth import storage


class StorageRecoveryTests(unittest.TestCase):
    def test_transient_sqlite_busy_is_retried_and_succeeds(self):
        calls = 0

        def write():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise sqlite3.OperationalError("database is locked")
            return "saved"

        with patch.object(storage.time, "sleep"):
            self.assertEqual(storage._retry_sqlite_write("test_write", write), "saved")
        self.assertEqual(calls, 2)

    def test_non_transient_sqlite_error_is_not_retried(self):
        calls = 0

        def write():
            nonlocal calls
            calls += 1
            raise sqlite3.OperationalError("malformed database schema")

        with self.assertRaises(sqlite3.OperationalError):
            storage._retry_sqlite_write("test_write", write)
        self.assertEqual(calls, 1)

    def test_completed_usage_totals_only_count_finished_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "test.sqlite3"
            with patch.object(storage, "DB_PATH", test_db):
                finished = storage.create_session()
                unfinished = storage.create_session()
                storage.record_model_usage(finished, 120, 30, 500)
                storage.record_model_usage(unfinished, 1000, 200, 9000)
                storage.save_result(finished, "fictional note", "fictional summary", "ROUTINE", "general")
                self.assertEqual(
                    storage.completed_usage_totals(),
                    {"sessions": 1, "input_tokens": 120, "output_tokens": 30, "latency_ms": 500.0},
                )


if __name__ == "__main__":
    unittest.main()
