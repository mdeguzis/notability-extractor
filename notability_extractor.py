#!/usr/bin/env python3
"""
notability_extractor.py

Discovers the Notability SQLite database on macOS, extracts flashcard data,
and exports it as an Anki .apkg deck.

Notability DB locations (macOS):
  ~/Library/Group Containers/com.gingerlabs.Notability/
  ~/Library/Containers/com.gingerlabs.Notability/Data/Library/Application Support/

Usage:
  python3 notability_extractor.py [--db PATH] [--out OUTPUT.apkg] [--list-tables]
"""

import argparse
import os
import sqlite3
import sys
import time
import random
import struct
import zipfile
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DB discovery
# ---------------------------------------------------------------------------

CANDIDATE_DIRS = [
    "~/Library/Group Containers/com.gingerlabs.Notability",
    "~/Library/Containers/com.gingerlabs.Notability/Data/Library/Application Support",
]


def find_notability_db(hint: str | None = None) -> Path | None:
    """Return the first .sqlite file found in known Notability dirs."""
    if hint:
        p = Path(hint).expanduser()
        if p.is_file():
            log.info("Using user-supplied DB path: %s", p)
            return p
        log.error("Supplied path does not exist: %s", p)
        return None

    for candidate in CANDIDATE_DIRS:
        base = Path(candidate).expanduser()
        if not base.exists():
            log.debug("Candidate dir not found: %s", base)
            continue
        hits = sorted(base.rglob("*.sqlite"))
        if hits:
            chosen = hits[0]
            log.info(
                "Found Notability DB: %s (source dir: %s, total candidates: %d)",
                chosen,
                base,
                len(hits),
            )
            return chosen
        log.debug("No .sqlite files under: %s", base)

    log.warning(
        "No Notability SQLite database found in standard macOS paths. "
        "Pass --db <path> to specify it manually."
    )
    return None


# ---------------------------------------------------------------------------
# Table introspection
# ---------------------------------------------------------------------------

FLASHCARD_TABLE_HINTS = [
    "flashcard",
    "studyset",
    "learnitem",
    "card",
    "quiz",
    "term",
    "definition",
]


def open_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r["name"] for r in rows]


def find_flashcard_tables(tables: list[str]) -> list[str]:
    """Return tables whose names look flashcard-related."""
    return [
        t
        for t in tables
        if any(hint in t.lower() for hint in FLASHCARD_TABLE_HINTS)
    ]


def describe_table(conn: sqlite3.Connection, table: str) -> list[dict]:
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return [dict(r) for r in rows]


def sample_rows(
    conn: sqlite3.Connection, table: str, limit: int = 5
) -> list[sqlite3.Row]:
    return conn.execute(f"SELECT * FROM '{table}' LIMIT {limit}").fetchall()


def is_binary(value) -> bool:
    return isinstance(value, (bytes, bytearray))


# ---------------------------------------------------------------------------
# Flashcard extraction
# ---------------------------------------------------------------------------

def extract_flashcards(conn: sqlite3.Connection, table: str) -> list[dict]:
    """
    Pull rows from `table` and map them to {front, back} dicts.

    Notability may store text directly or inside BLOBs. We do a best-effort
    decode: if a column value is bytes and valid UTF-8, use it; otherwise mark
    it as binary so the caller can decide how to handle protobuf/nbn blobs.
    """
    cols = [c["name"] for c in describe_table(conn, table)]
    rows = conn.execute(f"SELECT * FROM '{table}'").fetchall()
    log.debug(
        "extract_flashcards: table=%s, columns=%s, row_count=%d",
        table,
        cols,
        len(rows),
    )

    cards = []
    for row in rows:
        d = {}
        for col in cols:
            val = row[col]
            if is_binary(val):
                try:
                    val = val.decode("utf-8")
                    log.debug(
                        "Column %s decoded from UTF-8 bytes (source: table=%s)",
                        col,
                        table,
                    )
                except (UnicodeDecodeError, AttributeError):
                    val = f"<binary blob {len(val)} bytes>"
                    log.warning(
                        "Column %s contains non-UTF-8 binary data -- likely protobuf or nbn blob "
                        "(table=%s). Manual protobuf decoding may be required.",
                        col,
                        table,
                    )
            d[col] = val
        cards.append(d)

    log.info("Extracted %d rows from table '%s'", len(cards), table)
    return cards


