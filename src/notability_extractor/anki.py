"""
Build and write an Anki .apkg package from a list of front/back card dicts.

An .apkg is a ZIP file containing:
  - collection.anki2  -- a minimal SQLite database understood by Anki 2.1+
  - media             -- a JSON object mapping media filenames (empty here)

Reference: https://github.com/ankidroid/Anki-Android/wiki/Database-Structure
"""

import base64
import json
import random
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

from notability_extractor.utils import field_checksum, get_logger

log = get_logger(__name__)

_BASIC_MODEL_ID = 1702000000000
_DECK_ID = 1702000000001
_CONF_ID = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id      integer PRIMARY KEY,
    nid     integer NOT NULL,
    did     integer NOT NULL,
    ord     integer NOT NULL,
    mod     integer NOT NULL,
    usn     integer NOT NULL,
    type    integer NOT NULL,
    queue   integer NOT NULL,
    due     integer NOT NULL,
    ivl     integer NOT NULL,
    factor  integer NOT NULL,
    reps    integer NOT NULL,
    lapses  integer NOT NULL,
    left    integer NOT NULL,
    odue    integer NOT NULL,
    odid    integer NOT NULL,
    flags   integer NOT NULL,
    data    text    NOT NULL
);
CREATE TABLE IF NOT EXISTS col (
    id      integer PRIMARY KEY,
    crt     integer NOT NULL,
    mod     integer NOT NULL,
    scm     integer NOT NULL,
    ver     integer NOT NULL,
    dty     integer NOT NULL,
    usn     integer NOT NULL,
    ls      integer NOT NULL,
    conf    text    NOT NULL,
    models  text    NOT NULL,
    decks   text    NOT NULL,
    dconf   text    NOT NULL,
    tags    text    NOT NULL
);
CREATE TABLE IF NOT EXISTS graves (
    usn     integer NOT NULL,
    oid     integer NOT NULL,
    type    integer NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    id      integer PRIMARY KEY,
    guid    text    NOT NULL,
    mid     integer NOT NULL,
    mod     integer NOT NULL,
    usn     integer NOT NULL,
    tags    text    NOT NULL,
    flds    text    NOT NULL,
    sfld    text    NOT NULL,
    csum    integer NOT NULL,
    flags   integer NOT NULL,
    data    text    NOT NULL
);
CREATE TABLE IF NOT EXISTS revlog (
    id      integer PRIMARY KEY,
    cid     integer NOT NULL,
    usn     integer NOT NULL,
    ease    integer NOT NULL,
    ivl     integer NOT NULL,
    lastIvl integer NOT NULL,
    factor  integer NOT NULL,
    time    integer NOT NULL,
    type    integer NOT NULL
);
"""


def _guid() -> str:
    return base64.b64encode(random.randbytes(9)).decode("ascii")


def _build_collection(
    conn: sqlite3.Connection, cards: list[dict[str, Any]], deck_name: str, now: int
) -> None:
    conn.executescript(_SCHEMA)

    model = {
        str(_BASIC_MODEL_ID): {
            "id": _BASIC_MODEL_ID,
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
                {
                    "name": "Front",
                    "ord": 0,
                    "sticky": False,
                    "rtl": False,
                    "font": "Arial",
                    "size": 20,
                },
                {
                    "name": "Back",
                    "ord": 1,
                    "sticky": False,
                    "rtl": False,
                    "font": "Arial",
                    "size": 20,
                },
            ],
            "css": ".card { font-family: arial; font-size: 20px; text-align: center; }",
            "latexPre": "",
            "latexPost": "",
            "tags": [],
            "vers": [],
        }
    }

    deck = {
        str(_DECK_ID): {
            "id": _DECK_ID,
            "name": deck_name,
            "desc": "",
            "mod": now,
            "usn": -1,
            "collapsed": False,
            "browserCollapsed": False,
            "extendNew": 0,
            "extendRev": 0,
            "conf": _CONF_ID,
            "dyn": 0,
            "newToday": [0, 0],
            "revToday": [0, 0],
            "lrnToday": [0, 0],
            "timeToday": [0, 0],
        }
    }

    dconf = {
        str(_CONF_ID): {
            "id": _CONF_ID,
            "name": "Default",
            "replayq": True,
            "lapse": {"delays": [10], "leechAction": 0, "leechFails": 8, "minInt": 1, "mult": 0},
            "rev": {
                "ease4": 1.3,
                "fuzz": 0.05,
                "ivlFct": 1,
                "maxIvl": 36500,
                "minSpace": 1,
                "perDay": 100,
            },
            "new": {
                "bury": True,
                "delays": [1, 10],
                "initialFactor": 2500,
                "ints": [1, 4, 7],
                "order": 1,
                "perDay": 20,
                "separate": True,
            },
            "timer": 0,
            "autoplay": True,
            "mod": now,
            "usn": -1,
        }
    }

    col_conf = {
        "nextPos": 1,
        "estTimes": True,
        "activeDecks": [_DECK_ID],
        "sortType": "noteFld",
        "timeLim": 0,
        "sortBackwards": False,
        "addToCur": True,
        "curDeck": _DECK_ID,
        "newBury": True,
        "newSpread": 0,
        "dueCounts": True,
        "curModel": str(_BASIC_MODEL_ID),
        "collapseTime": 1200,
    }

    conn.execute(
        "INSERT INTO col VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            1,
            now,
            now,
            now,
            11,
            0,
            -1,
            0,
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
        front, back = card["front"], card["back"]
        flds = f"{front}\x1f{back}"
        conn.execute(
            "INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                note_id,
                _guid(),
                _BASIC_MODEL_ID,
                now,
                -1,
                "",
                flds,
                front,
                field_checksum(front),
                0,
                "",
            ),
        )
        conn.execute(
            "INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (card_id, note_id, _DECK_ID, 0, now, -1, 0, 0, i, 0, 0, 0, 0, 0, 0, 0, 0, ""),
        )

    conn.commit()
    log.debug("Inserted %d notes into temporary Anki collection", len(cards))


def write_apkg(cards: list[dict[str, Any]], deck_name: str, out_path: Path) -> None:
    """
    Write *cards* as an Anki .apkg file at *out_path*.

    Each card in *cards* must have ``"front"`` and ``"back"`` string keys.
    Raises ValueError when *cards* is empty.
    """
    if not cards:
        raise ValueError("No cards to write -- the .apkg would be empty.")

    now = int(time.time())

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "collection.anki2"
        conn = sqlite3.connect(str(db_path))
        _build_collection(conn, cards, deck_name, now)
        conn.close()

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(str(out_path), "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(str(db_path), "collection.anki2")
            zf.writestr("media", "{}")

    log.info(
        "Wrote %d cards to Anki package: %s  (deck: '%s')",
        len(cards),
        out_path,
        deck_name,
    )
