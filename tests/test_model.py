"""Tests for notability_extractor.model dataclasses."""

from datetime import UTC, datetime

from notability_extractor.model import Card, Deck, NoteText, Summary


def test_card_holds_question_and_options():
    c = Card(
        question="Q?",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_answer="B",
        source_file="quiz_1.json",
        index=1,
    )
    assert c.question == "Q?"
    assert c.options["B"] == "b"
    assert c.correct_answer == "B"


def test_summary_holds_title_and_body():
    s = Summary(title="t", body="# t\nbody", source_file="summary_1.md")
    assert s.title == "t"
    assert s.body.endswith("body")


def test_note_text_holds_name_and_body():
    n = NoteText(name="My Note", body="hello", source_file="My Note.txt")
    assert n.name == "My Note"


def test_deck_assembles_all_three():
    d = Deck(
        name="Deck",
        generated_at=datetime(2026, 5, 13, tzinfo=UTC),
        cards=[],
        summaries=[],
        notes=[],
    )
    assert d.name == "Deck"
    assert not d.cards
