"""CLI smoke tests (subprocess invocations)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE = Path.home() / "notability-test-data" / "notability_export"


def _run(args: list[str], env_extras: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_extras:
        env.update(env_extras)
    return subprocess.run(
        [sys.executable, "-m", "notability_extractor"] + args,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_help_lists_input_dir():
    r = _run(["--help"])
    assert r.returncode == 0
    assert "--input-dir" in r.stdout
    assert "--edit-flashcards" in r.stdout
    assert "--backup" in r.stdout


@pytest.mark.skipif(sys.platform == "darwin", reason="on macOS the no-args case runs phase 1")
def test_no_args_on_linux_errors_with_helpful_message():
    r = _run([])
    assert r.returncode != 0
    assert "input-dir" in (r.stderr + r.stdout).lower()


@pytest.mark.skipif(not FIXTURE.is_dir(), reason="test fixture not present")
def test_build_from_fixture_writes_outputs(tmp_path: Path):
    archive = tmp_path / ".na" / "cards.jsonl"
    out = tmp_path / "out"
    r = _run(
        [
            "--input-dir",
            str(FIXTURE),
            "--out-dir",
            str(out),
        ],
        env_extras={"NOTABILITY_ARCHIVE": str(archive)},
    )
    assert r.returncode == 0, r.stderr
    assert (out / "notability_flashcards.apkg").is_file()
    assert (out / "notability_flashcards.json").is_file()
    assert (out / "notability_flashcards.md").is_file()
    assert (out / "notability_notes.json").is_file()
    assert (out / "notability_summaries.json").is_file()
    assert archive.is_file()


def test_empty_input_dir_exits_nonzero(tmp_path: Path):
    r = _run(
        [
            "--input-dir",
            str(tmp_path),
            "--out-dir",
            str(tmp_path / "out"),
        ],
        env_extras={"NOTABILITY_ARCHIVE": str(tmp_path / "cards.jsonl")},
    )
    assert r.returncode != 0
    assert "nothing found" in (r.stderr + r.stdout).lower()


def test_list_cards_after_import(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    seed = tmp_path / "seed.jsonl"
    seed.write_text(
        '{"id":"aaa","created_at":"2026-05-15T12:00:00+00:00","updated_at":"2026-05-15T12:00:00+00:00",'
        '"question":"What is X?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct_answer":"A",'
        '"source_file":"x","index":1,"tags":["bio"]}\n'
    )
    r = _run(
        ["--import", str(seed), "--mode", "replace"],
        env_extras={"NOTABILITY_ARCHIVE": str(archive)},
    )
    assert r.returncode == 0, r.stderr
    r = _run(["--list-cards"], env_extras={"NOTABILITY_ARCHIVE": str(archive)})
    assert r.returncode == 0
    assert "What is X?" in r.stdout


def test_backup_creates_snapshot(tmp_path: Path):
    archive = tmp_path / "cards.jsonl"
    backups = tmp_path / "backups"
    seed = tmp_path / "seed.jsonl"
    seed.write_text(
        '{"id":"aaa","created_at":"2026-05-15T12:00:00+00:00","updated_at":"2026-05-15T12:00:00+00:00",'
        '"question":"Q?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct_answer":"A",'
        '"source_file":"x","index":1,"tags":[]}\n'
    )
    _run(
        ["--import", str(seed), "--mode", "replace"],
        env_extras={"NOTABILITY_ARCHIVE": str(archive), "NOTABILITY_BACKUPS": str(backups)},
    )
    r = _run(
        ["--backup"],
        env_extras={"NOTABILITY_ARCHIVE": str(archive), "NOTABILITY_BACKUPS": str(backups)},
    )
    assert r.returncode == 0, r.stderr
    assert list(backups.glob("cards-*.jsonl"))
