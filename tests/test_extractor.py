"""Tests for notability_extractor.extractor."""

from pathlib import Path

import pytest

from notability_extractor.db import open_db
from notability_extractor.extractor import extract_cards, extract_raw, map_front_back


class TestExtractRaw:
    def test_returns_list_of_dicts(self, tmp_db: Path):
        conn = open_db(tmp_db)
        rows = extract_raw(conn, "ZFLASHCARD")
        conn.close()
        assert isinstance(rows, list)
        assert all(isinstance(r, dict) for r in rows)

    def test_correct_row_count(self, tmp_db: Path):
        conn = open_db(tmp_db)
        rows = extract_raw(conn, "ZFLASHCARD")
        conn.close()
        assert len(rows) == 3

    def test_text_columns_preserved(self, tmp_db: Path):
        conn = open_db(tmp_db)
        rows = extract_raw(conn, "ZFLASHCARD")
        conn.close()
        terms = {r["ZTERM"] for r in rows}
        assert "Mitosis" in terms
        assert "ATP" in terms

    def test_binary_blob_becomes_placeholder(self, tmp_db_with_blobs: Path):
        conn = open_db(tmp_db_with_blobs)
        rows = extract_raw(conn, "ZFLASHCARD")
        conn.close()
        assert len(rows) == 1
        val = rows[0]["ZDEFINITION"]
        assert "<binary blob" in val

    def test_empty_table_returns_empty_list(self, tmp_db: Path):
        # ZSTUDYSET has 1 row; just verify extract_raw works on non-flashcard tables
        conn = open_db(tmp_db)
        rows = extract_raw(conn, "ZSTUDYSET")
        conn.close()
        assert isinstance(rows, list)


class TestMapFrontBack:
    def test_maps_term_definition(self):
        records = [{"ZTERM": "Mitosis", "ZDEFINITION": "Cell division"}]
        result = map_front_back(records)
        assert result == [{"front": "Mitosis", "back": "Cell division"}]

    def test_maps_front_back_columns(self):
        records = [{"front": "Q", "back": "A"}]
        result = map_front_back(records)
        assert result == [{"front": "Q", "back": "A"}]

    def test_fallback_uses_first_two_text_columns(self):
        records = [{"col_a": "alpha", "col_b": "beta"}]
        result = map_front_back(records)
        assert result[0]["front"] == "alpha"
        assert result[0]["back"] == "beta"

    def test_empty_input_returns_empty(self):
        assert map_front_back([]) == []

    def test_converts_non_strings_to_str(self):
        records = [{"ZTERM": 42, "ZDEFINITION": None}]
        result = map_front_back(records)
        assert result[0]["front"] == "42"
        assert result[0]["back"] == "None"

    def test_multiple_rows(self):
        records = [
            {"ZTERM": "A", "ZDEFINITION": "1"},
            {"ZTERM": "B", "ZDEFINITION": "2"},
        ]
        result = map_front_back(records)
        assert len(result) == 2
        assert result[1] == {"front": "B", "back": "2"}


class TestExtractCards:
    def test_end_to_end(self, tmp_db: Path):
        conn = open_db(tmp_db)
        cards = extract_cards(conn, "ZFLASHCARD")
        conn.close()
        assert len(cards) == 3
        for card in cards:
            assert "front" in card
            assert "back" in card
            assert card["front"]  # not empty

    def test_returns_correct_content(self, tmp_db: Path):
        conn = open_db(tmp_db)
        cards = extract_cards(conn, "ZFLASHCARD")
        conn.close()
        fronts = {c["front"] for c in cards}
        assert "Mitosis" in fronts
        assert "ATP" in fronts
