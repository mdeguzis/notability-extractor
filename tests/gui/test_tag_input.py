"""Tests for the TagInput chip widget."""

# tests poke at private widget members to drive behavior without adding public test hooks
# pylint: disable=protected-access

from PySide6.QtCore import Qt

from notability_extractor.gui.widgets.tag_input import TagInput


def test_initial_tags_set_from_constructor(qtbot):
    w = TagInput(initial=["biology", "midterm"], known=[])
    qtbot.addWidget(w)
    assert w.tags() == ["biology", "midterm"]


def test_typing_and_enter_adds_tag(qtbot):
    w = TagInput(initial=[], known=[])
    qtbot.addWidget(w)
    w._entry.setText("history")
    qtbot.keyPress(w._entry, Qt.Key.Key_Return)
    assert "history" in w.tags()


def test_typing_normalizes_whitespace(qtbot):
    w = TagInput(initial=[], known=[])
    qtbot.addWidget(w)
    w._entry.setText("  biology   midterm  ")
    qtbot.keyPress(w._entry, Qt.Key.Key_Return)
    assert w.tags() == ["biology midterm"]


def test_typing_preserves_case(qtbot):
    w = TagInput(initial=[], known=[])
    qtbot.addWidget(w)
    w._entry.setText("Biology")
    qtbot.keyPress(w._entry, Qt.Key.Key_Return)
    assert w.tags() == ["Biology"]