def guess_front_back(cards: list[dict]) -> list[dict]:
    """
    Heuristically map arbitrary column names to front/back.

    Priority: columns whose names contain 'front'/'term'/'question' -> front,
    'back'/'definition'/'answer' -> back.
    Falls back to first two text columns.
    """
    if not cards:
        return []

    cols = list(cards[0].keys())

    def pick(keywords):
        for kw in keywords:
            for c in cols:
                if kw in c.lower():
                    return c
        return None

    front_col = pick(["front", "term", "question"])
    back_col = pick(["back", "definition", "answer"])

    if not front_col or not front_col:
        text_cols = [c for c in cols if not any(b in c.lower() for b in ["id", "z_pk", "blob", "data"])]
        front_col = text_cols[0] if len(text_cols) > 0 else cols[0]
        back_col = text_cols[1] if len(text_cols) > 1 else cols[1] if len(cols) > 1 else cols[0]
        log.info(
            "No obvious front/back column names found; using '%s' -> front, '%s' -> back "
            "(source: heuristic fallback on table columns)",
            front_col,
            back_col,
        )
    else:
        log.debug(
            "Mapped front_col=%s back_col=%s (source: keyword match on column names)",
            front_col,
            back_col,
        )

    result = []
    for c in cards:
        result.append({"front": str(c.get(front_col, "")), "back": str(c.get(back_col, ""))})
    return result


# ---------------------------------------------------------------------------
# Anki .apkg export
# ---------------------------------------------------------------------------
# An .apkg is a ZIP containing collection.anki2 (SQLite) + media (JSON index).
# We write a minimal Anki 2.1-compatible collection.

