"""Smoke tests for the GUI app entry."""

# pylint: disable=import-outside-toplevel
import os


def test_wayland_detected_when_only_wayland_display_set(monkeypatch):
    from notability_extractor.gui.app import _set_wayland_if_needed

    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    _set_wayland_if_needed()
    assert os.environ.get("QT_QPA_PLATFORM") == "wayland"


def test_wayland_not_set_when_display_present(monkeypatch):
    from notability_extractor.gui.app import _set_wayland_if_needed

    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    _set_wayland_if_needed()
    assert "QT_QPA_PLATFORM" not in os.environ


def test_app_constructs_and_closes(qtbot):
    from notability_extractor.gui.app import build_app

    _app, window = build_app(headless=True)
    qtbot.addWidget(window)
    assert window.windowTitle() == "Notability Extractor"
    window.close()
