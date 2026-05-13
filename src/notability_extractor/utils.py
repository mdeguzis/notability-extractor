"""Shared utilities: logging setup and binary-value detection."""

import hashlib
import logging
import sys


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def is_binary(value: object) -> bool:
    return isinstance(value, (bytes, bytearray))


def field_checksum(text: str) -> int:
    """Anki field checksum: first 8 hex digits of SHA-1 of the field text."""
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16)