ANKI_SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id integer PRIMARY KEY,
    nid integer NOT NULL,
    did integer NOT NULL,
    ord integer NOT NULL,
    mod integer NOT NULL,
    usn integer NOT NULL,
    type integer NOT NULL,
    queue integer NOT NULL,
    due integer NOT NULL,
    ivl integer NOT NULL,
    factor integer NOT NULL,
    reps integer NOT NULL,
    lapses integer NOT NULL,
    left integer NOT NULL,
    odue integer NOT NULL,
    odid integer NOT NULL,
    flags integer NOT NULL,
    data text NOT NULL
);
CREATE TABLE IF NOT EXISTS col (
    id integer PRIMARY KEY,
    crt integer NOT NULL,
    mod integer NOT NULL,
    scm integer NOT NULL,
    ver integer NOT NULL,
    dty integer NOT NULL,
    usn integer NOT NULL,
    ls integer NOT NULL,
    conf text NOT NULL,
    models text NOT NULL,
    decks text NOT NULL,
    dconf text NOT NULL,
    tags text NOT NULL
);
CREATE TABLE IF NOT EXISTS graves (
    usn integer NOT NULL,
    oid integer NOT NULL,
    type integer NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    id integer PRIMARY KEY,
    guid text NOT NULL,
    mid integer NOT NULL,
    mod integer NOT NULL,
    usn integer NOT NULL,
    tags text NOT NULL,
    flds text NOT NULL,
    sfld text NOT NULL,
    csum integer NOT NULL,
    flags integer NOT NULL,
    data text NOT NULL
);
CREATE TABLE IF NOT EXISTS revlog (
    id integer PRIMARY KEY,
    cid integer NOT NULL,
    usn integer NOT NULL,
    ease integer NOT NULL,
    ivl integer NOT NULL,
    lastIvl integer NOT NULL,
    factor integer NOT NULL,
    time integer NOT NULL,
    type integer NOT NULL
);
"""

BASIC_MODEL_ID = 1702000000000
DECK_ID = 1702000000001
CONF_ID = 1


def _csum(text: str) -> int:
    """Anki field checksum: first 8 hex chars of SHA1 of first field."""
    import hashlib
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _guid() -> str:
    import base64
    return base64.b64encode(random.randbytes(9)).decode("ascii")


def build_anki_package(cards: list[dict], deck_name: str, out_path: Path):
    """Write cards as a minimal Anki .apkg file."""
    import tempfile

    now = int(time.time())

    model = {
        str(BASIC_MODEL_ID): {
            "id": BASIC_MODEL_ID,
            "name": "Notability Basic",
            "type": 0,
            "mod": now,
            "usn": -1,
            "sortf": 0,
            "did": None,
            "tmpls": [
                {
                    "name": "Card 1",
                    "ord": 0,
                    "qfmt": "{{Front}}",
                    "afmt": "{{FrontSide}}<hr id=answer>{{Back}}",
                    "bqfmt": "",
                    "bafmt": "",
                    "did": None,
                    "bfont": "",
                    "bsize": 0,
                }
            ],
            "flds": [
                {"name": "Front", "ord": 0, "sticky": False, "rtl": False, "font": "Arial", "size": 20},
                {"name": "Back", "ord": 1, "sticky": False, "rtl": False, "font": "Arial", "size": 20},
            ],
            "css": ".card { font-family: arial; font-size: 20px; text-align: center; }",
            "latexPre": "",
            "latexPost": "",
            "tags": [],
            "vers": [],
        }
    }

    deck = {
        str(DECK_ID): {
            "id": DECK_ID,
            "name": deck_name,
            "desc": "",
            "mod": now,
            "usn": -1,
            "collapsed": False,
            "browserCollapsed": False,
            "extendNew": 0,
            "extendRev": 0,
            "conf": CONF_ID,
            "dyn": 0,
            "newToday": [0, 0],
            "revToday": [0, 0],
            "lrnToday": [0, 0],
            "timeToday": [0, 0],
        }
    }

    dconf = {
        str(CONF_ID): {
            "id": CONF_ID,
            "name": "Default",
            "replayq": True,
            "lapse": {"delays": [10], "leechAction": 0, "leechFails": 8, "minInt": 1, "mult": 0},
            "rev": {"ease4": 1.3, "fuzz": 0.05, "ivlFct": 1, "maxIvl": 36500, "minSpace": 1, "perDay": 100},
            "new": {"bury": True, "delays": [1, 10], "initialFactor": 2500, "ints": [1, 4, 7], "order": 1, "perDay": 20, "separate": True},
            "timer": 0,
            "autoplay": True,
            "mod": now,
            "usn": -1,
        }
    }

    col_conf = {"nextPos": 1, "estTimes": True, "activeDecks": [DECK_ID], "sortType": "noteFld", "timeLim": 0, "sortBackwards": False, "addToCur": True, "curDeck": DECK_ID, "newBury": True, "newSpread": 0, "dueCounts": True, "curModel": str(BASIC_MODEL_ID), "collapseTime": 1200}

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "collection.anki2"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(ANKI_SCHEMA)

        conn.execute(
            "INSERT INTO col VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                1, now, now, now, 11, 0, -1, 0,
                json.dumps(col_conf),
                json.dumps(model),
                json.dumps(deck),
                json.dumps(dconf),
                "{}",
            ),
        )

        for i, card in enumerate(cards):
            note_id = now * 1000 + i
            card_id = note_id + 1
            front = card["front"]
            back = card["back"]
            flds = f"{front}\x1f{back}"

            conn.execute(
                "INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (note_id, _guid(), BASIC_MODEL_ID, now, -1, "", flds, front, _csum(front), 0, ""),
            )
            conn.execute(
                "INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (card_id, note_id, DECK_ID, 0, now, -1, 0, 0, i, 0, 0, 0, 0, 0, 0, 0, 0, ""),
            )

        conn.commit()
        conn.close()

        log.info(
            "Wrote %d notes to temporary Anki collection (source: build_anki_package)",
            len(cards),
        )

        with zipfile.ZipFile(str(out_path), "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(str(db_path), "collection.anki2")
            zf.writestr("media", "{}")

    log.info("Anki package written to: %s", out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract Notability flashcards and export to Anki .apkg"
    )
    parser.add_argument("--db", metavar="PATH", help="Path to Notability .sqlite file")
    parser.add_argument("--out", metavar="FILE", default="notability_flashcards.apkg", help="Output .apkg path")
    parser.add_argument("--deck-name", default="Notability Flashcards", help="Anki deck name")
    parser.add_argument("--list-tables", action="store_true", help="List all tables and exit")
    parser.add_argument("--table", metavar="NAME", help="Force a specific table to extract from")
    args = parser.parse_args()

    db_path = find_notability_db(args.db)
    if not db_path:
        sys.exit(1)

    conn = open_db(db_path)
    tables = list_tables(conn)

    if args.list_tables:
        print("Tables in", db_path)
        for t in tables:
            cols = describe_table(conn, t)
            print(f"  {t}  ({', '.join(c['name'] for c in cols)})")
        return

    fc_tables = [args.table] if args.table else find_flashcard_tables(tables)

    if not fc_tables:
        log.warning(
            "No flashcard-related tables found (searched for: %s). "
            "Run with --list-tables to inspect all tables.",
            FLASHCARD_TABLE_HINTS,
        )
        sys.exit(1)

    log.info(
        "Flashcard-candidate tables found: %s (source: keyword match against table names)",
        fc_tables,
    )

    all_cards: list[dict] = []
    for table in fc_tables:
        raw = extract_flashcards(conn, table)
        mapped = guess_front_back(raw)
        all_cards.extend(mapped)

    conn.close()

    if not all_cards:
        log.error("No cards extracted. Check the table schema with --list-tables.")
        sys.exit(1)

    out_path = Path(args.out)
    build_anki_package(all_cards, args.deck_name, out_path)
    print(f"Done. {len(all_cards)} cards written to: {out_path}")


if __name__ == "__main__":
    main()
