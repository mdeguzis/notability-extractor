"""Right-pane editor in the Library page."""

# PySide6 Signals are resolved at runtime via C extensions; pylint cant see
# the .connect() members statically even with extension-pkg-allow-list.
# pylint: disable=no-member

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from notability_extractor.gui.widgets.tag_input import TagInput
from notability_extractor.model import ArchivedCard, Card


class CardEditorWidget(QWidget):  # pylint: disable=too-many-instance-attributes
    saved = Signal(str, Card)
    deleted = Signal(str)

    def __init__(self, known_tags: list[str]) -> None:
        super().__init__()
        self._card_id: str | None = None
        self._known_tags = known_tags

        self._root = QVBoxLayout(self)
        form = QFormLayout()

        self._question = QTextEdit()
        self._question.setFixedHeight(80)
        self._question.textChanged.connect(self._validate)
        form.addRow("Question:", self._question)

        self._option_edits: dict[str, QLineEdit] = {}
        self._correct_radios = QButtonGroup(self)
        for letter in ("A", "B", "C", "D"):
            row = QHBoxLayout()
            radio = QRadioButton(letter)
            radio.setProperty("letter", letter)
            self._correct_radios.addButton(radio)
            edit = QLineEdit()
            edit.textChanged.connect(self._validate)
            row.addWidget(radio)
            row.addWidget(edit)
            container = QWidget()
            container.setLayout(row)
            form.addRow(container)
            self._option_edits[letter] = edit
        self._correct_radios.buttonClicked.connect(lambda *_: self._highlight_correct())

        self._root.addLayout(form)

        self._tags_label = QLabel("Tags:")
        self._root.addWidget(self._tags_label)
        self._tags = TagInput(initial=[], known=known_tags)
        self._root.addWidget(self._tags)

        button_row = QHBoxLayout()
        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._on_save)
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._on_delete)
        button_row.addWidget(self._save_btn)
        button_row.addWidget(self._delete_btn)
        self._root.addLayout(button_row)
        self._root.addStretch(1)

        self._validate()

    def load_card(self, archived: ArchivedCard) -> None:
        self._card_id = archived.id
        self._question.setPlainText(archived.card.question)
        for letter in ("A", "B", "C", "D"):
            self._option_edits[letter].setText(archived.card.options.get(letter, ""))
        for btn in self._correct_radios.buttons():
            btn.setChecked(btn.property("letter") == archived.card.correct_answer)
        # rebuild tag input with this card's tags
        old_index = self._root.indexOf(self._tags)
        self._root.removeWidget(self._tags)
        self._tags.deleteLater()
        self._tags = TagInput(initial=list(archived.card.tags), known=self._known_tags)
        self._root.insertWidget(old_index, self._tags)
        self._highlight_correct()
        self._validate()

    def _validate(self) -> None:
        q = self._question.toPlainText().strip()
        all_options_filled = all(e.text().strip() for e in self._option_edits.values())
        has_correct = self._correct_radios.checkedButton() is not None
        self._save_btn.setEnabled(bool(q) and all_options_filled and has_correct)

    def _highlight_correct(self) -> None:
        correct_btn = self._correct_radios.checkedButton()
        correct_letter = correct_btn.property("letter") if correct_btn is not None else None
        for letter, edit in self._option_edits.items():
            pal = edit.palette()
            is_correct = letter == correct_letter
            pal.setColor(
                QPalette.ColorRole.Base,
                QColor(220, 245, 220) if is_correct else QColor("white"),
            )
            edit.setPalette(pal)

    def _on_save(self) -> None:
        if self._card_id is None:
            return
        correct_btn = self._correct_radios.checkedButton()
        if correct_btn is None:
            return
        new_card = Card(
            question=self._question.toPlainText().strip(),
            options={letter: edit.text().strip() for letter, edit in self._option_edits.items()},
            correct_answer=correct_btn.property("letter"),
            source_file="edited",
            index=0,
            tags=self._tags.tags(),
        )
        self.saved.emit(self._card_id, new_card)

    def _on_delete(self) -> None:
        if self._card_id:
            self.deleted.emit(self._card_id)
