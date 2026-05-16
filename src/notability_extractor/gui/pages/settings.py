"""Settings page: paths, theme, schedule, backup controls."""

# pylint: disable=no-member,too-many-instance-attributes

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from notability_extractor.archive import backup as archive_backup
from notability_extractor.archive import store as archive_store

_CRON_LINE = "0 * * * * notability-extractor --backup"


class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("Archive path:", QLabel(str(archive_store.DEFAULT_ARCHIVE)))

        self._input_dir = QLineEdit()
        pick = QPushButton("Browse...")
        pick.clicked.connect(self._pick_input)
        input_row = QHBoxLayout()
        input_row.addWidget(self._input_dir)
        input_row.addWidget(pick)
        input_w = QWidget()
        input_w.setLayout(input_row)
        form.addRow("Notability input dir:", input_w)

        self._deck_name = QLineEdit("Notability Flashcards")
        form.addRow("Anki deck name:", self._deck_name)

        self._theme = QComboBox()
        self._theme.addItems(["light", "dark", "auto"])
        self._theme.setCurrentText("auto")
        form.addRow("Theme:", self._theme)

        self._cadence = QComboBox()
        self._cadence.addItems(["off", "hourly", "daily", "weekly"])
        form.addRow("Schedule:", self._cadence)

        self._export_dir = QLineEdit(str(Path.home() / "Documents" / "notability-backups"))
        form.addRow("Export dir:", self._export_dir)

        self._retention = QSpinBox()
        self._retention.setRange(1, 100)
        self._retention.setValue(10)
        form.addRow("Keep last N snapshots:", self._retention)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self._backup_btn = QPushButton("Backup now")
        self._backup_btn.clicked.connect(self._do_backup)
        self._restore_btn = QPushButton("Restore from backup...")
        self._restore_btn.clicked.connect(self._do_restore)
        self._export_btn = QPushButton("Export archive...")
        self._export_btn.clicked.connect(self._do_export)
        self._import_btn = QPushButton("Import archive...")
        self._import_btn.clicked.connect(self._do_import)
        for b in (self._backup_btn, self._restore_btn, self._export_btn, self._import_btn):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self._status = QLabel("Last backup: never")
        layout.addWidget(self._status)

        cron = QLabel(f"Headless cadence: copy this into cron/systemd:\n    {_CRON_LINE}")
        cron.setWordWrap(True)
        layout.addWidget(cron)
        layout.addStretch(1)

    def _pick_input(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose Notability input dir")
        if d:
            self._input_dir.setText(d)

    def _do_backup(self) -> None:
        path = archive_backup.snapshot()
        if path:
            self._status.setText(f"Last backup: {path.name}")
        else:
            self._status.setText("Last backup: no changes since last snapshot")

    def _do_restore(self) -> None:
        snaps = archive_backup.list_snapshots()
        if not snaps:
            QMessageBox.information(self, "Restore", "No snapshots available.")
            return
        # simple text-list picker; users on Settings know what they're doing
        names = "\n".join(f"{s.path.name}  ({s.timestamp.isoformat()})" for s in snaps)
        QMessageBox.information(
            self,
            "Restore",
            "Snapshots:\n" + names + "\n\nUse: notability-extractor --import <path>",
        )

    def _do_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export archive",
            "cards.jsonl",
            "JSONL (*.jsonl);;JSON (*.json)",
        )
        if not path:
            return
        fmt: Literal["json", "jsonl"] = "json" if path.endswith(".json") else "jsonl"
        archive_backup.export_archive(Path(path), fmt=fmt)

    def _do_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import archive",
            "",
            "JSONL (*.jsonl);;JSON (*.json)",
        )
        if not path:
            return
        confirm = QMessageBox.question(
            self,
            "Import mode",
            "Merge with existing archive (Yes) or replace it (No)?",
        )
        mode: Literal["merge", "replace"] = (
            "merge" if confirm == QMessageBox.StandardButton.Yes else "replace"
        )
        archive_backup.import_archive(Path(path), mode=mode)
