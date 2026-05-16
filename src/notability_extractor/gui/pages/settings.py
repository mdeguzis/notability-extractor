"""Settings page: paths, theme, schedule, backup controls, extraction."""

# pylint: disable=no-member,too-many-instance-attributes,too-many-statements

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PySide6.QtWidgets import (
    QApplication,
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
from notability_extractor.archive import config as archive_config
from notability_extractor.archive import scheduler_install
from notability_extractor.archive import store as archive_store
from notability_extractor.build.reader import read_input_dir
from notability_extractor.extract.platform_check import is_macos
from notability_extractor.gui.theme import apply_theme


class SettingsPage(QWidget):
    def __init__(self, on_archive_changed: object = None) -> None:
        super().__init__()
        self._cfg = archive_config.load()
        # fired after Pull / Import / Restore so MainWindow can refresh the
        # other pages and the status bar. None is a no-op for standalone use.
        self._on_archive_changed = on_archive_changed if callable(on_archive_changed) else None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("Archive path:", QLabel(str(archive_store.DEFAULT_ARCHIVE)))

        # --- Extraction location ---
        self._input_dir = QLineEdit(self._cfg.get("input_dir", ""))
        self._input_dir.editingFinished.connect(self._on_input_dir_changed)
        pick = QPushButton("Browse...")
        pick.clicked.connect(self._pick_input)
        input_row = QHBoxLayout()
        input_row.addWidget(self._input_dir)
        input_row.addWidget(pick)
        input_w = QWidget()
        input_w.setLayout(input_row)
        form.addRow("Extraction location:", input_w)

        self._pull_btn = QPushButton("Pull new cards from Notability")
        self._pull_btn.clicked.connect(self._on_pull)
        form.addRow("", self._pull_btn)

        # macOS-only: run the full extract phase, then pull
        self._extract_btn: QPushButton | None = None
        if is_macos():
            self._extract_btn = QPushButton("Run macOS extraction now")
            self._extract_btn.clicked.connect(self._on_macos_extract)
            form.addRow("", self._extract_btn)

        self._pull_status = QLabel("")
        self._pull_status.setWordWrap(True)
        form.addRow("", self._pull_status)

        # --- Deck name ---
        self._deck_name = QLineEdit(self._cfg.get("deck_name", "Notability Flashcards"))
        self._deck_name.editingFinished.connect(
            lambda: self._save_field("deck_name", self._deck_name.text())
        )
        form.addRow("Anki deck name:", self._deck_name)

        # --- Theme: change is applied live, no restart needed ---
        self._theme = QComboBox()
        self._theme.addItems(["light", "dark", "auto"])
        self._theme.setCurrentText(self._cfg.get("theme", "auto"))
        self._theme.currentTextChanged.connect(self._on_theme_changed)
        form.addRow("Theme:", self._theme)

        # --- Schedule ---
        self._cadence = QComboBox()
        self._cadence.addItems(["off", "hourly", "daily", "weekly"])
        self._cadence.setCurrentText(self._cfg.get("schedule", "off"))
        self._cadence.currentTextChanged.connect(lambda v: self._save_field("schedule", v))
        form.addRow("Schedule:", self._cadence)

        self._export_dir = QLineEdit(
            self._cfg.get("export_dir", str(Path.home() / "Documents" / "notability-backups"))
        )
        self._export_dir.editingFinished.connect(
            lambda: self._save_field("export_dir", self._export_dir.text())
        )
        form.addRow("Export dir:", self._export_dir)

        self._retention = QSpinBox()
        self._retention.setRange(1, 100)
        self._retention.setValue(int(self._cfg.get("retention", 10)))
        self._retention.valueChanged.connect(lambda v: self._save_field("retention", int(v)))
        form.addRow("Keep last N snapshots:", self._retention)

        layout.addLayout(form)

        # --- Backup controls ---
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

        # --- Schedule installation (platform-aware) ---
        if scheduler_install.system_supported():
            sched_row = QHBoxLayout()
            self._install_schedule_btn = QPushButton("Install schedule")
            self._install_schedule_btn.clicked.connect(self._do_install_schedule)
            self._remove_schedule_btn = QPushButton("Remove schedule")
            self._remove_schedule_btn.clicked.connect(self._do_uninstall_schedule)
            sched_row.addWidget(self._install_schedule_btn)
            sched_row.addWidget(self._remove_schedule_btn)
            layout.addLayout(sched_row)

            self._schedule_status = QLabel()
            self._schedule_status.setWordWrap(True)
            layout.addWidget(self._schedule_status)
            self._refresh_schedule_status()
        else:
            fallback = QLabel(
                "Scheduled backups: install your platform's equivalent of "
                "`notability-extractor --backup` (manual)."
            )
            fallback.setWordWrap(True)
            layout.addWidget(fallback)

        layout.addStretch(1)

    # --- save helpers ---

    def _save_field(self, key: str, value: object) -> None:
        archive_config.set_value(key, value)

    def _on_input_dir_changed(self) -> None:
        self._save_field("input_dir", self._input_dir.text())

    def _on_theme_changed(self, new_theme: str) -> None:
        self._save_field("theme", new_theme)
        app = QApplication.instance()
        if app is not None:
            # cast is safe: QCoreApplication.instance() returns QApplication here
            apply_theme(app, new_theme)  # type: ignore[arg-type]

    def _pick_input(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose extraction location")
        if d:
            self._input_dir.setText(d)
            self._save_field("input_dir", d)

    # --- extraction actions ---

    def _on_pull(self) -> None:
        input_dir = (self._input_dir.text() or "").strip()
        if not input_dir or not Path(input_dir).is_dir():
            self._pull_status.setText("Set a valid extraction location first.")
            return
        try:
            deck = read_input_dir(Path(input_dir))
        except (OSError, ValueError) as exc:
            self._pull_status.setText(f"Read failed: {exc}")
            return
        added, skipped = archive_store.merge(deck.cards)
        archive_backup.snapshot()
        self._pull_status.setText(
            f"Pulled {added} new cards ({skipped} already known). "
            f"{len(deck.notes)} notes, {len(deck.summaries)} summaries available."
        )
        if self._on_archive_changed is not None:
            self._on_archive_changed()

    def _on_macos_extract(self) -> None:
        # pylint: disable=import-outside-toplevel
        from notability_extractor.extract.exporter import run_extract
        from notability_extractor.extract.platform_check import (
            default_cache_dir,
            default_input_dir,
            default_notes_dir,
        )

        target = default_input_dir()
        try:
            run_extract(default_notes_dir(), default_cache_dir(), target)
        except OSError as exc:
            self._pull_status.setText(f"Extract failed: {exc}")
            return
        self._input_dir.setText(str(target))
        self._save_field("input_dir", str(target))
        self._on_pull()

    # --- backup buttons ---

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
        if self._on_archive_changed is not None:
            self._on_archive_changed()

    # --- schedule install/remove ---

    def _refresh_schedule_status(self) -> None:
        if scheduler_install.is_installed():
            if scheduler_install.is_macos():
                line = "LaunchAgent at " + str(scheduler_install.LAUNCHD_PLIST)
            else:
                line = scheduler_install.cron_line(self._current_cadence_for_install())
            self._schedule_status.setText(f"Schedule installed -> {line}")
        else:
            self._schedule_status.setText(
                "Schedule not installed. Pick a cadence above, then click Install schedule."
            )

    def _current_cadence_for_install(self) -> scheduler_install.Cadence:
        val = self._cadence.currentText()
        if val == "off":
            return "daily"  # fallback for status display only
        # the combobox only has off/hourly/daily/weekly so this cast is safe
        return val  # type: ignore[return-value]

    def _do_install_schedule(self) -> None:
        cadence = self._cadence.currentText()
        if cadence == "off":
            QMessageBox.warning(
                self,
                "Pick a cadence",
                "Set Schedule to hourly / daily / weekly first, then click Install schedule.",
            )
            return
        # cadence is one of the valid Literal values at this point
        _, msg = scheduler_install.install(cadence)  # type: ignore[arg-type]
        QMessageBox.information(self, "Install schedule", msg)
        self._refresh_schedule_status()

    def _do_uninstall_schedule(self) -> None:
        _, msg = scheduler_install.uninstall()
        QMessageBox.information(self, "Remove schedule", msg)
        self._refresh_schedule_status()
