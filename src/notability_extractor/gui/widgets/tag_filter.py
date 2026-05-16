"""Dropdown button with a checkable, searchable tag list inside."""

# pylint: disable=no-member

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)


class TagFilterButton(QToolButton):
    """A toolbar-style button that opens a popup with:
       - a search box at the top to filter the visible tag list
       - a scrollable list of checkable tags below

    Emits ``changed`` whenever the set of checked tags changes.
    """

    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setText("Filter by tag")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self._menu = QMenu(self)
        self.setMenu(self._menu)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Find tag...")
        self._search.textChanged.connect(self._on_search_typed)
        layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.setMinimumWidth(220)
        self._list.setMinimumHeight(220)
        self._list.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._list)

        action = QWidgetAction(self._menu)
        action.setDefaultWidget(container)
        self._menu.addAction(action)

    def set_tags(self, tags: list[str], checked: set[str] | None = None) -> None:
        """Rebuild the tag list. ``checked`` is the set to pre-check."""
        keep_checked = checked if checked is not None else set()
        self._list.blockSignals(True)
        self._list.clear()
        for t in tags:
            item = QListWidgetItem(t)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if t in keep_checked else Qt.CheckState.Unchecked
            )
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._refresh_button_label()

    def checked_tags(self) -> list[str]:
        out: list[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                out.append(item.text())
        return out

    def _on_search_typed(self, query: str) -> None:
        # filter the popup list by substring (case-insensitive); doesn't touch checked state
        needle = query.lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is None:
                continue
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        self._refresh_button_label()
        self.changed.emit()

    def _refresh_button_label(self) -> None:
        n = len(self.checked_tags())
        if n == 0:
            self.setText("Filter by tag")
        elif n == 1:
            self.setText("Filter by tag (1 selected)")
        else:
            self.setText(f"Filter by tag ({n} selected)")
