from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from bibliotecario.config import db_path

SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    title TEXT,
    paper_hash TEXT UNIQUE,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_idx INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding BLOB,
    UNIQUE(doc_id, chunk_idx)
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);

CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('entity','paper','technique','procedure')),
    label TEXT NOT NULL,
    metadata TEXT,
    UNIQUE(kind, label)
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY,
    src INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    dst INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('factual','procedural')),
    metadata TEXT,
    weight REAL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_unique ON edges(src, dst, relation, kind);

CREATE TABLE IF NOT EXISTS validation_tasks (
    id INTEGER PRIMARY KEY,
    task_text TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('qa','retrieval_judge','blueprint_check')),
    expected_answer TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS task_outcomes (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES validation_tasks(id) ON DELETE CASCADE,
    harness_run_id TEXT,
    success INTEGER NOT NULL,
    observed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_task_outcomes_task ON task_outcomes(task_id);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL,
    what_worked TEXT,
    what_failed TEXT,
    key_insights TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    skill_md TEXT NOT NULL,
    purpose_md TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS wiki_pages (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('raw','accumulated','skill')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS harness_runs (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    score REAL,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS memory_items (
    id INTEGER PRIMARY KEY,
    level TEXT NOT NULL CHECK(level IN ('L0','L1','L2','L3')) DEFAULT 'L0',
    content TEXT NOT NULL,
    embedding BLOB,
    strength REAL NOT NULL DEFAULT 1.0,
    last_access TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_memory_level ON memory_items(level);
"""


def _connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn(path: Path | None = None):
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: Path | None = None):
    conn = _connect(path)
    try:
        conn.executescript(_SCHEMA_SQL)
        # Migraciones idempotentes para DBs creadas con schema anterior:
        for ddl in ("ALTER TABLE documents ADD COLUMN metadata TEXT",):
            try:
                conn.execute(ddl)
            except Exception as e:
                if "duplicate column" not in str(e).lower():
                    raise
        conn.commit()
    finally:
        conn.close()
