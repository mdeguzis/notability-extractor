"""
Command-line interface for notability-extractor.

Entry point: notability-extractor (registered via pyproject.toml)
Also runnable as: python -m notability_extractor
"""

"""
Command-line interface for notability-extractor.

Entry point: notability-extractor (registered via pyproject.toml)
Also runnable as: python -m notability_extractor

TWO EXTRACTION MODES
--------------------
1. --mode sqlite (default fallback)
   Searches for a .sqlite index file in Notability's data directories.
   NOTE: Confirmed research shows Notability does NOT store note CONTENT
   in SQLite. A .sqlite file may exist as an index/settings DB, but
   flashcard text will more likely be in .note archives. Use this mode
   to inspect whatever SQLite is found with --list-tables first.

2. --mode note (recommended for note content)
   Scans for .note files (ZIP archives + binary plists) -- the confirmed
   Notability storage format. Best-effort plist walking surfaces any
   flashcard/study-set keys found in the Learn feature data.

Reference:
  https://jvns.ca/blog/2018/03/31/reverse-engineering-notability-format/
"""

import argparse
import sys
from pathlib import Path

from notability_extractor import __version__
from notability_extractor.anki import write_apkg
from notability_extractor.db import (
    find_flashcard_tables,
    list_tables,
    open_db,
    print_schema,
)
from notability_extractor.discovery import find_db, find_note_dirs
from notability_extractor.extractor import extract_cards
from notability_extractor.note_parser import extract_cards_from_notes, find_note_files
from notability_extractor.utils import configure_logging, get_logger

log = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notability-extractor",
        description=(
            "Extract flashcards from a Notability SQLite database "
            "and export them as an Anki .apkg deck."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-discover DB on macOS and write default output file
  notability-extractor

  # Specify the DB manually
  notability-extractor --db ~/Library/Group\\ Containers/com.gingerlabs.Notability/Notability.sqlite

  # See what tables exist before extracting
  notability-extractor --list-tables

  # Target a specific table and output path
  notability-extractor --table ZFLASHCARD --out biology.apkg --deck-name "Biology 101"

  # Verbose debug output
  notability-extractor --verbose
""",
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--db",
        metavar="PATH",
        help="Path to the Notability .sqlite file (auto-discovered if omitted).",
    )
    parser.add_argument(
        "--out",
        metavar="FILE",
        default="notability_flashcards.apkg",
        help="Output .apkg path (default: notability_flashcards.apkg).",
    )
    parser.add_argument(
        "--deck-name",
        default="Notability Flashcards",
        metavar="NAME",
        help="Anki deck name (default: 'Notability Flashcards').",
    )
    parser.add_argument(
        "--list-tables",
        action="store_true",
        help="Print all tables and their columns, then exit.",
    )
    parser.add_argument(
        "--table",
        metavar="NAME",
        help="Extract from this specific table instead of auto-detecting.",
    )
    parser.add_argument(
        "--mode",
        choices=["note", "sqlite"],
        default="note",
        help=(
            "Extraction mode: 'note' parses .note ZIP archives (confirmed Notability format); "
            "'sqlite' searches for a .sqlite index DB (experimental -- flashcard content is "
            "unlikely to be there). Default: note."
        ),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )

    return parser


def _run_note_mode(args: argparse.Namespace) -> list[dict]:
    """Extract cards from .note file archives."""
    note_dirs = find_note_dirs()
    if not note_dirs:
        log.error(
            "No Notability data directories found on this machine.\n"
            "  Expected one of:\n"
            "    ~/Library/Group Containers/com.gingerlabs.Notability/\n"
            "    ~/Library/Containers/com.gingerlabs.Notability/...\n"
            "  Make sure Notability is installed on this Mac and has synced at least once."
        )
        sys.exit(1)

    note_files: list[Path] = []
    for base in note_dirs:
        note_files.extend(find_note_files(base))

    if not note_files:
        log.error(
            "No .note files found under the Notability data directories.\n"
            "  If notes exist only on iPad/iPhone, enable iCloud sync on macOS first."
        )
        sys.exit(1)

    log.info("Processing %d .note file(s)", len(note_files))
    return extract_cards_from_notes(note_files)


def _run_sqlite_mode(args: argparse.Namespace) -> list[dict]:
    """Extract cards from a Notability SQLite index database."""
    log.warning(
        "SQLite mode selected. NOTE: Confirmed research shows Notability does NOT store "
        "note content in SQLite. A .sqlite file may exist as a settings/index DB, but "
        "flashcard text is unlikely to be there. Consider --mode note instead.\n"
        "  Reference: https://jvns.ca/blog/2018/03/31/reverse-engineering-notability-format/"
    )

    db_path = find_db(args.db)
    if db_path is None:
        sys.exit(1)

    conn = open_db(db_path)
    tables = list_tables(conn)

    if args.list_tables:
        print(f"\nDatabase: {db_path}")
        print(f"{'Table':<40} Columns")
        print("-" * 80)
        print_schema(conn, tables)
        conn.close()
        sys.exit(0)

    target_tables: list[str]
    if args.table:
        if args.table not in tables:
            log.error(
                "Table '%s' not found. Run --mode sqlite --list-tables to see available tables.",
                args.table,
            )
            conn.close()
            sys.exit(1)
        target_tables = [args.table]
    else:
        target_tables = find_flashcard_tables(tables)
        if not target_tables:
            log.error(
                "No flashcard-related tables found automatically.\n"
                "  Run --mode sqlite --list-tables to inspect the schema."
            )
            conn.close()
            sys.exit(1)

    log.info("Extracting from table(s): %s", target_tables)
    all_cards: list[dict] = []
    for table in target_tables:
        all_cards.extend(extract_cards(conn, table))
    conn.close()
    return all_cards


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    configure_logging(verbose=args.verbose)

    # --list-tables only makes sense in sqlite mode
    if args.list_tables and args.mode != "sqlite":
        log.info("--list-tables implies --mode sqlite")
        args.mode = "sqlite"

    if args.mode == "note":
        all_cards = _run_note_mode(args)
    else:
        all_cards = _run_sqlite_mode(args)

    if not all_cards:
        log.error(
            "No cards were extracted.\n"
            "  In 'note' mode: the .note files may not contain Learn/flashcard data yet.\n"
            "  In 'sqlite' mode: the table(s) may be empty or store content as binary blobs.\n"
            "  Try --mode sqlite --list-tables to inspect the raw database schema."
        )
        sys.exit(1)

    out_path = Path(args.out)
    try:
        write_apkg(all_cards, args.deck_name, out_path)
    except ValueError as exc:
        log.error("%s", exc)
        sys.exit(1)

    print(f"\nDone. {len(all_cards)} cards written to: {out_path}")
    print(f"Import into Anki via: File > Import > {out_path}")
