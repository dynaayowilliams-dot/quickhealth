"""Keep every test run's SQLite writes outside the app data directory."""

import os
import tempfile
from pathlib import Path

_TEST_DATABASE_DIR = tempfile.TemporaryDirectory(prefix="quickhealth-tests-")
os.environ["QUICKHEALTH_DB_PATH"] = str(Path(_TEST_DATABASE_DIR.name) / "tests.sqlite3")
