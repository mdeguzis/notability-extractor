"""Tests for the Library page."""

# tests poke at private widget members to drive behavior without adding public test hooks
# pylint: disable=protected-access

from pathlib import Path

from notability_extractor.archive import store
from notability_extractor.gui.pages.library import LibraryPage
from notability_extractor.model import Card


def _seed(archive_path: Path) -> None:
    store.save_all([], archive_path)
    for i, (q, tags) in enumerate(
        [
            ("Capital of France?", ["geography"]),
            ("Photosynthesis?", ["biology"]),
            ("Pythagoras?", ["math", "geometry"]),
        ]
    ):
        store.add(
            Card(
                question=q,
                options={"A": "a", "B": "b", "C": "c", "D": "d"},
                correct_answer="A",
                source_file="x",
                index=i,
                tags=tags,
            ),
            archive_path,
        )


def test_library_lists_all_cards(qtbot, tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    _seed(archive)
    page = LibraryPage(archive_path=archive)
    qtbot.addWidget(page)
    assert page._table.rowCount() == 3


def test_filter_by_text_narrows_list(qtbot, tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    _seed(archive)
    page = LibraryPage(archive_path=archive)
    qtbot.addWidget(page)
    page._search.setText("photo")
    page._on_filter_changed("photo")
    assert page._table.rowCount() == 1
