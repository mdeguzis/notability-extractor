"""Tests for archive.store."""

import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from notability_extractor.archive import store
from notability_extractor.model import ArchivedCard, Card


def _make_card(q: str = "Q?", tags: list[str] | None = None) -> Card:
    return Card(
        question=q,
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_answer="B",
        source_file="quiz_1.json",
        index=1,
        tags=tags or [],
    )


def _make_archived(card: Card, id_: str = "id1") -> ArchivedCard:
    now = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
    return ArchivedCard(card=card, id=id_, created_at=now, updated_at=now)


def test_load_returns_empty_when_archive_missing(tmp_path: Path):
    assert not store.load(tmp_path / "cards.jsonl")


def test_save_all_then_load_round_trips(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    cards = [
        _make_archived(_make_card("Q1?", tags=["bio"]), id_="aaa"),
        _make_archived(_make_card("Q2?"), id_="bbb"),
    ]
    store.save_all(cards, archive)
    loaded = store.load(archive)
    assert len(loaded) == 2
    assert loaded[0].id == "aaa"
    assert loaded[0].card.question == "Q1?"
    assert loaded[0].card.tags == ["bio"]


def test_save_all_writes_one_object_per_line(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    store.save_all(
        [
            _make_archived(_make_card("Q1?"), id_="aaa"),
            _make_archived(_make_card("Q2?"), id_="bbb"),
        ],
        archive,
    )
    lines = archive.read_text().splitlines()
    assert len(lines) == 2


def test_save_all_sorts_by_id_for_stable_diffs(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    store.save_all(
        [
            _make_archived(_make_card("Q2?"), id_="bbb"),
            _make_archived(_make_card("Q1?"), id_="aaa"),
        ],
        archive,
    )
    loaded = store.load(archive)
    assert [c.id for c in loaded] == ["aaa", "bbb"]


def test_load_skips_corrupt_line_with_warning(tmp_path: Path, caplog):
    archive = tmp_path / "cards.jsonl"
    archive.write_text(
        '{"id":"aaa","created_at":"2026-05-15T12:00:00+00:00","updated_at":"2026-05-15T12:00:00+00:00",'
        '"question":"Q1?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct_answer":"B",'
        '"source_file":"x","index":1,"tags":[]}\n'
        "{not valid json\n"
        '{"id":"ccc","created_at":"2026-05-15T12:00:00+00:00","updated_at":"2026-05-15T12:00:00+00:00",'
        '"question":"Q3?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct_answer":"A",'
        '"source_file":"x","index":3,"tags":[]}\n'
    )
    with caplog.at_level(logging.WARNING):
        loaded = store.load(archive)
    assert [c.id for c in loaded] == ["aaa", "ccc"]
    assert "Skipping corrupt line" in caplog.text


def test_load_tolerates_missing_tags_field(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    archive.write_text(
        '{"id":"aaa","created_at":"2026-05-15T12:00:00+00:00","updated_at":"2026-05-15T12:00:00+00:00",'
        '"question":"Q1?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct_answer":"B",'
        '"source_file":"x","index":1}\n'
    )
    loaded = store.load(archive)
    assert loaded[0].card.tags == []


def test_load_tolerates_missing_updated_at(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    archive.write_text(
        '{"id":"aaa","created_at":"2026-05-15T12:00:00+00:00",'
        '"question":"Q1?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct_answer":"B",'
        '"source_file":"x","index":1,"tags":[]}\n'
    )
    loaded = store.load(archive)
    assert loaded[0].updated_at == loaded[0].created_at


def test_save_all_atomic_via_tmpfile(tmp_path: Path, monkeypatch):
    archive = tmp_path / "cards.jsonl"
    archive.write_text("original\n")
    original = archive.read_text()

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("os.replace", boom)
    with pytest.raises(OSError):
        store.save_all([_make_archived(_make_card())], archive)
    assert archive.read_text() == original


def test_add_appends_new_card(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    c = _make_card("Q1?")
    archived = store.add(c, archive)
    assert archived.id == c.stable_id
    assert archived.card == c
    loaded = store.load(archive)
    assert len(loaded) == 1


def test_add_to_existing_archive_preserves_existing(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    store.save_all([_make_archived(_make_card("Q1?"), id_="aaa")], archive)
    store.add(_make_card("Q2?"), archive)
    loaded = store.load(archive)
    assert len(loaded) == 2


def test_update_replaces_card_keeps_id_and_created_at(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    original = _make_archived(_make_card("Q1?"), id_="aaa")
    store.save_all([original], archive)

    new_card = _make_card("Q1 fixed?", tags=["edited"])
    updated = store.update("aaa", new_card, archive)

    assert updated.id == "aaa"
    assert updated.card.question == "Q1 fixed?"
    assert updated.created_at == original.created_at
    assert updated.updated_at >= original.updated_at


def test_update_raises_on_missing_id(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    store.save_all([_make_archived(_make_card("Q1?"), id_="aaa")], archive)
    with pytest.raises(KeyError):
        store.update("nope", _make_card("Q?"), archive)


def test_delete_removes_card(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    store.save_all(
        [
            _make_archived(_make_card("Q1?"), id_="aaa"),
            _make_archived(_make_card("Q2?"), id_="bbb"),
        ],
        archive,
    )
    store.delete("aaa", archive)
    loaded = store.load(archive)
    assert [c.id for c in loaded] == ["bbb"]


def test_delete_raises_on_missing_id(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    store.save_all([_make_archived(_make_card())], archive)
    with pytest.raises(KeyError):
        store.delete("nope", archive)


def test_concurrent_writes_dont_lose_data(tmp_path: Path):
    """Two threads adding simultaneously: both cards end up in the archive."""
    archive = tmp_path / "cards.jsonl"
    errors: list[Exception] = []

    def worker(q: str) -> None:
        try:
            store.add(_make_card(q), archive)
        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            errors.append(e)

    t1 = threading.Thread(target=worker, args=("Q1?",))
    t2 = threading.Thread(target=worker, args=("Q2?",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors
    loaded = store.load(archive)
    assert len(loaded) == 2


def test_merge_adds_new_cards_and_returns_count(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    added, skipped = store.merge([_make_card("Q1?"), _make_card("Q2?")], archive)
    assert (added, skipped) == (2, 0)
    assert len(store.load(archive)) == 2


def test_merge_skips_duplicates_by_stable_id(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    store.merge([_make_card("Q1?")], archive)
    added, skipped = store.merge([_make_card("Q1?"), _make_card("Q2?")], archive)
    assert (added, skipped) == (1, 1)
    assert len(store.load(archive)) == 2
