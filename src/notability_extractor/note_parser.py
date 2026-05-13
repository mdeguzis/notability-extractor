"""
Parse Notability .note files to extract flashcard / study-set content.

CONFIRMED ARCHITECTURE (from reverse-engineering analysis):
  - Notability does NOT use a local SQLite database for note content.
  - Notes are stored as .note files, which are ZIP archives containing:
      Session.plist   -- binary Apple plist with drawing/stroke data
      metadata.plist  -- note metadata (title, timestamps, etc.)
      assets/         -- embedded images and PDFs
  - The "Learn" / flashcard feature (added ~2022) may store study-set data
    inside these same .note files or in a separate file alongside them.
  - There is no confirmed protobuf encoding; data uses Apple binary plist
    and relative-encoded float arrays for stroke data.

References:
  https://jvns.ca/blog/2018/03/31/reverse-engineering-notability-format/
  https://github.com/xrayshan/notability-reader
  https://github.com/GZhonghui/NotabilityViewer

This module provides best-effort extraction: it opens .note ZIP archives,
parses every plist inside, and surfaces any key/value pairs that look like
flashcard front/back content for further inspection.
"""

import plistlib
import zipfile
from pathlib import Path

from notability_extractor.utils import get_logger

log = get_logger(__name__)

# Plist keys that commonly appear in Notability metadata
_TITLE_KEYS = {"title", "noteTitle", "name"}

# Plist keys that may indicate flashcard / study content in the Learn feature
_FLASHCARD_KEYS = {
    "term", "definition", "front", "back",
    "question", "answer", "studySet", "flashcard",
    "learnItem", "card",
}


def find_note_files(base: Path) -> list[Path]:
    """
    Recursively find all .note files under *base*.

    .note files are the primary Notability note container format.
    They are commonly stored under:
      ~/Library/Group Containers/com.gingerlabs.Notability/
    """
    if not base.exists():
        log.debug("Note search base does not exist: %s", base)
        return []
    hits = sorted(base.rglob("*.note"))
    log.info(
        "Found %d .note file(s) under: %s  (source: rglob '*.note')",
        len(hits),
        base,
    )
    return hits


def _parse_plist_bytes(data: bytes, source_label: str) -> object:
    """Deserialise *data* as a binary or XML plist. Returns None on failure."""
    try:
        return plistlib.loads(data)
    except Exception as exc:
        log.debug("Failed to parse plist from %s: %s", source_label, exc)
        return None


def _walk_plist(obj: object, depth: int = 0) -> list[dict]:
    """
    Recursively walk a deserialised plist object and collect dicts that
    contain keys resembling flashcard front/back pairs.
    """
    results: list[dict] = []
    if isinstance(obj, dict):
        lower_keys = {k.lower() for k in obj}
        if lower_keys & {fk.lower() for fk in _FLASHCARD_KEYS}:
            results.append({str(k): v for k, v in obj.items() if isinstance(v, (str, int, float, bool))})
        for v in obj.values():
            results.extend(_walk_plist(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_walk_plist(item, depth + 1))
    return results


def parse_note_file(note_path: Path) -> dict:
    """
    Open a .note file (ZIP archive) and extract whatever structured data
    can be read from the plists inside.

    Returns a dict with:
      "path"        -- absolute path to the .note file
      "metadata"    -- dict from metadata.plist (title, timestamps, etc.)
      "flashcards"  -- list of dicts that look like flashcard candidates
      "raw_members" -- list of member filenames found in the ZIP
    """
    result: dict = {
        "path": note_path,
        "metadata": {},
        "flashcards": [],
        "raw_members": [],
    }

    if not zipfile.is_zipfile(str(note_path)):
        log.warning(
            "Not a valid ZIP archive: %s  (expected .note format; skipping)",
            note_path,
        )
        return result

    with zipfile.ZipFile(str(note_path), "r") as zf:
        result["raw_members"] = zf.namelist()
        log.debug(
            "Opened .note archive: %s  members=%s",
            note_path.name,
            result["raw_members"],
        )

        for member in zf.namelist():
            if not member.endswith(".plist"):
                continue
            data = zf.read(member)
            parsed = _parse_plist_bytes(data, f"{note_path.name}/{member}")
            if parsed is None:
                continue

            label = f"{note_path.name}/{member}"
            if "metadata" in member.lower():
                if isinstance(parsed, dict):
                    result["metadata"] = {str(k): v for k, v in parsed.items() if isinstance(v, (str, int, float, bool))}
                    log.debug(
                        "Parsed metadata from %s: title=%s",
                        label,
                        result["metadata"].get("title") or result["metadata"].get("noteTitle"),
                    )
            else:
                candidates = _walk_plist(parsed)
                if candidates:
                    log.debug(
                        "Found %d flashcard candidate(s) in %s",
                        len(candidates),
                        label,
                    )
                result["flashcards"].extend(candidates)

    log.info(
        "Parsed .note file: %s  flashcard_candidates=%d",
        note_path.name,
        len(result["flashcards"]),
    )
    return result


def extract_cards_from_notes(note_files: list[Path]) -> list[dict]:
    """
    Parse a list of .note files and return front/back card dicts for any
    flashcard-like content found.

    NOTE: The Notability Learn/flashcard feature was added ~2022. If no
    flashcard candidates are found, the notes likely contain only regular
    ink/text data, not study sets. Inspect the raw plist keys manually
    with --list-tables (SQLite path) or check raw_members output.
    """
    cards: list[dict] = []
    for note_path in note_files:
        parsed = parse_note_file(note_path)
        for candidate in parsed["flashcards"]:
            # Map whatever keys we found to front/back
            front = (
                candidate.get("term")
                or candidate.get("front")
                or candidate.get("question")
                or ""
            )
            back = (
                candidate.get("definition")
                or candidate.get("back")
                or candidate.get("answer")
                or ""
            )
            if front or back:
                cards.append({"front": str(front), "back": str(back)})

    log.info(
        "Total flashcard candidates extracted from %d .note file(s): %d",
        len(note_files),
        len(cards),
    )
    return cards
