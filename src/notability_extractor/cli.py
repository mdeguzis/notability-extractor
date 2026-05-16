"""
Command-line interface for notability-extractor.

Entry point: notability-extractor (registered via pyproject.toml).
Also runnable as: python -m notability_extractor

Two phases:
  1. extract   - read .nbn bundles + HTTP cache (macOS only), produce input dir
  2. build     - read input dir, MERGE into JSONL archive, write outputs from archive

The JSONL archive at ~/.notability_extractor/cards.jsonl is the source of truth
for flashcards. Notes and summaries are read directly from input dir at build time.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from notability_extractor import __version__
from notability_extractor.archive import backup as archive_backup
from notability_extractor.archive import store as archive_store
from notability_extractor.build import flashcards, notes, summaries
from notability_extractor.build.reader import read_input_dir
from notability_extractor.extract.exporter import run_extract
from notability_extractor.extract.platform_check import (
    default_cache_dir,
    default_input_dir,
    default_notes_dir,
    is_macos,
)
from notability_extractor.model import Card
from notability_extractor.utils import configure_logging, get_logger

log = get_logger(__name__)


def _archive_path() -> Path:
    override = os.environ.get("NOTABILITY_ARCHIVE")
    return Path(override) if override else archive_store.DEFAULT_ARCHIVE


def _backups_path() -> Path:
    override = os.environ.get("NOTABILITY_BACKUPS")
    return Path(override) if override else archive_backup.DEFAULT_BACKUPS


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="notability-extractor",
        description="Extract Notability Learn content and export to Anki / JSON / Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "--input-dir", metavar="DIR", help="Pre-extracted input dir (required on non-macOS)."
    )
    p.add_argument("--extract-only", action="store_true", help="Phase 1 only (macOS).")
    p.add_argument(
        "--out-dir", metavar="DIR", default=".", help="Output directory. Default: current dir."
    )
    p.add_argument("--deck-name", default="Notability Flashcards", help="Anki deck name.")
    p.add_argument(
        "--edit-flashcards", action="store_true", help="Open prompt-driven editor over the archive."
    )
    p.add_argument("--add-card", action="store_true", help="Interactively add a single card.")
    p.add_argument("--list-cards", action="store_true", help="Print archive contents.")
    p.add_argument("--tag", metavar="TAG", help="Filter --list-cards by tag.")
    p.add_argument("--backup", action="store_true", help="Snapshot the archive once.")
    p.add_argument("--export", metavar="PATH", help="Dump archive to PATH.")
    p.add_argument("--export-format", choices=["jsonl", "json"], default="jsonl")
    p.add_argument("--import", dest="import_path", metavar="PATH", help="Load archive from PATH.")
    p.add_argument("--mode", choices=["merge", "replace"], default="merge", help="Import mode.")
    p.add_argument("--gui", action="store_true", help="Launch the GUI.")
    p.add_argument("-v", "--verbose", action="store_true", help="DEBUG logging.")
    return p


def main() -> (
    None
):  # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements
    args = _build_parser().parse_args()
    configure_logging(verbose=args.verbose)
    archive_path = _archive_path()

    # short-circuit subcommands
    if args.gui:
        _launch_gui()
        return
    if args.backup:
        path = archive_backup.snapshot(archive_path, _backups_path())
        print(path if path else "no changes since last snapshot")
        return
    if args.export:
        archive_backup.export_archive(
            Path(args.export),
            fmt=args.export_format,
            archive_path=archive_path,
        )
        return
    if args.import_path:
        added, skipped = archive_backup.import_archive(
            Path(args.import_path),
            mode=args.mode,
            archive_path=archive_path,
        )
        print(f"added={added} skipped={skipped}")
        return
    if args.list_cards:
        _list_cards(archive_path, args.tag)
        return
    if args.add_card:
        _add_card_interactive(archive_path)
        return
    if args.edit_flashcards:
        _edit_flashcards_interactive(archive_path)
        return

    if args.extract_only and not is_macos():
        log.error("--extract-only is only available on macOS")
        sys.exit(1)
    if args.input_dir is None and not is_macos():
        log.error("Need --input-dir on non-macOS. Run extract on a Mac first.")
        sys.exit(1)

    if args.input_dir:
        input_dir = Path(args.input_dir).expanduser()
    else:
        input_dir = default_input_dir()
        run_extract(default_notes_dir(), default_cache_dir(), input_dir)
    if args.extract_only:
        return

    deck = read_input_dir(input_dir, deck_name=args.deck_name)
    log.info(
        "Loaded: %d cards, %d summaries, %d notes",
        len(deck.cards),
        len(deck.summaries),
        len(deck.notes),
    )
    if not deck.cards and not deck.summaries and not deck.notes:
        log.error("Nothing found under '%s'.", input_dir)
        sys.exit(1)

    added, skipped = archive_store.merge(deck.cards, archive_path)
    log.info("Merged into archive: %d added, %d already known", added, skipped)
    archive_backup.snapshot(archive_path, _backups_path())

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    archived_cards = archive_store.load(archive_path)

    flashcards.write_apkg(
        archived_cards, out_dir / "notability_flashcards.apkg", deck_name=args.deck_name
    )
    flashcards.write_json(archived_cards, out_dir / "notability_flashcards.json")
    flashcards.write_md(archived_cards, out_dir / "notability_flashcards.md")
    notes.write_json(deck.notes, out_dir / "notability_notes.json")
    notes.write_md(deck.notes, out_dir / "notability_notes.md")
    summaries.write_json(deck.summaries, out_dir / "notability_summaries.json")
    summaries.write_md(deck.summaries, out_dir / "notability_summaries.md")
    log.info("Build complete: %s", out_dir)


def _list_cards(archive_path: Path, tag: str | None) -> None:
    from notability_extractor.archive import filter as flt  # noqa: I001  # pylint: disable=import-outside-toplevel  # fmt: skip

    cards = archive_store.load(archive_path)
    if tag:
        cards = flt.by_tags(cards, [tag])
    for c in cards:
        tagstr = (" [" + ", ".join(c.card.tags) + "]") if c.card.tags else ""
        print(f"{c.id[:8]}  {c.card.question}{tagstr}")


def _add_card_interactive(archive_path: Path) -> None:
    print("Add a new card. Empty question cancels.")
    q = input("Question: ").strip()
    if not q:
        print("cancelled")
        return
    opts = {}
    for letter in ("A", "B", "C", "D"):
        opts[letter] = input(f"  {letter}: ").strip()
    correct = input("Correct (A/B/C/D): ").strip().upper()
    if correct not in opts:
        print("bad correct letter")
        return
    tags_raw = input("Tags (comma-separated, optional): ").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
    card = Card(
        question=q, options=opts, correct_answer=correct, source_file="manual", index=0, tags=tags
    )
    archived = archive_store.add(card, archive_path)
    print(f"added id={archived.id[:8]}")


def _edit_flashcards_interactive(archive_path: Path) -> None:  # pylint: disable=too-many-locals
    while True:
        cards = archive_store.load(archive_path)
        if not cards:
            print("Archive is empty.")
            return
        for i, c in enumerate(cards, 1):
            print(f"{i:3}. {c.card.question}")
        cmd = input("\n[number to edit, 'd N' to delete, 'q' to quit]: ").strip()
        if cmd == "q":
            return
        if cmd.startswith("d "):
            try:
                idx = int(cmd[2:].strip()) - 1
                archive_store.delete(cards[idx].id, archive_path)
                print("deleted")
            except (ValueError, IndexError, KeyError) as exc:
                print(f"err: {exc}")
            continue
        try:
            idx = int(cmd) - 1
            target = cards[idx]
        except (ValueError, IndexError):
            print("invalid")
            continue
        new_q = input(f"Question [{target.card.question}]: ").strip() or target.card.question
        new_opts = dict(target.card.options)
        for letter in ("A", "B", "C", "D"):
            v = input(f"  {letter} [{new_opts[letter]}]: ").strip()
            if v:
                new_opts[letter] = v
        new_correct = (
            input(f"Correct [{target.card.correct_answer}]: ").strip().upper()
            or target.card.correct_answer
        )
        new_tags_raw = input(f"Tags (comma) [{', '.join(target.card.tags)}]: ").strip()
        new_tags = (
            [t.strip() for t in new_tags_raw.split(",") if t.strip()]
            if new_tags_raw
            else target.card.tags
        )
        new_card = Card(
            question=new_q,
            options=new_opts,
            correct_answer=new_correct,
            source_file=target.card.source_file,
            index=target.card.index,
            tags=new_tags,
        )
        archive_store.update(target.id, new_card, archive_path)
        print("saved")


def _launch_gui() -> None:
    # gui package may not exist yet; catch ImportError gracefully so --gui fails
    # with a clear message rather than a traceback
    try:
        from notability_extractor.gui.app import main as gui_main  # type: ignore[import-untyped]  # pylint: disable=import-outside-toplevel  # noqa: I001
    except ImportError as exc:
        print(f"GUI unavailable: {exc}", file=sys.stderr)
        print("Reinstall with: pip install notability-extractor", file=sys.stderr)
        sys.exit(1)
    gui_main()
