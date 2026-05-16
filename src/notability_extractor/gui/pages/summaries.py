"""Summaries page: read-only markdown browser."""

# pylint: disable=no-member

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
from notability_extractor.model import Summary


class SummariesPage(QWidget):
    def __init__(self, input_dir: Path | None = None) -> None:
        super().__init__()
        self._input_dir = input_dir
        self._summaries: list[Summary] = []

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
        self._viewer.setOpenExternalLinks(True)
        layout.addWidget(self._viewer, 1)

        self._empty_label = QLabel("Set Notability input dir in Settings to browse summaries.")
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
        self._summaries = deck.summaries
        self._list.clear()
        for s in self._summaries:
            self._list.addItem(QListWidgetItem(s.title))

    def _on_select(self, row: int) -> None:
        if 0 <= row < len(self._summaries):
            self._viewer.setMarkdown(self._summaries[row].body)
