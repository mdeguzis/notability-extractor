"""GUI entry point: notability-extractor-gui."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from notability_extractor.archive import config as archive_config
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

    saved_theme = archive_config.get("theme")
    apply_theme(app, saved_theme if saved_theme in ("light", "dark", "auto") else "auto")

    saved_font_size = archive_config.get("font_size")
    if isinstance(saved_font_size, int) and 8 <= saved_font_size <= 24:
        font = app.font()
        font.setPointSize(saved_font_size)
        app.setFont(font)

    # global QSplitter handle styling so resize bars are actually visible.
    # Qt's default is 2-3 tiny dots that disappear against a dark theme.
    # 10px wide bar, subtle in idle state and brighter on hover.
    app.setStyleSheet(app.styleSheet() + """
        QSplitter::handle {
            background: rgba(160, 160, 168, 60);
        }
        QSplitter::handle:horizontal { width: 10px; }
        QSplitter::handle:vertical   { height: 10px; }
        QSplitter::handle:hover {
            background: rgba(100, 160, 220, 180);
        }
        QSplitter::handle:pressed {
            background: rgba(100, 160, 220, 220);
        }
        """)

    window = MainWindow()
    if not headless:
        window.show()
    return app, window


def main() -> None:
    saved_level = archive_config.get("log_level")
    level = saved_level if isinstance(saved_level, str) else "info"
    configure_logging(level=level)
    app, _ = build_app()
    sys.exit(app.exec())
