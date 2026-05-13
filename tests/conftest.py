"""
Shared pytest fixtures for notability-extractor tests.

All fixtures create temporary, in-memory or tmp-path SQLite databases so tests
never touch a real Notability installation.
"""

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return a path to a minimal SQLite DB that mimics a Notability schema."""
    db = tmp_path / "Notability.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE ZFLASHCARD (
            Z_PK      INTEGER PRIMARY KEY,
            ZTERM     TEXT,
            ZDEFINITION TEXT,
            ZSTUDYSET INTEGER
        );
        CREATE TABLE ZSTUDYSET (
            Z_PK  INTEGER PRIMARY KEY,
            ZNAME TEXT
        );
        CREATE TABLE ZNOTE (
            Z_PK    INTEGER PRIMARY KEY,
            ZTITLE  TEXT,
            ZDATA   BLOB
        );
        INSERT INTO ZSTUDYSET VALUES (1, 'Biology Ch.1');
        INSERT INTO ZFLASHCARD VALUES (1, 'Mitosis', 'Cell division producing two identical daughter cells', 1);
        INSERT INTO ZFLASHCARD VALUES (2, 'Meiosis', 'Cell division producing four genetically unique cells', 1);
        INSERT INTO ZFLASHCARD VALUES (3, 'ATP', 'Adenosine triphosphate -- the energy currency of cells', 1);
        INSERT INTO ZNOTE VALUES (1, 'Lecture 1', NULL);
        """)
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def tmp_db_with_blobs(tmp_path: Path) -> Path:
    """DB where a flashcard column contains a non-UTF-8 binary blob."""
    db = tmp_path / "Notability_blob.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE ZFLASHCARD (Z_PK INTEGER PRIMARY KEY, ZTERM TEXT, ZDEFINITION BLOB)")
    # Insert a valid text term but a binary (non-UTF-8) definition blob
    conn.execute(
        "INSERT INTO ZFLASHCARD VALUES (?, ?, ?)",
        (1, "Entropy", bytes([0x80, 0x81, 0x82])),
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def sample_cards() -> list[dict]:
    """A small list of well-formed front/back card dicts."""
    return [
        {"front": "What is ATP?", "back": "The energy currency of cells"},
        {"front": "Define mitosis", "back": "Cell division producing two identical daughter cells"},
        {"front": "What is entropy?", "back": "A measure of disorder in a system"},
    ]
