"""Tests for archive.filter (pure functions, no I/O)."""

from datetime import UTC, datetime

from notability_extractor.archive import filter as flt
from notability_extractor.model import ArchivedCard, Card


def _ac(q: str, tags: list[str], id_: str) -> ArchivedCard:
    card = Card(
        question=q,
        options={"A": "alpha", "B": "beta", "C": "gamma", "D": "delta"},
        correct_answer="A",
        source_file="x",
        index=1,
        tags=tags,
    )
    now = datetime(2026, 5, 15, tzinfo=UTC)
    return ArchivedCard(card=card, id=id_, created_at=now, updated_at=now)


def test_by_tags_any_returns_cards_with_any_match():
    cards = [
        _ac("Q1", ["biology"], "a"),
        _ac("Q2", ["chemistry"], "b"),
        _ac("Q3", ["biology", "midterm"], "c"),
        _ac("Q4", [], "d"),
    ]
    result = flt.by_tags(cards, ["biology"], mode="any")
    assert {c.id for c in result} == {"a", "c"}


def test_by_tags_all_requires_every_tag():
    cards = [
        _ac("Q1", ["biology"], "a"),
        _ac("Q2", ["biology", "midterm"], "b"),
        _ac("Q3", ["biology", "midterm", "review"], "c"),
    ]
    result = flt.by_tags(cards, ["biology", "midterm"], mode="all")
    assert {c.id for c in result} == {"b", "c"}


def test_by_tags_empty_query_returns_all():
    cards = [_ac("Q1", ["bio"], "a"), _ac("Q2", [], "b")]
    assert len(flt.by_tags(cards, [], mode="any")) == 2


def test_by_text_matches_question_case_insensitive():
    cards = [_ac("Capital of France?", [], "a"), _ac("Photosynthesis", [], "b")]
    result = flt.by_text(cards, "FRANCE")
    assert [c.id for c in result] == ["a"]


def test_by_text_matches_option_text():
    cards = [_ac("Q?", [], "a")]
    assert flt.by_text(cards, "gamma") == cards


def test_by_text_empty_query_returns_all():
    cards = [_ac("Q1", [], "a"), _ac("Q2", [], "b")]
    assert flt.by_text(cards, "") == cards


def test_all_tags_deduped_and_sorted():
    cards = [
        _ac("Q1", ["chemistry", "biology"], "a"),
        _ac("Q2", ["biology"], "b"),
        _ac("Q3", ["physics"], "c"),
    ]
    assert flt.all_tags(cards) == ["biology", "chemistry", "physics"]
