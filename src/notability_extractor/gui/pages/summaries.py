"""Summaries page: read-only markdown browser."""

# pylint: disable=no-member,duplicate-code

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
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
        self._row_to_summary_idx: list[int] = []

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        left.setContentsMargins(6, 6, 6, 6)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search summaries...")
        self._search.textChanged.connect(self._on_search_changed)
        left.addWidget(self._search)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        left.addWidget(self._list, 1)

        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setMinimumWidth(280)

        self._viewer = QTextBrowser()
        self._viewer.setOpenExternalLinks(True)

        self._empty_label = QLabel("Set Notability input dir in Settings to browse summaries.")
        self._empty_label.hide()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_w)
        splitter.addWidget(self._viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 880])
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, 1)
        outer.addWidget(self._empty_label)

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
        self._apply_filter(self._search.text())

    def set_input_dir(self, input_dir: Path | None) -> None:
        """Update the source dir (called by MainWindow after Settings changes)."""
        self._input_dir = input_dir
        self.refresh()

    def _on_search_changed(self, text: str) -> None:
        self._apply_filter(text)

    def _apply_filter(self, query: str) -> None:
        needle = query.lower().strip()
        self._row_to_summary_idx = []
        self._list.clear()
        for idx, s in enumerate(self._summaries):
            if not needle or needle in s.title.lower() or needle in s.body.lower():
                self._row_to_summary_idx.append(idx)
                self._list.addItem(QListWidgetItem(s.title))

    def _on_select(self, row: int) -> None:
        if 0 <= row < len(self._row_to_summary_idx):
            summary = self._summaries[self._row_to_summary_idx[row]]
            self._viewer.setMarkdown(summary.body)
