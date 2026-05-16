"""Main window: sidebar + QStackedWidget + status bar."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from notability_extractor.archive import store as archive_store

_PAGE_NAMES = ["Library", "Notes", "Summaries", "Build", "Settings"]


class MainWindow(QMainWindow):  # pylint: disable=too-few-public-methods
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Notability Extractor")
        self.resize(1280, 800)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(160)
        for name in _PAGE_NAMES:
            self._sidebar.addItem(QListWidgetItem(name))
        self._sidebar.currentRowChanged.connect(  # pylint: disable=no-member
            self._on_sidebar_changed
        )

        self._pages = QStackedWidget()
        self._build_pages()

        layout.addWidget(self._sidebar)
        layout.addWidget(self._pages, 1)

        self.setCentralWidget(central)
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._refresh_status()

        self._sidebar.setCurrentRow(0)

    def _build_pages(self) -> None:
        # Keep page imports inside the method so a missing page doesn't blow up
        # every test that just needs MainWindow to instantiate cleanly.
        # pylint: disable=import-outside-toplevel
        from notability_extractor.archive import config as archive_config
        from notability_extractor.gui.pages.build import BuildPage
        from notability_extractor.gui.pages.library import LibraryPage
        from notability_extractor.gui.pages.notes import NotesPage
        from notability_extractor.gui.pages.settings import SettingsPage
        from notability_extractor.gui.pages.summaries import SummariesPage

        cfg = archive_config.load()
        raw_input_dir = cfg.get("input_dir", "") or ""
        input_dir = Path(raw_input_dir) if raw_input_dir else None

        self._pages.addWidget(LibraryPage(on_change=self._refresh_status))
        self._pages.addWidget(NotesPage(input_dir=input_dir))
        self._pages.addWidget(SummariesPage(input_dir=input_dir))
        self._pages.addWidget(BuildPage(input_dir=input_dir))
        self._pages.addWidget(SettingsPage())

    def _on_sidebar_changed(self, row: int) -> None:
        self._pages.setCurrentIndex(row)

    def _refresh_status(self) -> None:
        try:
            count = len(archive_store.load())
        except OSError:
            count = 0
        self._status.showMessage(f"archive: {count} cards")
