"""Tests for the three build writers (apkg, json, md)."""

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from notability_extractor.build.apkg_writer import write_apkg_deck
from notability_extractor.build.json_writer import write_json_deck
from notability_extractor.build.md_writer import write_md_deck
from notability_extractor.model import Card, Deck, NoteText, Summary


def _sample_deck() -> Deck:
    return Deck(
        name="Test Deck",
        generated_at=datetime(2026, 5, 13, 20, 30, tzinfo=UTC),
        cards=[
            Card(
                question="What is 2+2?",
                options={"A": "3", "B": "4", "C": "5", "D": "22"},
                correct_answer="B",
                source_file="quiz_1.json",
                index=1,
            ),
        ],
        summaries=[Summary(title="Math", body="# Math\nNumbers.", source_file="summary_1.md")],
        notes=[NoteText(name="My Note", body="OCR text here", source_file="My Note.txt")],
    )


def test_apkg_writer_writes_apkg_file(tmp_path: Path):
    out = tmp_path / "deck.apkg"
    write_apkg_deck(_sample_deck(), out)
    assert out.is_file()
    # .apkg is a ZIP archive
    assert zipfile.is_zipfile(out)


class TestJsonWriter:
    def test_writes_valid_json(self, tmp_path: Path):
        out = tmp_path / "deck.json"
        write_json_deck(_sample_deck(), out)
        data = json.loads(out.read_text())
        assert data["deck_name"] == "Test Deck"
        assert len(data["cards"]) == 1
        assert data["cards"][0]["correct_answer"] == "B"
        assert data["cards"][0]["correct_text"] == "4"
        assert len(data["summaries"]) == 1
        assert len(data["notes"]) == 1

    def test_includes_generated_at_iso(self, tmp_path: Path):
        out = tmp_path / "deck.json"
        write_json_deck(_sample_deck(), out)
        data = json.loads(out.read_text())
        assert "2026-05-13" in data["generated_at"]


class TestMdWriter:
    def test_contains_top_level_headings(self, tmp_path: Path):
        out = tmp_path / "deck.md"
        write_md_deck(_sample_deck(), out)
        content = out.read_text()
        assert "# Test Deck" in content
        assert "## Cards" in content
        assert "## Summaries" in content
        assert "## Note Transcripts" in content

    def test_renders_question_and_options(self, tmp_path: Path):
        out = tmp_path / "deck.md"
        write_md_deck(_sample_deck(), out)
        content = out.read_text()
        assert "What is 2+2?" in content
        assert "**A)** 3" in content
        assert "**B)** 4" in content
        assert "**Answer:** B - 4" in content
