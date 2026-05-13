"""Tests for notability_extractor.discovery."""

from pathlib import Path

import pytest

from notability_extractor.discovery import candidate_dirs, find_db


class TestFindDb:
    def test_returns_path_when_hint_is_valid_file(self, tmp_path: Path):
        db = tmp_path / "test.sqlite"
        db.touch()
        result = find_db(str(db))
        assert result == db

    def test_returns_none_when_hint_path_missing(self, tmp_path: Path):
        result = find_db(str(tmp_path / "nonexistent.sqlite"))
        assert result is None

    def test_discovers_sqlite_in_candidate_dir(self, tmp_path: Path, monkeypatch):
        # Patch _CANDIDATE_DIRS to point at our temp directory
        fake_db = tmp_path / "Notability.sqlite"
        fake_db.touch()

        monkeypatch.setattr(
            "notability_extractor.discovery._CANDIDATE_DIRS", [str(tmp_path)]
        )
        result = find_db()
        assert result == fake_db

    def test_returns_none_when_no_candidates_exist(self, monkeypatch):
        monkeypatch.setattr(
            "notability_extractor.discovery._CANDIDATE_DIRS",
            ["/nonexistent/path/that/cannot/exist"],
        )
        result = find_db()
        assert result is None

    def test_ignores_non_sqlite_files(self, tmp_path: Path, monkeypatch):
        (tmp_path / "notes.txt").touch()
        (tmp_path / "data.db").touch()
        monkeypatch.setattr(
            "notability_extractor.discovery._CANDIDATE_DIRS", [str(tmp_path)]
        )
        result = find_db()
        assert result is None

    def test_prefers_first_candidate_dir(self, tmp_path: Path, monkeypatch):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        db_a = dir_a / "Notability.sqlite"
        db_b = dir_b / "Notability.sqlite"
        db_a.touch()
        db_b.touch()
        monkeypatch.setattr(
            "notability_extractor.discovery._CANDIDATE_DIRS",
            [str(dir_a), str(dir_b)],
        )
        result = find_db()
        assert result == db_a


class TestCandidateDirs:
    def test_returns_list_of_paths(self):
        dirs = candidate_dirs()
        assert isinstance(dirs, list)
        assert all(isinstance(d, Path) for d in dirs)

    def test_not_empty(self):
        assert len(candidate_dirs()) > 0
