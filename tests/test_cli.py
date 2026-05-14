"""CLI smoke tests (subprocess invocations)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE = Path.home() / "notability-test-data" / "notability_export"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "notability_extractor"] + args,
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_lists_input_dir():
    r = _run(["--help"])
    assert r.returncode == 0
    assert "--input-dir" in r.stdout


@pytest.mark.skipif(sys.platform == "darwin", reason="on macOS the no-args case runs phase 1")
def test_no_args_on_linux_errors_with_helpful_message():
    r = _run([])
    assert r.returncode != 0
    assert "input-dir" in (r.stderr + r.stdout).lower()


@pytest.mark.skipif(not FIXTURE.is_dir(), reason="test fixture not present")
def test_build_from_fixture_writes_all_three_formats(tmp_path: Path):
    r = _run(
        [
            "--input-dir",
            str(FIXTURE),
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "notability_flashcards.apkg").is_file()
    assert (tmp_path / "notability_flashcards.json").is_file()
    assert (tmp_path / "notability_flashcards.md").is_file()


@pytest.mark.skipif(not FIXTURE.is_dir(), reason="test fixture not present")
def test_format_filter_writes_only_json(tmp_path: Path):
    r = _run(
        [
            "--input-dir",
            str(FIXTURE),
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "notability_flashcards.apkg").exists()
    assert (tmp_path / "notability_flashcards.json").is_file()
    assert not (tmp_path / "notability_flashcards.md").exists()


@pytest.mark.skipif(not FIXTURE.is_dir(), reason="test fixture not present")
def test_json_output_round_trips(tmp_path: Path):
    _run(
        [
            "--input-dir",
            str(FIXTURE),
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    data = json.loads((tmp_path / "notability_flashcards.json").read_text())
    assert len(data["cards"]) == 18
    assert len(data["summaries"]) == 3
    assert len(data["notes"]) == 15
