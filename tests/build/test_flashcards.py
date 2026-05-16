"""Tests for build.flashcards consuming list[ArchivedCard]."""

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from notability_extractor.build import flashcards
from notability_extractor.model import ArchivedCard, Card


def _ac(q: str, tags: list[str]) -> ArchivedCard:
    card = Card(
        question=q,
        options={"A": "alpha", "B": "beta", "C": "gamma", "D": "delta"},
        correct_answer="A",
        source_file="x",
        index=1,
        tags=tags,
    )
    now = datetime(2026, 5, 15, tzinfo=UTC)
    return ArchivedCard(card=card, id=q, created_at=now, updated_at=now)


def test_write_apkg_creates_valid_zip(tmp_path: Path):
    out = tmp_path / "out.apkg"
    flashcards.write_apkg([_ac("Q1?", ["biology"])], out, deck_name="Test Deck")
    assert out.is_file()
    assert zipfile.is_zipfile(out)


def test_write_apkg_passes_tags_through(tmp_path: Path):
    out = tmp_path / "tagged.apkg"
    flashcards.write_apkg([_ac("Q1?", ["biology", "midterm"])], out, deck_name="Tags Test")
    assert out.is_file()


def test_write_json_contains_cards_array(tmp_path: Path):
    out = tmp_path / "out.json"
    flashcards.write_json([_ac("Q1?", ["bio"])], out)
    data = json.loads(out.read_text())
    assert "cards" in data
    assert data["cards"][0]["question"] == "Q1?"
    assert data["cards"][0]["tags"] == ["bio"]


def test_write_md_renders_question_and_options(tmp_path: Path):
    out = tmp_path / "out.md"
    flashcards.write_md([_ac("Capital of France?", [])], out)
    body = out.read_text()
    assert "Capital of France?" in body
    assert "alpha" in body
    assert "**A**" in body
