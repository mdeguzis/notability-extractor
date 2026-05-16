"""Tests for CardEditorWidget."""

# tests poke at private widget members to drive behavior without adding public test hooks
# pylint: disable=protected-access

from datetime import UTC, datetime

from notability_extractor.gui.widgets.card_editor import CardEditorWidget
from notability_extractor.model import ArchivedCard, Card


def _ac(q: str, options: dict[str, str] | None = None) -> ArchivedCard:
    card = Card(
        question=q,
        options=options or {"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_answer="A",
        source_file="x",
        index=1,
    )
    now = datetime(2026, 5, 15, tzinfo=UTC)
    return ArchivedCard(card=card, id="abc", created_at=now, updated_at=now)


def test_loads_card_into_fields(qtbot):
    w = CardEditorWidget(known_tags=[])
    qtbot.addWidget(w)
    w.load_card(_ac("Capital of France?"))
    assert w._question.toPlainText() == "Capital of France?"


def test_save_button_disabled_when_question_blank(qtbot):
    w = CardEditorWidget(known_tags=[])
    qtbot.addWidget(w)
    w.load_card(_ac(""))
    assert not w._save_btn.isEnabled()


def test_save_button_enabled_when_all_fields_valid(qtbot):
    w = CardEditorWidget(known_tags=[])
    qtbot.addWidget(w)
    w.load_card(_ac("Q?"))
    assert w._save_btn.isEnabled()


def test_save_emits_card_with_edits(qtbot):
    w = CardEditorWidget(known_tags=[])
    qtbot.addWidget(w)
    w.load_card(_ac("Original?"))
    w._question.setPlainText("Edited?")
    captured: list = []
    w.saved.connect(lambda card_id, card: captured.append(card))
    with qtbot.waitSignal(w.saved, timeout=1000):
        w._save_btn.click()
    assert captured[0].question == "Edited?"
