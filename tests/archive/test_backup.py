"""Tests for archive.backup."""

import json as _json
from pathlib import Path

import pytest
from freezegun import freeze_time

from notability_extractor.archive import backup, store
from notability_extractor.model import Card


def _seed(archive: Path, q: str = "Q?") -> None:
    store.save_all([], archive)
    store.add(
        Card(
            question=q,
            options={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct_answer="A",
            source_file="x",
            index=1,
        ),
        archive,
    )


# --- snapshot + prune ---


def test_snapshot_writes_a_copy_with_timestamp(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    backups = tmp_path / "backups"
    _seed(archive)
    with freeze_time("2026-05-15 18:14:23", tz_offset=0):
        out = backup.snapshot(archive, backups)
    assert out is not None
    assert out.name == "cards-20260515-181423.jsonl"
    assert out.exists()
    assert out.read_text() == archive.read_text()


def test_snapshot_returns_none_when_archive_unchanged(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    backups = tmp_path / "backups"
    _seed(archive)
    with freeze_time("2026-05-15 18:14:23"):
        first = backup.snapshot(archive, backups)
    assert first is not None
    with freeze_time("2026-05-15 18:14:24"):
        second = backup.snapshot(archive, backups)
    assert second is None


def test_snapshot_runs_again_when_archive_changes(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    backups = tmp_path / "backups"
    _seed(archive, "Q1?")
    with freeze_time("2026-05-15 18:14:23"):
        first = backup.snapshot(archive, backups)
    _seed(archive, "Q2?")
    with freeze_time("2026-05-15 18:14:24"):
        second = backup.snapshot(archive, backups)
    assert second is not None
    assert second != first


def test_list_snapshots_returns_sorted_newest_first(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    backups = tmp_path / "backups"
    for i, t in enumerate(["2026-05-15 09:00", "2026-05-15 10:00", "2026-05-15 11:00"]):
        _seed(archive, f"Q{i}?")
        with freeze_time(t):
            backup.snapshot(archive, backups)
    snaps = backup.list_snapshots(backups)
    assert [s.path.name for s in snaps] == [
        "cards-20260515-110000.jsonl",
        "cards-20260515-100000.jsonl",
        "cards-20260515-090000.jsonl",
    ]


def test_prune_keeps_last_n(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    backups = tmp_path / "backups"
    for i, t in enumerate([f"2026-05-15 0{h}:00" for h in range(8)]):
        _seed(archive, f"Q{i}?")
        with freeze_time(t):
            backup.snapshot(archive, backups)
    deleted = backup.prune(backups, keep=3)
    assert deleted == 5
    remaining = sorted(p.name for p in backups.glob("*.jsonl"))
    assert len(remaining) == 3


def test_prune_handles_count_less_than_keep(tmp_path: Path):
    backups = tmp_path / "backups"
    backups.mkdir()
    assert backup.prune(backups, keep=10) == 0


# --- restore ---


def test_restore_replaces_archive_with_snapshot_contents(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    backups = tmp_path / "backups"

    _seed(archive, "Q-original?")
    with freeze_time("2026-05-15 09:00"):
        old_snap = backup.snapshot(archive, backups)
    assert old_snap is not None
    snap_text = old_snap.read_text()

    _seed(archive, "Q-current?")
    backup.restore_snapshot(old_snap.name, archive_path=archive, backups_dir=backups)

    assert archive.read_text() == snap_text


def test_restore_creates_pre_restore_snapshot_first(tmp_path: Path):
    """Critical safety invariant: restore is undo-able."""
    archive = tmp_path / "cards.jsonl"
    backups = tmp_path / "backups"

    _seed(archive, "Q-original?")
    with freeze_time("2026-05-15 09:00"):
        old_snap = backup.snapshot(archive, backups)
    assert old_snap is not None

    _seed(archive, "Q-current?")
    pre_text = archive.read_text()

    with freeze_time("2026-05-15 10:00"):
        backup.restore_snapshot(old_snap.name, archive_path=archive, backups_dir=backups)

    pre_restore = backups / "cards-20260515-100000.jsonl"
    assert pre_restore.exists()
    assert pre_restore.read_text() == pre_text


def test_restore_raises_on_missing_snapshot(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    backups = tmp_path / "backups"
    backups.mkdir()
    with pytest.raises(FileNotFoundError):
        backup.restore_snapshot(
            "cards-20260515-090000.jsonl", archive_path=archive, backups_dir=backups
        )


# --- export + import ---


def test_export_jsonl_byte_for_byte_copy(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    target = tmp_path / "exported.jsonl"
    _seed(archive)
    backup.export_archive(target, fmt="jsonl", archive_path=archive)
    assert target.read_text() == archive.read_text()


def test_export_json_pretty_array_form(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    target = tmp_path / "exported.json"
    _seed(archive)
    backup.export_archive(target, fmt="json", archive_path=archive)
    data = _json.loads(target.read_text())
    assert isinstance(data["cards"], list)
    assert len(data["cards"]) == 1


def test_import_merge_adds_new_cards_only(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    source = tmp_path / "incoming.jsonl"
    _seed(archive, "Q1?")
    backup.export_archive(source, fmt="jsonl", archive_path=archive)

    # add second card, then re-import the source (which only has Q1?)
    store.add(
        Card(
            question="Q2?",
            options={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct_answer="A",
            source_file="x",
            index=1,
        ),
        archive,
    )

    added, skipped = backup.import_archive(source, mode="merge", archive_path=archive)
    assert added == 0
    assert skipped >= 1
    assert len(store.load(archive)) == 2


def test_import_replace_overwrites_archive(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    source = tmp_path / "incoming.jsonl"
    _seed(archive, "Q-original?")
    backup.export_archive(source, fmt="jsonl", archive_path=archive)

    archive.unlink()
    _seed(archive, "Q-changed?")
    assert "Q-changed?" in archive.read_text()

    backup.import_archive(source, mode="replace", archive_path=archive)
    assert "Q-original?" in archive.read_text()
    assert "Q-changed?" not in archive.read_text()
