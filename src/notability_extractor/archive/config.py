"""Persistent GUI/CLI config at ~/.notability_extractor/config.json.

Schema is a flat dict. Reads are tolerant -- missing keys fall back to
sensible defaults. Writes are atomic via tmpfile + os.replace.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path.home() / ".notability_extractor" / "config.json"

# Keys and what they do:
#   theme      - color scheme: light | dark | auto (follows OS)
#   deck_name  - Anki deck name used when building .apkg
#   input_dir  - path to the Notability export dir; empty string = unset
#   export_dir - where backup snapshots are written
#   schedule   - headless backup cadence: off | hourly | daily | weekly
#   retention  - how many snapshots to keep
_DEFAULTS: dict[str, Any] = {
    "theme": "auto",
    "deck_name": "Notability Flashcards",
    "input_dir": "",
    "export_dir": str(Path.home() / "Documents" / "notability-backups"),
    "schedule": "off",
    "retention": 10,
}


def load(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load config from disk, falling back to defaults for missing keys.

    Returns a fresh dict each call -- callers can mutate freely without
    affecting the on-disk state.
    """
    out = dict(_DEFAULTS)
    if not path.is_file():
        return out
    try:
        raw = json.loads(path.read_text())
        if isinstance(raw, dict):
            for k, v in raw.items():
                out[k] = v
    except (OSError, json.JSONDecodeError):
        # corrupt config -- fall back to defaults rather than crash the app
        return dict(_DEFAULTS)
    return out


def save(cfg: dict[str, Any], path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Atomic write of config to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(payload)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def get(key: str, path: Path = DEFAULT_CONFIG_PATH) -> Any:
    """Convenience: load + get one key with default fallback."""
    return load(path).get(key, _DEFAULTS.get(key))


def set_value(key: str, value: Any, path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Convenience: load, set one key, save."""
    cfg = load(path)
    cfg[key] = value
    save(cfg, path)
