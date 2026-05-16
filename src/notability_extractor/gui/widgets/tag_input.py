"""Chip-style tag input with autocomplete."""

# PySide6 Signals are resolved at runtime via C extensions; pylint cant see
# the .connect() members statically even with extension-pkg-allow-list.
# pylint: disable=no-member

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _normalize(raw: str) -> str:
    """Strip and collapse internal whitespace. Preserves case."""
    return " ".join(raw.split())


class TagInput(QWidget):
    """Removable tag chips + a text entry with autocomplete."""

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
        chip = QWidget()
        row = QHBoxLayout(chip)
        row.setContentsMargins(6, 2, 4, 2)
        lbl = QLabel(tag)
        x = QPushButton("x")
        x.setFixedSize(16, 16)
        # capture both tag and chip_widget to avoid the cell-var-from-loop issue
        x.clicked.connect(lambda *_, t=tag, c=chip: self._remove(t, c))
        row.addWidget(lbl)
        row.addWidget(x)
        chip.setStyleSheet("background:#e0e0e0; border-radius:8px;")
        self._chip_row.addWidget(chip)
        self.changed.emit()

    def _remove(self, tag: str, chip_widget: QWidget) -> None:
        self._tags = [t for t in self._tags if t != tag]
        chip_widget.deleteLater()
        self.changed.emit()
