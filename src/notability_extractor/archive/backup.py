"""Backup operations: snapshot, restore, export, import, prune."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from notability_extractor.archive.store import DEFAULT_ARCHIVE
from notability_extractor.archive.store import load as _load_archive
from notability_extractor.archive.store import merge as _merge_cards
from notability_extractor.archive.store import save_all as _save_all
from notability_extractor.model import Card
from notability_extractor.utils import get_logger

log = get_logger(__name__)

DEFAULT_BACKUPS = Path.home() / ".notability_extractor" / "backups"


@dataclass(frozen=True)
class Snapshot:
    path: Path
    timestamp: datetime


def snapshot(
    path: Path = DEFAULT_ARCHIVE,
    backups_dir: Path = DEFAULT_BACKUPS,
) -> Path | None:
    """Copy archive to backups_dir with timestamped filename.

    Returns None if (a) archive doesn't exist, (b) archive hash matches the most
    recent snapshot, or (c) the copy fails. Never raises -- a failed backup must
    not crash a save flow.
    """
    if not path.is_file():
        return None
    try:
        backups_dir.mkdir(parents=True, exist_ok=True)
        current_hash = _hash(path)
        latest = _latest_snapshot(backups_dir)
        if latest is not None and _hash(latest.path) == current_hash:
            return None
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        target = backups_dir / f"cards-{stamp}.jsonl"
        shutil.copy2(path, target)
        return target
    except OSError as exc:
        log.error("Backup snapshot failed: %s", exc)
        return None


def list_snapshots(backups_dir: Path = DEFAULT_BACKUPS) -> list[Snapshot]:
    """Return all snapshots, newest first."""
    if not backups_dir.is_dir():
        return []
    out: list[Snapshot] = []
    for p in backups_dir.glob("cards-*.jsonl"):
        ts = _parse_timestamp(p.name)
        if ts is not None:
            out.append(Snapshot(path=p, timestamp=ts))
    out.sort(key=lambda s: s.timestamp, reverse=True)
    return out


def prune(backups_dir: Path = DEFAULT_BACKUPS, keep: int = 10) -> int:
    """Delete oldest snapshots so only `keep` remain. Returns deletion count."""
    snaps = list_snapshots(backups_dir)
    if len(snaps) <= keep:
        return 0
    to_delete = snaps[keep:]
    for s in to_delete:
        try:
            s.path.unlink()
        except OSError as exc:
            log.warning("Failed to prune %s: %s", s.path, exc)
    return len(to_delete)


def restore_snapshot(
    snapshot_name: str,
    archive_path: Path = DEFAULT_ARCHIVE,
    backups_dir: Path = DEFAULT_BACKUPS,
) -> None:
    """Replace archive contents with this snapshot's contents.

    SAFETY: snapshots the current archive first, so a restore-by-mistake can be
    undone by restoring the pre-restore snapshot.
    """
    source = backups_dir / snapshot_name
    if not source.is_file():
        raise FileNotFoundError(f"No snapshot at {source}")
    snapshot(archive_path, backups_dir)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, archive_path)


def export_archive(
    target: Path,
    fmt: Literal["jsonl", "json"] = "jsonl",
    archive_path: Path = DEFAULT_ARCHIVE,
) -> None:
    """Dump archive to target. jsonl = byte-copy. json = pretty, {cards: [...]}."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "jsonl":
        shutil.copy2(archive_path, target)
        return
    cards = _load_archive(archive_path)
    payload = {
        "exported_at": datetime.now(UTC).isoformat(),
        "cards": [
            {
                "id": c.id,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                "question": c.card.question,
                "options": c.card.options,
                "correct_answer": c.card.correct_answer,
                "source_file": c.card.source_file,
                "index": c.card.index,
                "tags": c.card.tags,
            }
            for c in cards
        ],
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def import_archive(
    source: Path,
    mode: Literal["merge", "replace"] = "merge",
    archive_path: Path = DEFAULT_ARCHIVE,
) -> tuple[int, int]:
    """Load cards from source (.jsonl or pretty .json). Merge or replace."""
    incoming_cards = _read_cards_for_import(source)
    if mode == "replace":
        snapshot(archive_path)
        _save_all([], archive_path)
    return _merge_cards(incoming_cards, archive_path)


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _latest_snapshot(backups_dir: Path) -> Snapshot | None:
    snaps = list_snapshots(backups_dir)
    return snaps[0] if snaps else None


def _parse_timestamp(filename: str) -> datetime | None:
    stem = filename.removeprefix("cards-").removesuffix(".jsonl")
    try:
        return datetime.strptime(stem, "%Y%m%d-%H%M%S").replace(tzinfo=UTC)
    except ValueError:
        return None


def _read_cards_for_import(source: Path) -> list[Card]:
    text = source.read_text()
    # .json files are pretty-printed {cards: [...]}; .jsonl is one object per line.
    # We also sniff the content for unknown extensions -- a top-level object that
    # isn't JSONL (which would be line-delimited) gets the JSON path.
    if source.suffix == ".json":
        payload = json.loads(text)
        rows = payload.get("cards", []) if isinstance(payload, dict) else payload
    else:
        # .jsonl or anything else: parse line by line
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    out: list[Card] = []
    for r in rows:
        # r is a dict parsed from JSON; we guard with isinstance for mypy
        if not isinstance(r, dict):
            continue
        out.append(
            Card(
                question=str(r["question"]),
                options=(
                    {str(k): str(v) for k, v in r["options"].items()}
                    if isinstance(r.get("options"), dict)
                    else {}
                ),
                correct_answer=str(r["correct_answer"]),
                source_file=str(r.get("source_file", "imported")),
                index=int(str(r.get("index", 0))),
                tags=list(r.get("tags", [])) if isinstance(r.get("tags"), list) else [],
            )
        )
    return out
