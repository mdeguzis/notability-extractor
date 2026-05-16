"""GUI entry point: notability-extractor-gui."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from notability_extractor.utils import configure_logging, get_logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

    from notability_extractor.gui.main_window import MainWindow

log = get_logger(__name__)


def _set_wayland_if_needed() -> None:
    """Mirror MangoHudPy's Wayland trick: set QT_QPA_PLATFORM when no DISPLAY
    but a Wayland session is active. Lets SSH/login users avoid the export."""
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    if not os.environ.get("DISPLAY") and os.environ.get("WAYLAND_DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "wayland"
        log.info("No DISPLAY set + WAYLAND_DISPLAY present, forcing QT_QPA_PLATFORM=wayland")


def build_app(headless: bool = False) -> tuple[QApplication, MainWindow]:
    """Construct QApplication + MainWindow. Returns (app, window). Used by tests too."""
    # pylint: disable=import-outside-toplevel
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        print(f"PySide6 not installed: {exc}", file=sys.stderr)
        print("Reinstall with: pip install notability-extractor", file=sys.stderr)
        sys.exit(1)

    _set_wayland_if_needed()
    app: QApplication = QApplication.instance() or QApplication(
        sys.argv
    )  # type: ignore[assignment]

    from notability_extractor.gui.main_window import MainWindow
    from notability_extractor.gui.theme import apply_theme

    apply_theme(app, "auto")
    window = MainWindow()
    if not headless:
        window.show()
    return app, window


def main() -> None:
    configure_logging(verbose=False)
    app, _ = build_app()
    sys.exit(app.exec())
