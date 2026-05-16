"""Library page: master-detail flashcard editor."""

# PySide6 Signals are resolved at runtime via C extensions; pylint cant see
# the .connect() members statically even with extension-pkg-allow-list.
# pylint: disable=no-member

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from notability_extractor.archive import filter as flt
from notability_extractor.archive import store as archive_store
from notability_extractor.gui.widgets.card_editor import CardEditorWidget
from notability_extractor.model import ArchivedCard, Card

_ID_ROLE = int(Qt.ItemDataRole.UserRole)


class LibraryPage(QWidget):  # pylint: disable=too-many-instance-attributes
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

        # left panel: toolbar + search box + card list
        left = QVBoxLayout()
        toolbar = QHBoxLayout()
        self._add_btn = QPushButton("+ Add")
        self._add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(self._add_btn)
        toolbar.addStretch(1)
        left.addLayout(toolbar)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search...")
        self._search.textChanged.connect(self._on_search_changed)
        left.addWidget(self._search)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        left.addWidget(self._list, 1)

        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setMinimumWidth(200)

        # right panel: card editor
        self._editor = CardEditorWidget(known_tags=[])
        self._editor.saved.connect(self._on_saved)
        self._editor.deleted.connect(self._on_deleted)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_w)
        splitter.addWidget(self._editor)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 820])
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter)

        self.refresh()

    def refresh(self) -> None:
        """Reload from disk and rebuild the list."""
        self._cards = archive_store.load(self._archive_path)
        # keep tag autocomplete pool in sync with what's actually in the archive
        self._editor._known_tags = flt.all_tags(self._cards)  # pylint: disable=protected-access
        self._on_search_changed(self._search.text())

    def _on_search_changed(self, text: str) -> None:
        visible = flt.by_text(self._cards, text) if text else self._cards
        self._list.clear()
        for c in visible:
            item = QListWidgetItem(c.card.question or "(blank)")
            item.setData(_ID_ROLE, c.id)
            self._list.addItem(item)

    def _on_select(self, row: int) -> None:
        if row < 0:
            return
        item = self._list.item(row)
        if item is None:
            return
        # navigating to an existing card discards any draft in flight
        self._pending_new = False
        card_id = item.data(_ID_ROLE)
        for c in self._cards:
            if c.id == card_id:
                self._editor.load_card(c)
                return

    def _on_add(self) -> None:
        # Show an unsaved draft in the editor. Don't write to disk yet -
        # Save commits the draft, switching cards or pressing Delete discards.
        self._pending_new = True
        self._list.setCurrentRow(-1)
        self._editor.load_draft()

    def _on_saved(self, card_id: str, new_card: Card) -> None:
        if self._pending_new and card_id == "":
            archived = archive_store.add(new_card, self._archive_path)
            self._pending_new = False
            self.refresh()
            self._on_change()
            # select the new row so the user sees the result
            for i in range(self._list.count()):
                item = self._list.item(i)
                if item is not None and item.data(_ID_ROLE) == archived.id:
                    self._list.setCurrentRow(i)
                    break
            return
        archive_store.update(card_id, new_card, self._archive_path)
        self.refresh()
        self._on_change()

    def _on_deleted(self, card_id: str) -> None:
        if self._pending_new and card_id == "":
            # discard the unsaved draft, no archive write
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
