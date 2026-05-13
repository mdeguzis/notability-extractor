"""Tests for notability_extractor.discovery."""

from pathlib import Path

from notability_extractor.discovery import candidate_dirs, find_db, find_note_dirs


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

        monkeypatch.setattr("notability_extractor.discovery._CANDIDATE_DIRS", [str(tmp_path)])
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
        monkeypatch.setattr("notability_extractor.discovery._CANDIDATE_DIRS", [str(tmp_path)])
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


class TestFindNoteDirsOverride:
    def test_override_returns_only_override(self, tmp_path: Path):
        # tmp_path exists and is a directory, so it should be returned as-is
        result = find_note_dirs(override=tmp_path)
        assert result == [tmp_path]

    def test_missing_override_returns_empty(self, tmp_path: Path):
        bad = tmp_path / "does_not_exist"
        result = find_note_dirs(override=bad)
        assert not result

    def test_file_as_override_returns_empty(self, tmp_path: Path):
        # passing a file instead of a directory should be rejected
        f = tmp_path / "a_file.txt"
        f.touch()
        result = find_note_dirs(override=f)
        assert not result


class TestFindDbSearchRoot:
    def test_search_root_finds_sqlite_inside(self, tmp_path: Path):
        # drop a .sqlite file under tmp_path and confirm it gets found
        db = tmp_path / "notes.sqlite"
        db.touch()
        result = find_db(hint=None, search_root=tmp_path)
        assert result == db

    def test_hint_wins_over_search_root(self, tmp_path: Path):
        # when both are given, the explicit --db (hint) takes precedence
        hint_db = tmp_path / "explicit.sqlite"
        hint_db.touch()
        root_db = tmp_path / "subdir"
        root_db.mkdir()
        (root_db / "other.sqlite").touch()
        result = find_db(hint=str(hint_db), search_root=root_db)
        assert result == hint_db

    def test_missing_search_root_returns_none(self, tmp_path: Path):
        bad = tmp_path / "nope"
        result = find_db(hint=None, search_root=bad)
        assert result is None
