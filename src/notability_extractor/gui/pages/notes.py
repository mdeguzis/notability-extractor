"""Notes page: read-only browser. Reads from the configured input dir."""

# pylint: disable=no-member,duplicate-code

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from notability_extractor.build.reader import read_input_dir
from notability_extractor.model import NoteText


class NotesPage(QWidget):
    def __init__(self, input_dir: Path | None = None) -> None:
        super().__init__()
        self._input_dir = input_dir
        self._notes: list[NoteText] = []

        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        left.addWidget(self._list)
        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setMaximumWidth(300)
        layout.addWidget(left_w)

        self._viewer = QTextBrowser()
        layout.addWidget(self._viewer, 1)

        self._empty_label = QLabel("Set Notability input dir in Settings to browse notes.")
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        self.refresh()

    def refresh(self) -> None:
        if self._input_dir is None or not Path(self._input_dir).is_dir():
            self._list.clear()
            self._viewer.clear()
            self._empty_label.show()
            return
        self._empty_label.hide()
        deck = read_input_dir(self._input_dir)
        self._notes = deck.notes
        self._list.clear()
        for n in self._notes:
            self._list.addItem(QListWidgetItem(n.name))

    def set_input_dir(self, input_dir: Path | None) -> None:
        """Update the source dir (called by MainWindow after Settings changes)."""
        self._input_dir = input_dir
        self.refresh()

    def _on_select(self, row: int) -> None:
        if 0 <= row < len(self._notes):
            self._viewer.setPlainText(self._notes[row].body)
