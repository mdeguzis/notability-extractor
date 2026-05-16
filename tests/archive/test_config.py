"""Tests for archive.config."""

from pathlib import Path

import pytest

from notability_extractor.archive import config


def test_load_returns_defaults_when_missing(tmp_path: Path) -> None:
    cfg = config.load(tmp_path / "config.json")
    assert cfg["theme"] == "auto"
    assert cfg["schedule"] == "off"
    assert cfg["retention"] == 10


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    config.save({"theme": "dark", "deck_name": "Custom"}, path)
    loaded = config.load(path)
    assert loaded["theme"] == "dark"
    assert loaded["deck_name"] == "Custom"
    # defaults still present for keys not saved
    assert loaded["schedule"] == "off"


def test_load_corrupt_falls_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{not valid json")
    cfg = config.load(path)
    assert cfg["theme"] == "auto"


def test_load_tolerates_extra_keys(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"theme":"dark","unknown_future_key":42}')
    cfg = config.load(path)
    assert cfg["theme"] == "dark"
    assert cfg["unknown_future_key"] == 42


def test_set_value_persists_one_key(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    config.set_value("theme", "dark", path)
    assert config.get("theme", path) == "dark"


def test_save_is_atomic_keeps_old_on_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.json"
    config.save({"theme": "light"}, path)
    original = path.read_text()

    def boom(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("os.replace", boom)
    with pytest.raises(OSError):
        config.save({"theme": "dark"}, path)
    assert path.read_text() == original
