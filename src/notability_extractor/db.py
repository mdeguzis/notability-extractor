"""SQLite helpers: open, introspect, and sample a Notability database."""

import sqlite3
from pathlib import Path
from typing import Any

from notability_extractor.utils import get_logger

log = get_logger(__name__)

# Table-name fragments that suggest flashcard / study content.
FLASHCARD_TABLE_HINTS: list[str] = [
    "flashcard",
    "studyset",
    "learnitem",
    "card",
    "quiz",
    "term",
    "definition",
]


def open_db(path: Path) -> sqlite3.Connection:
    """Open *path* read-only and configure Row factory."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    log.debug("Opened DB (read-only): %s", path)
    return conn


def list_tables(conn: sqlite3.Connection) -> list[str]:
    """Return all user table names sorted alphabetically."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = [r["name"] for r in rows]
    log.debug("Tables in DB (%d): %s", len(names), names)
    return names


def describe_table(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    """Return PRAGMA table_info rows as plain dicts."""
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return [dict(r) for r in rows]


def sample_rows(conn: sqlite3.Connection, table: str, limit: int = 5) -> list[sqlite3.Row]:
    """Fetch up to *limit* rows from *table* for inspection."""
    return conn.execute(f"SELECT * FROM '{table}' LIMIT {limit}").fetchall()


def find_flashcard_tables(tables: list[str]) -> list[str]:
    """
    Filter *tables* to those whose names match a flashcard-related hint.

    The match is case-insensitive substring search against FLASHCARD_TABLE_HINTS.
    """
    matches = [t for t in tables if any(hint in t.lower() for hint in FLASHCARD_TABLE_HINTS)]
    log.debug("Flashcard-candidate tables: %s  (hints: %s)", matches, FLASHCARD_TABLE_HINTS)
    return matches


def print_schema(conn: sqlite3.Connection, tables: list[str]) -> None:
    """Pretty-print every table with its column list (used by --list-tables)."""
    for table in tables:
        cols = describe_table(conn, table)
        col_str = ", ".join(c["name"] for c in cols)
        print(f"  {table}  ({col_str})")
