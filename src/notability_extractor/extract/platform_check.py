"""Platform detection and default paths for macOS Notability data."""

import sys
from pathlib import Path

# Team prefix for the iCloud container - this is Ginger Labs' Apple Developer team ID
_ICLOUD_DIR_NAME = "ZP9ZJ4EF3S~com~gingerlabs~Notability"


def is_macos() -> bool:
    return sys.platform == "darwin"


def default_notes_dir() -> Path:
    """iCloud Drive location where .nbn bundles live on a synced Mac."""
    return Path.home() / "Library" / "Mobile Documents" / _ICLOUD_DIR_NAME / "Documents"


def default_cache_dir() -> Path:
    """Sandbox container where Cache.db + fsCachedData/ live."""
    return (
        Path.home()
        / "Library"
        / "Containers"
        / "com.gingerlabs.Notability"
        / "Data"
        / "Library"
        / "Caches"
        / "com.gingerlabs.Notability"
    )


def default_export_dir() -> Path:
    """Where phase 1 writes its output if --export-dir isn't given."""
    return Path.home() / "notability_export"
