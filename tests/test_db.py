"""Tests for notability_extractor.db."""

import sqlite3
from pathlib import Path

import pytest

from notability_extractor.db import (
    FLASHCARD_TABLE_HINTS,
    describe_table,
    find_flashcard_tables,
    list_tables,
    open_db,
    sample_rows,
)


class TestOpenDb:
    def test_opens_valid_sqlite(self, tmp_db: Path):
        conn = open_db(tmp_db)
        assert conn is not None
        conn.close()

    def test_row_factory_set(self, tmp_db: Path):
        conn = open_db(tmp_db)
        row = conn.execute("SELECT * FROM ZFLASHCARD LIMIT 1").fetchone()
        assert row is not None
        # sqlite3.Row supports column-name access
        assert row["ZTERM"] is not None
        conn.close()

    def test_raises_on_missing_file(self, tmp_path: Path):
        # sqlite3 raises OperationalError when read-only mode hits a missing file
        with pytest.raises(sqlite3.OperationalError):
            open_db(tmp_path / "missing.sqlite")


class TestListTables:
    def test_returns_all_tables(self, tmp_db: Path):
        conn = open_db(tmp_db)
        tables = list_tables(conn)
        conn.close()
        assert "ZFLASHCARD" in tables
        assert "ZSTUDYSET" in tables
        assert "ZNOTE" in tables

    def test_sorted_alphabetically(self, tmp_db: Path):
        conn = open_db(tmp_db)
        tables = list_tables(conn)
        conn.close()
        assert tables == sorted(tables)


class TestDescribeTable:
    def test_returns_column_info(self, tmp_db: Path):
        conn = open_db(tmp_db)
        cols = describe_table(conn, "ZFLASHCARD")
        conn.close()
        names = [c["name"] for c in cols]
        assert "ZTERM" in names
        assert "ZDEFINITION" in names

    def test_empty_for_nonexistent_table(self, tmp_db: Path):
        conn = open_db(tmp_db)
        cols = describe_table(conn, "NONEXISTENT")
        conn.close()
        assert cols == []


class TestSampleRows:
    def test_returns_up_to_limit(self, tmp_db: Path):
        conn = open_db(tmp_db)
        rows = sample_rows(conn, "ZFLASHCARD", limit=2)
        conn.close()
        assert len(rows) <= 2

    def test_returns_all_when_table_smaller_than_limit(self, tmp_db: Path):
        conn = open_db(tmp_db)
        rows = sample_rows(conn, "ZSTUDYSET", limit=100)
        conn.close()
        assert len(rows) == 1


class TestFindFlashcardTables:
    def test_detects_flashcard_table(self):
        tables = ["ZNOTE", "ZFLASHCARD", "ZSTUDYSET", "ZUNRELATED"]
        result = find_flashcard_tables(tables)
        assert "ZFLASHCARD" in result
        assert "ZSTUDYSET" in result
        assert "ZNOTE" not in result
        assert "ZUNRELATED" not in result

    def test_case_insensitive(self):
        tables = ["Flashcard", "StudySet", "Note"]
        result = find_flashcard_tables(tables)
        assert "Flashcard" in result
        assert "StudySet" in result

    def test_empty_input(self):
        assert find_flashcard_tables([]) == []

    def test_no_matches(self):
        assert find_flashcard_tables(["ZNOTE", "ZUSER", "ZCONFIG"]) == []

    def test_hints_list_is_nonempty(self):
        assert len(FLASHCARD_TABLE_HINTS) > 0
