"""Tests for notability_extractor.build.reader against the real fixture."""

from pathlib import Path

import pytest

from notability_extractor.build.reader import read_input_dir

FIXTURE = Path.home() / "notability-test-data" / "notability_export"


@pytest.mark.skipif(not FIXTURE.is_dir(), reason="test fixture not on this machine")
class TestReadExportDir:
    def test_returns_18_cards(self):
        deck = read_input_dir(FIXTURE)
        assert len(deck.cards) == 18

    def test_returns_3_summaries(self):
        deck = read_input_dir(FIXTURE)
        assert len(deck.summaries) == 3

    def test_returns_15_notes(self):
        deck = read_input_dir(FIXTURE)
        assert len(deck.notes) == 15

    def test_card_has_correct_shape(self):
        deck = read_input_dir(FIXTURE)
        c = deck.cards[0]
        assert c.question
        assert set(c.options.keys()) == {"A", "B", "C", "D"}
        assert c.correct_answer in {"A", "B", "C", "D"}
        assert c.index == 1
        assert c.source_file == "quiz_1.json"

    def test_deck_name_defaults(self):
        deck = read_input_dir(FIXTURE)
        assert deck.name == "Notability Flashcards"

    def test_deck_name_override(self):
        deck = read_input_dir(FIXTURE, deck_name="Custom")
        assert deck.name == "Custom"


def test_missing_subdirs_produce_empty_lists(tmp_path: Path):
    # tmp_path has no learn/, no .txt files - reader returns empty deck
    deck = read_input_dir(tmp_path)
    assert not deck.cards
    assert not deck.summaries
    assert not deck.notes
