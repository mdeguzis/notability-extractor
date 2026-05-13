"""
Extract raw rows from a Notability table and map them to front/back card dicts.

Notability may store text directly in columns or encoded in BLOBs / Protocol
Buffers.  This module does best-effort UTF-8 decoding and logs a clear warning
when binary data is detected so the caller knows manual protobuf work is needed.
"""

import sqlite3

from notability_extractor.db import describe_table
from notability_extractor.utils import get_logger, is_binary

log = get_logger(__name__)

# Column name fragments that map to the card front / back.
_FRONT_KEYWORDS = ["front", "term", "question"]
_BACK_KEYWORDS = ["back", "definition", "answer"]

# Column name fragments that are never useful as text content.
_SKIP_KEYWORDS = ["id", "z_pk", "blob", "data", "mod", "usn", "crt"]


def extract_raw(conn: sqlite3.Connection, table: str) -> list[dict]:
    """
    Pull every row from *table* and return as plain dicts.

    Binary column values are decoded as UTF-8 when possible.  Non-decodable
    blobs are replaced with a placeholder string and a WARNING is emitted --
    these are likely protobuf payloads that require a dedicated decoder.
    """
    cols = [c["name"] for c in describe_table(conn, table)]
    rows = conn.execute(f"SELECT * FROM '{table}'").fetchall()
    log.debug(
        "extract_raw: table=%s  columns=%s  rows=%d", table, cols, len(rows)
    )

    records: list[dict] = []
    for row in rows:
        record: dict = {}
        for col in cols:
            val = row[col]
            if is_binary(val):
                try:
                    val = val.decode("utf-8")
                    log.debug(
                        "Column '%s' decoded from UTF-8 bytes (table=%s)", col, table
                    )
                except (UnicodeDecodeError, AttributeError):
                    val = f"<binary blob {len(val)} bytes>"
                    log.warning(
                        "Column '%s' in table '%s' contains non-UTF-8 binary data "
                        "(likely a protobuf or .nbn blob). "
                        "The exported card field will be a placeholder. "
                        "Manual protobuf decoding may be required to recover the text.",
                        col,
                        table,
                    )
            record[col] = val
        records.append(record)

    log.info("Extracted %d raw rows from table '%s'", len(records), table)
    return records


def _pick_column(cols: list[str], keywords: list[str]) -> str | None:
    """Return the first column whose name contains any of *keywords*."""
    for kw in keywords:
        for col in cols:
            if kw in col.lower():
                return col
    return None


def map_front_back(records: list[dict]) -> list[dict]:
    """
    Map raw row dicts to ``{"front": ..., "back": ...}`` dicts.

    Column selection priority:
    1. Columns containing 'front'/'term'/'question' -> front
       Columns containing 'back'/'definition'/'answer' -> back
    2. Fallback: first two non-ID text columns in declaration order.

    Returns an empty list when *records* is empty.
    """
    if not records:
        return []

    cols = list(records[0].keys())
    front_col = _pick_column(cols, _FRONT_KEYWORDS)
    back_col = _pick_column(cols, _BACK_KEYWORDS)

    if not front_col or not back_col:
        text_cols = [
            c for c in cols if not any(sk in c.lower() for sk in _SKIP_KEYWORDS)
        ]
        front_col = text_cols[0] if len(text_cols) > 0 else cols[0]
        back_col = (
            text_cols[1]
            if len(text_cols) > 1
            else (cols[1] if len(cols) > 1 else cols[0])
        )
        log.info(
            "No obvious front/back columns found; falling back to '%s' (front) "
            "and '%s' (back). Use --table + --front-col/--back-col to override.",
            front_col,
            back_col,
        )
    else:
        log.debug("Column mapping: front='%s'  back='%s'", front_col, back_col)

    return [
        {"front": str(rec.get(front_col, "")), "back": str(rec.get(back_col, ""))}
        for rec in records
    ]


def extract_cards(conn: sqlite3.Connection, table: str) -> list[dict]:
    """Convenience wrapper: extract raw rows and map to front/back dicts."""
    return map_front_back(extract_raw(conn, table))
