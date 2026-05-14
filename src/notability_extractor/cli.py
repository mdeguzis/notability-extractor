"""
Command-line interface for notability-extractor.

Entry point: notability-extractor (registered via pyproject.toml)
Also runnable as: python -m notability_extractor

Two phases:
  1. extract   - read .nbn bundles + HTTP cache (macOS only), produce input dir
  2. build     - read input dir, write .apkg / .json / .md outputs

On macOS, running with no flags does both phases. On Linux/Windows, you must
provide --input-dir pointing at a pre-extracted dir.
"""

import argparse
import sys
from pathlib import Path

from notability_extractor import __version__
from notability_extractor.build.apkg_writer import write_apkg_deck
from notability_extractor.build.json_writer import write_json_deck
from notability_extractor.build.md_writer import write_md_deck
from notability_extractor.build.reader import read_input_dir
from notability_extractor.extract.exporter import run_extract
from notability_extractor.extract.platform_check import (
    default_cache_dir,
    default_input_dir,
    default_notes_dir,
    is_macos,
)
from notability_extractor.utils import configure_logging, get_logger

log = get_logger(__name__)
_FORMATS = ("apkg", "json", "md")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="notability-extractor",
        description=(
            "Extract Notability Learn content (quizzes, summaries, OCR) and "
            "export as an Anki deck, JSON, or Markdown."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # macOS: auto-extract and build all three outputs to current dir
  notability-extractor

  # Anywhere: build from a pre-extracted input dir
  notability-extractor --input-dir ~/notability_export

  # JSON only, custom output directory
  notability-extractor --input-dir ~/notability_export --format json --out-dir ./decks

  # macOS: just produce the input dir, don't build anything
  notability-extractor --extract-only
""",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "--input-dir",
        metavar="DIR",
        help="Use a pre-extracted dir instead of running phase 1 (required on non-macOS).",
    )
    p.add_argument(
        "--extract-only",
        action="store_true",
        help="Run phase 1 only (macOS only).",
    )
    p.add_argument(
        "--format",
        default="apkg,json,md",
        help="Comma-separated output formats. Choices: apkg, json, md. Default: all three.",
    )
    p.add_argument(
        "--out-dir",
        metavar="DIR",
        default=".",
        help=(
            "Where to write outputs. Default: current dir. Filenames are fixed: "
            "notability_flashcards.{apkg,json,md}."
        ),
    )
    p.add_argument(
        "--deck-name",
        default="Notability Flashcards",
        help="Anki deck name (inside the .apkg). Default: 'Notability Flashcards'.",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()
    configure_logging(verbose=args.verbose)

    # platform gating
    if args.extract_only and not is_macos():
        log.error("--extract-only is only available on macOS")
        sys.exit(1)
    if args.input_dir is None and not is_macos():
        log.error(
            "This command needs --input-dir on non-macOS. Phase 1 extraction "
            "requires Notability data that only exists on Macs. Provide a "
            "pre-extracted directory (run on a Mac first, then transfer)."
        )
        sys.exit(1)

    # phase 1: extract (auto-discovers macOS paths, no user knobs)
    if args.input_dir:
        input_dir = Path(args.input_dir).expanduser()
    else:
        input_dir = default_input_dir()
        run_extract(default_notes_dir(), default_cache_dir(), input_dir)

    if args.extract_only:
        return

    # parse + validate format list
    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    for f in formats:
        if f not in _FORMATS:
            log.error("Unknown format: %s. Valid: %s", f, ", ".join(_FORMATS))
            sys.exit(1)

    # phase 2: build
    deck = read_input_dir(input_dir, deck_name=args.deck_name)
    log.info(
        "Loaded deck: %d cards, %d summaries, %d notes",
        len(deck.cards),
        len(deck.summaries),
        len(deck.notes),
    )
    if not deck.cards and not deck.summaries and not deck.notes:
        log.error(
            "Nothing found under '%s'. Check the path points at a Notability "
            "export directory (containing learn/quizzes/, learn/summaries/, "
            "and/or top-level *.txt files).",
            input_dir,
        )
        sys.exit(1)

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    if "apkg" in formats:
        path = out_dir / "notability_flashcards.apkg"
        write_apkg_deck(deck, path)
        log.info("Wrote %s", path)
    if "json" in formats:
        path = out_dir / "notability_flashcards.json"
        write_json_deck(deck, path)
        log.info("Wrote %s", path)
    if "md" in formats:
        path = out_dir / "notability_flashcards.md"
        write_md_deck(deck, path)
        log.info("Wrote %s", path)
