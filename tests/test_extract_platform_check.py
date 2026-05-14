"""Tests for platform_check helpers."""

from pathlib import Path
from unittest.mock import patch

from notability_extractor.extract.platform_check import (
    default_cache_dir,
    default_input_dir,
    default_notes_dir,
    is_macos,
)


def test_is_macos_returns_bool():
    assert isinstance(is_macos(), bool)


def test_default_notes_dir_uses_icloud_team_prefix():
    p = default_notes_dir()
    assert "ZP9ZJ4EF3S~com~gingerlabs~Notability" in str(p)


def test_default_cache_dir_under_containers():
    p = default_cache_dir()
    assert "Containers/com.gingerlabs.Notability" in str(p)


def test_default_input_dir_in_home():
    p = default_input_dir()
    assert p == Path.home() / "notability_export"


@patch("sys.platform", "darwin")
def test_is_macos_true_on_darwin():
    assert is_macos() is True


@patch("sys.platform", "linux")
def test_is_macos_false_on_linux():
    assert is_macos() is False
