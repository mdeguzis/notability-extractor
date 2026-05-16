"""Chip-style tag input with autocomplete and per-tag color picker."""

# PySide6 Signals are resolved at runtime via C extensions; pylint cant see
# the .connect() members statically even with extension-pkg-allow-list.
# pylint: disable=no-member

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from notability_extractor.archive import config as archive_config

DEFAULT_CHIP_COLOR = "#3a4a5c"

# small curated palette - works in both light and dark themes
_TAG_COLORS: list[tuple[str, str]] = [
    ("Blue", "#3a4a5c"),
    ("Green", "#2d7d4a"),
    ("Red", "#b13a3a"),
    ("Orange", "#c87a2d"),
    ("Gold", "#b3922d"),
    ("Purple", "#6b3a8c"),
    ("Teal", "#2d8c87"),
    ("Pink", "#b13a7a"),
    ("Gray", "#5a5a5a"),
]


def _normalize(raw: str) -> str:
    """Strip and collapse internal whitespace. Preserves case."""
    return " ".join(raw.split())


def _chip_stylesheet(color: str) -> str:
    return (
        f"background:{color}; color:#e8eef5; border-radius:12px; "
        "padding:4px 10px; font-size: 13px;"
    )


_ICON_BTN_STYLE = (
    "QPushButton { background: transparent; border: none; color: #e8eef5; "
    "font-size: 16px; font-weight: bold; padding: 0px; }"
    "QPushButton:hover { color: #ffffff; }"
)
_ICON_BTN_SIZE = 24


class TagInput(QWidget):
    """Removable tag chips + a text entry with autocomplete.

    Each chip has a small dropdown arrow that opens a color picker. The chosen
    color is persisted in config.tag_colors and applies wherever the tag is
    rendered (this widget + any future tag-aware UI).
    """

    changed = Signal()

    def __init__(self, initial: list[str], known: list[str]) -> None:
        super().__init__()
        self._tags: list[str] = []
        self._known = known

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._chip_row = QHBoxLayout()
        self._chip_row.setSpacing(4)
        outer.addLayout(self._chip_row)

        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Type a tag and press Enter")
        completer = QCompleter(known)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._entry.setCompleter(completer)
        self._entry.returnPressed.connect(self._on_submit)
        outer.addWidget(self._entry)

        for t in initial:
            self._add(t)

    def tags(self) -> list[str]:
        return list(self._tags)

    def _on_submit(self) -> None:
        normalized = _normalize(self._entry.text())
        if normalized:
            self._add(normalized)
        self._entry.clear()

    def _add(self, tag: str) -> None:
        if tag in self._tags:
            return
        self._tags.append(tag)
        chip = self._build_chip(tag)
        self._chip_row.addWidget(chip)
        self.changed.emit()

    def _build_chip(self, tag: str) -> QWidget:
        chip = QWidget()
        row = QHBoxLayout(chip)
        row.setContentsMargins(8, 4, 6, 4)
        row.setSpacing(6)
        lbl = QLabel(tag)
        lbl.setStyleSheet("font-size: 13px;")

        color = archive_config.get_tag_color(tag) or DEFAULT_CHIP_COLOR
        chip.setStyleSheet(_chip_stylesheet(color))

        # dropdown arrow: opens a color menu. Bigger triangle, bigger button.
        color_btn = QPushButton("▼")  # ▼ filled down triangle
        color_btn.setFixedSize(_ICON_BTN_SIZE, _ICON_BTN_SIZE)
        color_btn.setStyleSheet(_ICON_BTN_STYLE)
        color_btn.setToolTip("Change color")
        color_btn.clicked.connect(lambda *_, t=tag, c=chip, b=color_btn: self._pick_color(t, c, b))

        x = QPushButton("✕")  # ✕ multiplication-X close icon
        x.setFixedSize(_ICON_BTN_SIZE, _ICON_BTN_SIZE)
        x.setStyleSheet(_ICON_BTN_STYLE)
        x.setToolTip("Remove tag")
        # capture both tag and chip_widget to avoid the cell-var-from-loop issue
        x.clicked.connect(lambda *_, t=tag, c=chip: self._remove(t, c))

        row.addWidget(lbl)
        row.addWidget(color_btn)
        row.addWidget(x)
        return chip

    def _pick_color(self, tag: str, chip_widget: QWidget, anchor: QWidget) -> None:
        menu = QMenu(self)
        for name, hex_color in _TAG_COLORS:
            act = QAction(name, menu)
            # small color swatch icon via stylesheet wouldn't render in QAction;
            # rely on the tooltip and the immediate-apply feedback instead
            act.setData(hex_color)
            act.triggered.connect(
                lambda _checked=False, t=tag, c=chip_widget, h=hex_color: self._set_color(t, c, h)
            )
            menu.addAction(act)
        # show the menu just below the dropdown arrow button
        menu.exec(anchor.mapToGlobal(QPoint(0, anchor.height())))

    def _set_color(self, tag: str, chip_widget: QWidget, color: str) -> None:
        archive_config.set_tag_color(tag, color)
        chip_widget.setStyleSheet(_chip_stylesheet(color))
        self.changed.emit()

    def _remove(self, tag: str, chip_widget: QWidget) -> None:
        self._tags = [t for t in self._tags if t != tag]
        chip_widget.deleteLater()
        self.changed.emit()
