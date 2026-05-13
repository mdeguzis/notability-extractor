"""Tests for notability_extractor.note_parser."""

import plistlib
import zipfile
from pathlib import Path

import pytest

from notability_extractor.note_parser import (
    extract_cards_from_notes,
    find_note_files,
    parse_note_file,
)


def _make_note_file(path: Path, plists: dict[str, object]) -> Path:
    """Helper: write a .note ZIP with the given plist member files."""
    with zipfile.ZipFile(str(path), "w") as zf:
        for member_name, data in plists.items():
            zf.writestr(member_name, plistlib.dumps(data, fmt=plistlib.FMT_XML))
    return path


class TestFindNoteFiles:
    def test_finds_note_files(self, tmp_path: Path):
        (tmp_path / "note1.note").touch()
        (tmp_path / "note2.note").touch()
        (tmp_path / "other.txt").touch()
        result = find_note_files(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".note" for p in result)

    def test_searches_recursively(self, tmp_path: Path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "deep.note").touch()
        result = find_note_files(tmp_path)
        assert len(result) == 1

    def test_returns_empty_for_missing_dir(self, tmp_path: Path):
        result = find_note_files(tmp_path / "nonexistent")
        assert result == []

    def test_returns_empty_when_no_note_files(self, tmp_path: Path):
        (tmp_path / "file.txt").touch()
        assert find_note_files(tmp_path) == []


class TestParseNoteFile:
    def test_parses_metadata_plist(self, tmp_path: Path):
        note = tmp_path / "test.note"
        _make_note_file(note, {"metadata.plist": {"title": "Biology Notes", "mod": 12345}})
        result = parse_note_file(note)
        assert result["metadata"].get("title") == "Biology Notes"

    def test_surfaces_flashcard_keys(self, tmp_path: Path):
        note = tmp_path / "test.note"
        _make_note_file(
            note,
            {
                "Session.plist": [
                    {"term": "Mitosis", "definition": "Cell division"}
                ]
            },
        )
        result = parse_note_file(note)
        assert len(result["flashcards"]) >= 1
        assert any("term" in fc for fc in result["flashcards"])

    def test_lists_raw_members(self, tmp_path: Path):
        note = tmp_path / "test.note"
        _make_note_file(note, {"metadata.plist": {}, "Session.plist": {}})
        result = parse_note_file(note)
        assert "metadata.plist" in result["raw_members"]
        assert "Session.plist" in result["raw_members"]

    def test_handles_non_zip_gracefully(self, tmp_path: Path):
        note = tmp_path / "broken.note"
        note.write_bytes(b"this is not a zip file")
        result = parse_note_file(note)
        assert result["flashcards"] == []
        assert result["metadata"] == {}

    def test_returns_path_in_result(self, tmp_path: Path):
        note = tmp_path / "test.note"
        _make_note_file(note, {"metadata.plist": {}})
        result = parse_note_file(note)
        assert result["path"] == note


class TestExtractCardsFromNotes:
    def test_extracts_term_definition(self, tmp_path: Path):
        note = tmp_path / "test.note"
        _make_note_file(
            note,
            {"Session.plist": [{"term": "ATP", "definition": "Energy currency"}]},
        )
        cards = extract_cards_from_notes([note])
        assert len(cards) == 1
        assert cards[0]["front"] == "ATP"
        assert cards[0]["back"] == "Energy currency"

    def test_skips_empty_candidates(self, tmp_path: Path):
        note = tmp_path / "test.note"
        _make_note_file(note, {"metadata.plist": {"title": "Notes"}})
        cards = extract_cards_from_notes([note])
        assert cards == []

    def test_handles_multiple_note_files(self, tmp_path: Path):
        for i, (term, defn) in enumerate([("A", "1"), ("B", "2")]):
            note = tmp_path / f"note{i}.note"
            _make_note_file(note, {"Session.plist": [{"term": term, "definition": defn}]})
        notes = list(tmp_path.glob("*.note"))
        cards = extract_cards_from_notes(notes)
        assert len(cards) == 2

    def test_empty_input(self):
        assert extract_cards_from_notes([]) == []
