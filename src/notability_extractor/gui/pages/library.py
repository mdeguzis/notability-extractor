"""Library page: master-detail flashcard editor."""

# PySide6 Signals are resolved at runtime via C extensions; pylint cant see
# the .connect() members statically even with extension-pkg-allow-list.
# pylint: disable=no-member

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from notability_extractor.archive import filter as flt
from notability_extractor.archive import store as archive_store
from notability_extractor.gui.widgets.card_editor import CardEditorWidget
from notability_extractor.model import ArchivedCard, Card

_ID_ROLE = int(Qt.ItemDataRole.UserRole)

# row height = approx 3 lines of text. Calibrated for default Qt font ~22px line height.
_MAX_ROW_HEIGHT_PX = 66


class LibraryPage(QWidget):  # pylint: disable=too-many-instance-attributes
    # pylint: disable-next=too-many-statements
    def __init__(
        self,
        archive_path: Path | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._archive_path = archive_path or archive_store.DEFAULT_ARCHIVE
        self._on_change = on_change or (lambda: None)
        self._cards: list[ArchivedCard] = []

        # pending = a fresh blank not yet saved to the archive. None means
        # "no draft in flight". Save commits the draft; Delete or navigating
        # to another card discards it.
        self._pending_new = False

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # left panel: toolbar + search box + tag filter + card table
        left = QVBoxLayout()
        toolbar = QHBoxLayout()
        self._add_btn = QPushButton("+ Add")
        self._add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(self._add_btn)
        toolbar.addStretch(1)
        left.addLayout(toolbar)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search...")
        self._search.textChanged.connect(self._on_filter_changed)
        left.addWidget(self._search)

        self._tag_filter = QComboBox()
        self._tag_filter.setPlaceholderText("Filter by tag...")
        self._tag_filter.currentTextChanged.connect(self._on_filter_changed)
        left.addWidget(self._tag_filter)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["ID", "Tags", "Question"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setWordWrap(True)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 80)
        self._table.setColumnWidth(1, 140)
        self._table.currentCellChanged.connect(self._on_cell_changed)
        left.addWidget(self._table, 1)

        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setMinimumWidth(300)

        # right panel: card editor
        self._editor = CardEditorWidget(known_tags=[])
        self._editor.saved.connect(self._on_saved)
        self._editor.deleted.connect(self._on_deleted)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_w)
        splitter.addWidget(self._editor)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 760])
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter)

        self.refresh()

    def refresh(self) -> None:
        """Reload from disk and rebuild the table."""
        self._cards = archive_store.load(self._archive_path)
        all_tags = flt.all_tags(self._cards)
        # keep tag autocomplete pool in sync with what's actually in the archive
        self._editor._known_tags = all_tags  # pylint: disable=protected-access
        # rebuild the filter combobox, preserving the current selection if it
        # still exists in the new tag set
        current = self._tag_filter.currentText()
        self._tag_filter.blockSignals(True)
        self._tag_filter.clear()
        self._tag_filter.addItem("(all tags)")
        for t in all_tags:
            self._tag_filter.addItem(t)
        if current and current != "(all tags)" and current in all_tags:
            self._tag_filter.setCurrentText(current)
        else:
            self._tag_filter.setCurrentIndex(0)
        self._tag_filter.blockSignals(False)
        self._on_filter_changed()

    def _on_filter_changed(self, _text: str = "") -> None:
        visible = list(self._cards)
        tag = self._tag_filter.currentText()
        if tag and tag != "(all tags)":
            visible = flt.by_tags(visible, [tag])
        query = self._search.text()
        if query:
            visible = flt.by_text(visible, query)
        self._table.setRowCount(len(visible))
        for row_idx, c in enumerate(visible):
            id_item = QTableWidgetItem(c.id[:8])
            id_item.setData(_ID_ROLE, c.id)
            self._table.setItem(row_idx, 0, id_item)
            self._table.setItem(row_idx, 1, QTableWidgetItem(", ".join(c.card.tags)))
            self._table.setItem(row_idx, 2, QTableWidgetItem(c.card.question or "(blank)"))
        self._table.resizeRowsToContents()
        # cap row height at ~3 lines so long questions don't blow up the row
        for row_idx in range(self._table.rowCount()):
            if self._table.rowHeight(row_idx) > _MAX_ROW_HEIGHT_PX:
                self._table.setRowHeight(row_idx, _MAX_ROW_HEIGHT_PX)

    def _on_cell_changed(self, row: int, _col: int, _prev_row: int, _prev_col: int) -> None:
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        # navigating to an existing card discards any draft in flight
        self._pending_new = False
        card_id = item.data(_ID_ROLE)
        for c in self._cards:
            if c.id == card_id:
                self._editor.load_card(c)
                return

    def _select_id(self, card_id: str) -> None:
        for row_idx in range(self._table.rowCount()):
            item = self._table.item(row_idx, 0)
            if item is not None and item.data(_ID_ROLE) == card_id:
                self._table.setCurrentCell(row_idx, 0)
                return

    def _on_add(self) -> None:
        # Show an unsaved draft in the editor. Don't write to disk yet -
        # Save commits the draft, switching cards or pressing Delete discards.
        self._pending_new = True
        self._table.setCurrentCell(-1, -1)
        self._editor.load_draft()

    def _on_saved(self, card_id: str, new_card: Card) -> None:
        if self._pending_new and card_id == "":
            archived = archive_store.add(new_card, self._archive_path)
            self._pending_new = False
            self.refresh()
            self._on_change()
            self._select_id(archived.id)
            return
        archive_store.update(card_id, new_card, self._archive_path)
        self.refresh()
        self._on_change()
        self._select_id(card_id)

    def _on_deleted(self, card_id: str) -> None:
        if self._pending_new and card_id == "":
            self._pending_new = False
            self.refresh()
            return
        confirm = QMessageBox.question(
            self,
            "Delete card?",
            "Delete this card? It will still exist in your most recent backup.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        archive_store.delete(card_id, self._archive_path)
        self.refresh()
        self._on_change()
