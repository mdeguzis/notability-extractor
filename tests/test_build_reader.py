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


def test_auto_descends_when_pointed_one_level_too_shallow(tmp_path: Path):
    # simulate user pointing at the staging dir instead of the export subdir
    staging = tmp_path / "staging"
    staging.mkdir()
    # decoy non-export sibling
    (staging / "notability.sh").write_text("#!/usr/bin/env bash\n")
    # the real export subdir
    export = staging / "notability_export"
    (export / "learn" / "quizzes").mkdir(parents=True)
    (export / "Some Note.txt").write_text("hi")

    deck = read_input_dir(staging)
    assert len(deck.notes) == 1
    assert deck.notes[0].name == "Some Note"


def test_does_not_descend_when_already_export_shape(tmp_path: Path):
    # tmp_path itself looks like an export (has a *.txt), so don't descend
    (tmp_path / "note.txt").write_text("body")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "other.txt").write_text("body2")
    deck = read_input_dir(tmp_path)
    # picked up the top-level .txt, not the one inside subdir/
    assert len(deck.notes) == 1
    assert deck.notes[0].name == "note"
