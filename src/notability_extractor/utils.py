"""Shared utilities: logging setup and binary-value detection."""

from __future__ import annotations

import hashlib
import logging
import logging.handlers
import sys
from pathlib import Path

DEFAULT_LOG_DIR = Path.home() / ".notability_extractor" / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "notability.log"


def configure_logging(
    verbose: bool = False,
    level: str | None = None,
    to_file: bool = True,
) -> None:
    """Wire stderr + (optionally) a rotating file log.

    Precedence: explicit `level` arg > `verbose=True` shortcut > INFO default.
    File logging goes to ~/.notability_extractor/logs/notability.log with a
    1MB cap and 5 rotations, enough for an audit trail without filling disk.
    """
    if level is not None:
        resolved = getattr(logging, level.upper(), logging.INFO)
    elif verbose:
        resolved = logging.DEBUG
    else:
        resolved = logging.INFO

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(resolved)

    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(stderr)

    if to_file:
        try:
            DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                DEFAULT_LOG_FILE,
                maxBytes=1_000_000,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)-5s %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            root.addHandler(file_handler)
        except OSError:
            # if we can't write the log file (perms, RO fs), keep stderr-only;
            # logging itself should never crash the app
            pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def is_binary(value: object) -> bool:
    return isinstance(value, (bytes, bytearray))


def field_checksum(text: str) -> int:
    """Anki field checksum: first 8 hex digits of SHA-1 of the field text."""
    h = hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()
    return int(h[:8], 16)
