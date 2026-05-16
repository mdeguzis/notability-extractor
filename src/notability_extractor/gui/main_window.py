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


class MainWindow(
    QMainWindow
):  # pylint: disable=too-few-public-methods,too-many-instance-attributes
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

        self._library_page = LibraryPage(on_change=self._refresh_status)
        self._notes_page = NotesPage(input_dir=input_dir)
        self._summaries_page = SummariesPage(input_dir=input_dir)
        self._build_page = BuildPage(input_dir=input_dir)
        self._settings_page = SettingsPage(on_archive_changed=self._refresh_all)

        for page in (
            self._library_page,
            self._notes_page,
            self._summaries_page,
            self._build_page,
            self._settings_page,
        ):
            self._pages.addWidget(page)

    def _on_sidebar_changed(self, row: int) -> None:
        self._pages.setCurrentIndex(row)
        # refresh the destination page on tab switch so external mutations
        # (CLI editing, another pull) show up without restart
        page = self._pages.widget(row)
        refresh_fn = getattr(page, "refresh", None)
        if callable(refresh_fn):
            refresh_fn()
        self._refresh_status()

    def _refresh_status(self) -> None:
        try:
            count = len(archive_store.load())
        except OSError:
            count = 0
        self._status.showMessage(f"archive: {count} cards")

    def _refresh_all(self) -> None:
        """Called by Settings after Pull / Import / Restore. Rereads config so
        input_dir changes are picked up, then refreshes every page."""
        # pylint: disable=import-outside-toplevel
        from notability_extractor.archive import config as archive_config

        cfg = archive_config.load()
        raw_input_dir = cfg.get("input_dir", "") or ""
        new_input_dir = Path(raw_input_dir) if raw_input_dir else None
        # propagate the latest input_dir to the pages that need it
        self._notes_page.set_input_dir(new_input_dir)
        self._summaries_page.set_input_dir(new_input_dir)
        self._build_page.set_input_dir(new_input_dir)
        self._library_page.refresh()
        self._refresh_status()
