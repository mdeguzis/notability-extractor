"""JSONL archive store. All mutating writes are atomic and file-locked."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

try:
    import fcntl  # POSIX only

    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False
    import msvcrt

from notability_extractor.model import ArchivedCard, Card
from notability_extractor.utils import get_logger

log = get_logger(__name__)

DEFAULT_ARCHIVE = Path.home() / ".notability_extractor" / "cards.jsonl"


def load(path: Path = DEFAULT_ARCHIVE) -> list[ArchivedCard]:
    """Load cards from JSONL. Missing file is fine, corrupt lines are skipped."""
    if not path.is_file():
        return []
    out: list[ArchivedCard] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
                out.append(_row_to_archived(row))
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                log.warning("Skipping corrupt line %d in %s: %s", lineno, path, exc)
    return out


def save_all(cards: list[ArchivedCard], path: Path = DEFAULT_ARCHIVE) -> None:
    """Atomic write of the full archive. Sorted by id for deterministic diffs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_cards = sorted(cards, key=lambda c: c.id)
    lines = [json.dumps(_archived_to_row(c), separators=(",", ":")) + "\n" for c in sorted_cards]
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.writelines(lines)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    try:
        os.replace(tmp_name, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _archived_to_row(a: ArchivedCard) -> dict[str, object]:
    return {
        "id": a.id,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat(),
        "question": a.card.question,
        "options": a.card.options,
        "correct_answer": a.card.correct_answer,
        "source_file": a.card.source_file,
        "index": a.card.index,
        "tags": a.card.tags,
    }


def _row_to_archived(row: dict[str, object]) -> ArchivedCard:
    created = datetime.fromisoformat(str(row["created_at"]))
    updated = datetime.fromisoformat(str(row.get("updated_at", row["created_at"])))

    # options is always a dict in valid JSONL, but we guard so mypy is happy
    raw_opts = row["options"]
    if isinstance(raw_opts, dict):
        opts: dict[str, str] = {str(k): str(v) for k, v in raw_opts.items()}
    else:
        opts = {}

    # tags may be absent in older records
    raw_tags = row.get("tags")
    tags = [str(t) for t in raw_tags] if isinstance(raw_tags, list) else []

    card = Card(
        question=str(row["question"]),
        options=opts,
        correct_answer=str(row["correct_answer"]),
        source_file=str(row["source_file"]),
        index=int(str(row["index"])),
        tags=tags,
    )
    return ArchivedCard(card=card, id=str(row["id"]), created_at=created, updated_at=updated)


class ArchiveBusyError(RuntimeError):
    """Raised when the archive file lock can't be acquired after retries."""


@contextlib.contextmanager
def _file_lock(path: Path, retries: int = 3, backoff_s: float = 0.1) -> Iterator[None]:
    """Cross-platform exclusive file lock around path. Retries with backoff."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lockfile = path.with_suffix(path.suffix + ".lock")
    fh = None
    for attempt in range(retries + 1):
        try:
            fh = lockfile.open("w")
            if _HAS_FCNTL:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:  # pragma: no cover - Windows path
                # pylint: disable-next=used-before-assignment
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
            break
        except (BlockingIOError, OSError) as exc:
            if fh is not None:
                fh.close()
                fh = None
            if attempt < retries:
                time.sleep(backoff_s)
                continue
            raise ArchiveBusyError(f"Could not lock {path}") from exc
    try:
        yield
    finally:
        if fh is not None:
            with contextlib.suppress(OSError):
                if _HAS_FCNTL:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                fh.close()


def add(card: Card, path: Path = DEFAULT_ARCHIVE) -> ArchivedCard:
    """Append card to the archive. Returns the ArchivedCard."""
    with _file_lock(path):
        current = load(path)
        now = datetime.now(UTC)
        archived = ArchivedCard(card=card, id=card.stable_id, created_at=now, updated_at=now)
        current.append(archived)
        save_all(current, path)
        return archived


def update(card_id: str, new_card: Card, path: Path = DEFAULT_ARCHIVE) -> ArchivedCard:
    """Replace card content under card_id. id and created_at stay frozen."""
    with _file_lock(path):
        current = load(path)
        for i, a in enumerate(current):
            if a.id == card_id:
                updated = ArchivedCard(
                    card=new_card,
                    id=a.id,
                    created_at=a.created_at,
                    updated_at=datetime.now(UTC),
                )
                current[i] = updated
                save_all(current, path)
                return updated
        raise KeyError(f"No card with id {card_id!r}")


def delete(card_id: str, path: Path = DEFAULT_ARCHIVE) -> None:
    """Remove the card with this id, or raise KeyError."""
    with _file_lock(path):
        current = load(path)
        new = [a for a in current if a.id != card_id]
        if len(new) == len(current):
            raise KeyError(f"No card with id {card_id!r}")
        save_all(new, path)


def merge(incoming: list[Card], path: Path = DEFAULT_ARCHIVE) -> tuple[int, int]:
    """Append cards whose stable_id is not already in the archive.

    Returns (added, skipped) counts. Skipped == already-present duplicates.
    """
    with _file_lock(path):
        current = load(path)
        seen = {a.id for a in current}
        added = 0
        for card in incoming:
            if card.stable_id in seen:
                continue
            now = datetime.now(UTC)
            current.append(
                ArchivedCard(card=card, id=card.stable_id, created_at=now, updated_at=now)
            )
            seen.add(card.stable_id)
            added += 1
        save_all(current, path)
        return added, len(incoming) - added
