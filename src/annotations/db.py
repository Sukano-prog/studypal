"""SQLite schema and connection for annotations."""
import sqlite3
from pathlib import Path

from utils.paths import get_db_path, get_data_dir

DB_DIR = get_data_dir()
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = get_db_path()

SCHEMA = """
CREATE TABLE IF NOT EXISTS annotations (
    id            TEXT PRIMARY KEY,
    doc_hash      TEXT NOT NULL,
    char_start    INTEGER NOT NULL,
    char_end      INTEGER NOT NULL,
    line_number   INTEGER,
    audio_ms      INTEGER,
    type          TEXT NOT NULL,
    color         TEXT,
    content       TEXT,
    tags          TEXT DEFAULT '[]',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_doc_hash   ON annotations(doc_hash);
CREATE INDEX IF NOT EXISTS idx_type       ON annotations(type);
CREATE INDEX IF NOT EXISTS idx_char_start ON annotations(doc_hash, char_start);
"""


def get_connection() -> sqlite3.Connection:
    """Return a connection with row access by name."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call repeatedly."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    print(f"[Annotations] DB ready at {DB_PATH}")
