"""Export page: write the archive out to apkg / json / md files."""

# pylint: disable=no-member,too-many-instance-attributes

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from notability_extractor.archive import config as archive_config
from notability_extractor.archive import store as archive_store
from notability_extractor.build import flashcards, notes, summaries
from notability_extractor.build.reader import read_input_dir
from notability_extractor.utils import get_logger

log = get_logger(__name__)


class ExportPage(QWidget):
    def __init__(self, input_dir: Path | None = None) -> None:
        super().__init__()
        self._input_dir = input_dir

        layout = QVBoxLayout(self)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output dir:"))
        saved_out = archive_config.get("output_dir")
        self._out = QLineEdit(saved_out if isinstance(saved_out, str) and saved_out else ".")
        self._out.editingFinished.connect(self._save_output_dir)
        out_row.addWidget(self._out, 1)
        pick = QPushButton("Browse...")
        pick.clicked.connect(self._pick_out)
        out_row.addWidget(pick)
        layout.addLayout(out_row)

        formats = QGroupBox("Formats")
        f_layout = QVBoxLayout()
        self._cb_apkg = QCheckBox("Flashcards .apkg")
        self._cb_apkg.setChecked(True)
        self._cb_fjson = QCheckBox("Flashcards .json")
        self._cb_fjson.setChecked(True)
        self._cb_fmd = QCheckBox("Flashcards .md")
        self._cb_fmd.setChecked(True)
        self._cb_njson = QCheckBox("Notes .json")
        self._cb_njson.setChecked(True)
        self._cb_nmd = QCheckBox("Notes .md")
        self._cb_nmd.setChecked(True)
        self._cb_sjson = QCheckBox("Summaries .json")
        self._cb_sjson.setChecked(True)
        self._cb_smd = QCheckBox("Summaries .md")
        self._cb_smd.setChecked(True)
        for cb in (
            self._cb_apkg,
            self._cb_fjson,
            self._cb_fmd,
            self._cb_njson,
            self._cb_nmd,
            self._cb_sjson,
            self._cb_smd,
        ):
            f_layout.addWidget(cb)
        formats.setLayout(f_layout)
        layout.addWidget(formats)

        run = QPushButton("Export")
        run.clicked.connect(self._build)
        layout.addWidget(run)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout.addWidget(self._log, 1)

    def _pick_out(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose output directory")
        if d:
            self._out.setText(d)
            self._save_output_dir()

    def _save_output_dir(self) -> None:
        archive_config.set_value("output_dir", self._out.text() or ".")

    def set_input_dir(self, input_dir: Path | None) -> None:
        """Update the source dir (called by MainWindow after Settings changes)."""
        self._input_dir = input_dir

    def _build(self) -> None:
        out_dir = Path(self._out.text()).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        cards = archive_store.load()
        log.info("export: writing to %s, %d cards in archive", out_dir, len(cards))
        self._log.append(f"Loaded {len(cards)} cards from archive.")
        if self._cb_apkg.isChecked():
            flashcards.write_apkg(
                cards,
                out_dir / "notability_flashcards.apkg",
                deck_name="Notability Flashcards",
            )
            self._log.append("wrote notability_flashcards.apkg")
        if self._cb_fjson.isChecked():
            flashcards.write_json(cards, out_dir / "notability_flashcards.json")
            self._log.append("wrote notability_flashcards.json")
        if self._cb_fmd.isChecked():
            flashcards.write_md(cards, out_dir / "notability_flashcards.md")
            self._log.append("wrote notability_flashcards.md")
        if self._input_dir and Path(self._input_dir).is_dir():
            deck = read_input_dir(self._input_dir)
            if self._cb_njson.isChecked():
                notes.write_json(deck.notes, out_dir / "notability_notes.json")
                self._log.append(f"wrote notability_notes.json ({len(deck.notes)} notes)")
            if self._cb_nmd.isChecked():
                notes.write_md(deck.notes, out_dir / "notability_notes.md")
                self._log.append("wrote notability_notes.md")
            if self._cb_sjson.isChecked():
                summaries.write_json(deck.summaries, out_dir / "notability_summaries.json")
                self._log.append(
                    f"wrote notability_summaries.json ({len(deck.summaries)} summaries)"
                )
            if self._cb_smd.isChecked():
                summaries.write_md(deck.summaries, out_dir / "notability_summaries.md")
                self._log.append("wrote notability_summaries.md")
        else:
            log.info("export: no input_dir set, skipping notes/summaries")
            self._log.append("(no input dir set; skipping notes/summaries)")
        log.info("export complete: out_dir=%s", out_dir)
