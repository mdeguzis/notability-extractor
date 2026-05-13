"""
Locate Notability data files on the local filesystem.

CONFIRMED ARCHITECTURE:
  Notability does NOT use a local SQLite database for note content.
  Notes are stored as .note files (ZIP archives containing binary plists).
  However, the app may maintain index/settings SQLite files alongside the
  .note files -- these are worth checking for flashcard/study-set metadata.

  We search for both .sqlite and .note files so the caller can choose
  the most appropriate extraction path.

References:
  https://jvns.ca/blog/2018/03/31/reverse-engineering-notability-format/
"""

from pathlib import Path

from notability_extractor.utils import get_logger

log = get_logger(__name__)

# Standard macOS locations where Notability stores its data.
_CANDIDATE_DIRS: list[str] = [
    "~/Library/Group Containers/com.gingerlabs.Notability",
    "~/Library/Containers/com.gingerlabs.Notability/Data/Library/Application Support",
]


def find_db(hint: str | None = None) -> Path | None:
    """
    Return the path to the Notability SQLite database.

    If *hint* is given it is used directly (after expanding ~).
    Otherwise the function searches the known macOS candidate directories
    and returns the first .sqlite file found.

    Returns None and logs a helpful message when nothing is found.
    """
    if hint:
        p = Path(hint).expanduser()
        if p.is_file():
            log.info("Using user-supplied DB path: %s", p)
            return p
        log.error("Supplied DB path does not exist: %s -- check the path and try again.", p)
        return None

    for raw in _CANDIDATE_DIRS:
        base = Path(raw).expanduser()
        if not base.exists():
            log.debug("Candidate directory not present: %s", base)
            continue

        hits = sorted(base.rglob("*.sqlite"))
        if hits:
            chosen = hits[0]
            log.info(
                "Found Notability DB: %s  (dir: %s, total .sqlite files: %d)",
                chosen,
                base,
                len(hits),
            )
            if len(hits) > 1:
                log.debug(
                    "Multiple .sqlite files found under %s; using the first: %s",
                    base,
                    chosen,
                )
            return chosen

        log.debug("No .sqlite files found under: %s", base)

    log.warning(
        "No Notability SQLite database found in standard macOS paths.\n"
        "  Searched:\n%s\n"
        "  Tip: pass --db <path> to specify the file manually.",
        "\n".join(f"    {p}" for p in _CANDIDATE_DIRS),
    )
    return None


def find_note_dirs() -> list[Path]:
    """
    Return candidate base directories that exist on this machine.

    Used by note_parser.find_note_files() to locate .note archives.
    """
    found: list[Path] = []
    for raw in _CANDIDATE_DIRS:
        p = Path(raw).expanduser()
        if p.exists():
            found.append(p)
            log.debug("Note data directory exists: %s", p)
        else:
            log.debug("Note data directory not present: %s", p)
    return found


def candidate_dirs() -> list[Path]:
    """Return expanded candidate directory paths (for testing / inspection)."""
    return [Path(p).expanduser() for p in _CANDIDATE_DIRS]
