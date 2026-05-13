"""Tests for notability_extractor.anki."""

import sqlite3
import zipfile
from pathlib import Path

import pytest

from notability_extractor.anki import write_apkg


class TestWriteApkg:
    def test_creates_file(self, sample_cards: list[dict], tmp_path: Path):
        out = tmp_path / "test.apkg"
        write_apkg(sample_cards, "Test Deck", out)
        assert out.exists()

    def test_is_valid_zip(self, sample_cards: list[dict], tmp_path: Path):
        out = tmp_path / "test.apkg"
        write_apkg(sample_cards, "Test Deck", out)
        assert zipfile.is_zipfile(str(out))

    def test_contains_collection_and_media(self, sample_cards: list[dict], tmp_path: Path):
        out = tmp_path / "test.apkg"
        write_apkg(sample_cards, "Test Deck", out)
        with zipfile.ZipFile(str(out)) as zf:
            names = zf.namelist()
        assert "collection.anki2" in names
        assert "media" in names

    def test_collection_is_valid_sqlite(self, sample_cards: list[dict], tmp_path: Path):
        out = tmp_path / "test.apkg"
        write_apkg(sample_cards, "Test Deck", out)
        with zipfile.ZipFile(str(out)) as zf:
            data = zf.read("collection.anki2")
        db_path = tmp_path / "collection.anki2"
        db_path.write_bytes(data)
        conn = sqlite3.connect(str(db_path))
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        conn.close()
        assert {"cards", "notes", "col"}.issubset(tables)

    def test_note_count_matches_input(self, sample_cards: list[dict], tmp_path: Path):
        out = tmp_path / "test.apkg"
        write_apkg(sample_cards, "Test Deck", out)
        with zipfile.ZipFile(str(out)) as zf:
            data = zf.read("collection.anki2")
        db_path = tmp_path / "collection.anki2"
        db_path.write_bytes(data)
        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        conn.close()
        assert count == len(sample_cards)

    def test_front_back_in_flds(self, tmp_path: Path):
        cards = [{"front": "Hello", "back": "World"}]
        out = tmp_path / "test.apkg"
        write_apkg(cards, "Test Deck", out)
        with zipfile.ZipFile(str(out)) as zf:
            data = zf.read("collection.anki2")
        db_path = tmp_path / "collection.anki2"
        db_path.write_bytes(data)
        conn = sqlite3.connect(str(db_path))
        flds = conn.execute("SELECT flds FROM notes LIMIT 1").fetchone()[0]
        conn.close()
        assert "Hello" in flds
        assert "World" in flds

    def test_raises_on_empty_cards(self, tmp_path: Path):
        with pytest.raises(ValueError, match="empty"):
            write_apkg([], "Empty Deck", tmp_path / "out.apkg")

    def test_creates_parent_dirs(self, sample_cards: list[dict], tmp_path: Path):
        out = tmp_path / "nested" / "deep" / "test.apkg"
        write_apkg(sample_cards, "Test Deck", out)
        assert out.exists()

    def test_deck_name_stored_in_collection(self, sample_cards: list[dict], tmp_path: Path):
        out = tmp_path / "test.apkg"
        write_apkg(sample_cards, "My Custom Deck", out)
        with zipfile.ZipFile(str(out)) as zf:
            data = zf.read("collection.anki2")
        db_path = tmp_path / "collection.anki2"
        db_path.write_bytes(data)
        conn = sqlite3.connect(str(db_path))
        decks_json = conn.execute("SELECT decks FROM col").fetchone()[0]
        conn.close()
        assert "My Custom Deck" in decks_json
