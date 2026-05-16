"""Tests for build.notes."""

import json
from pathlib import Path

from notability_extractor.build import notes
from notability_extractor.model import NoteText


def test_write_json_lists_each_note(tmp_path: Path):
    out = tmp_path / "notes.json"
    notes.write_json([
        NoteText(name="N1", body="body1", source_file="N1.txt"),
        NoteText(name="N2", body="body2", source_file="N2.txt"),
    ], out)
    data = json.loads(out.read_text())
    assert len(data["notes"]) == 2
    assert data["notes"][0]["name"] == "N1"


def test_write_md_uses_note_name_as_h2(tmp_path: Path):
    out = tmp_path / "notes.md"
    notes.write_md([NoteText(name="My Note", body="hello", source_file="My Note.txt")], out)
    body = out.read_text()
    assert "## My Note" in body
    assert "hello" in body
