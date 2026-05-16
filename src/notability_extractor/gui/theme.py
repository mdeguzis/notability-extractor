"""Theme application for the GUI.

Three modes: light, dark, auto. Auto reads OS color scheme at app launch.
Switching mid-session requires an app restart for v1; Qt doesn't always
repaint palette changes cleanly across every widget.
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

Theme = Literal["light", "dark", "auto"]


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Apply the given theme to the application palette."""
    resolved = _resolve(theme, app)
    if resolved == "dark":
        app.setPalette(_dark_palette())
    else:
        app.setPalette(app.style().standardPalette())


def _resolve(theme: Theme, app: QApplication) -> Literal["light", "dark"]:
    if theme != "auto":
        return theme
    try:
        hints = app.styleHints()
        scheme = hints.colorScheme()
        # Direct enum comparison works across PySide6 versions; int() cast fails on 6.5+
        return "dark" if scheme == Qt.ColorScheme.Dark else "light"
    except (AttributeError, RuntimeError):
        return "light"


def _dark_palette() -> QPalette:
    p = QPalette()
    base = QColor(40, 40, 44)
    text = QColor(220, 220, 220)
    p.setColor(QPalette.ColorRole.Window, base)
    p.setColor(QPalette.ColorRole.WindowText, text)
    p.setColor(QPalette.ColorRole.Base, QColor(30, 30, 34))
    p.setColor(QPalette.ColorRole.AlternateBase, base)
    p.setColor(QPalette.ColorRole.ToolTipBase, text)
    p.setColor(QPalette.ColorRole.ToolTipText, text)
    p.setColor(QPalette.ColorRole.Text, text)
    p.setColor(QPalette.ColorRole.Button, base)
    p.setColor(QPalette.ColorRole.ButtonText, text)
    p.setColor(QPalette.ColorRole.Highlight, QColor(42, 77, 143))
    p.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    return p
