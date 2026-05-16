"""Tests for notability_extractor.model dataclasses."""

import hashlib
from datetime import UTC, datetime

from notability_extractor.model import ArchivedCard, Card, Deck, NoteText, Summary


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


def test_card_defaults_to_empty_tags():
    c = Card(
        question="Q?",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_answer="B",
        source_file="quiz_1.json",
        index=1,
    )
    assert not c.tags


def test_card_accepts_tags():
    c = Card(
        question="Q?",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_answer="B",
        source_file="quiz_1.json",
        index=1,
        tags=["biology", "midterm"],
    )
    assert c.tags == ["biology", "midterm"]


def test_card_stable_id_is_md5_of_question_plus_correct_text():
    c = Card(
        question="Capital of France?",
        options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Rome"},
        correct_answer="B",
        source_file="quiz_1.json",
        index=1,
    )
    expected = hashlib.md5(b"Capital of France?|Paris").hexdigest()
    assert c.stable_id == expected


def test_card_stable_id_changes_when_question_changes():
    base = {
        "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
        "correct_answer": "B",
        "source_file": "quiz_1.json",
        "index": 1,
    }
    c1 = Card(question="Q1?", **base)
    c2 = Card(question="Q2?", **base)
    assert c1.stable_id != c2.stable_id


def test_archived_card_holds_card_plus_metadata():
    card = Card(
        question="Q?",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_answer="A",
        source_file="quiz_1.json",
        index=1,
    )
    now = datetime(2026, 5, 15, tzinfo=UTC)
    a = ArchivedCard(card=card, id="abc123", created_at=now, updated_at=now)
    assert a.card is card
    assert a.id == "abc123"
    assert a.created_at == now
    assert a.updated_at == now


def test_archived_card_id_stays_stable_when_underlying_card_changes():
    """The whole reason ArchivedCard.id and Card.stable_id are separate:
    when the user edits a card's question, the new Card.stable_id changes
    but the archive's stored `id` does not. Edit history survives typo fixes.
    """
    original = Card(
        question="Original?",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_answer="A",
        source_file="x",
        index=1,
    )
    locked_id = original.stable_id
    now = datetime(2026, 5, 15, tzinfo=UTC)
    archived = ArchivedCard(card=original, id=locked_id, created_at=now, updated_at=now)

    edited = Card(
        question="Edited?",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_answer="A",
        source_file="x",
        index=1,
    )
    # the underlying Card stable_id changes after edit
    assert edited.stable_id != locked_id
    # but a fresh ArchivedCard would still use the original locked id
    rearchived = ArchivedCard(card=edited, id=archived.id, created_at=now, updated_at=now)
    assert rearchived.id == locked_id
    assert rearchived.id != rearchived.card.stable_id


def test_card_stable_id_uses_empty_string_when_correct_answer_missing():
    """Documents the silent fallback: if correct_answer points to a key not in
    options, stable_id hashes question + '|' + '' rather than raising. Upstream
    validation should prevent this state, but stable_id stays total."""
    c = Card(
        question="Q?",
        options={"A": "a", "B": "b"},  # no "Z" key
        correct_answer="Z",
        source_file="x",
        index=1,
    )
    expected = hashlib.md5(b"Q?|", usedforsecurity=False).hexdigest()
    assert c.stable_id == expected
