"""Tests for archive.scheduler_install."""

from unittest.mock import MagicMock, patch

from notability_extractor.archive import scheduler_install


def test_cron_line_hourly_includes_managed_marker_absent():
    # the line itself doesn't carry the marker (that's separate). Just
    # check format is correct.
    line = scheduler_install.cron_line("hourly")
    assert line.startswith("0 * * * *")
    assert "--backup" in line


def test_cron_line_daily_9am():
    assert scheduler_install.cron_line("daily").startswith("0 9 * * *")


def test_cron_line_weekly_sunday_9am():
    assert scheduler_install.cron_line("weekly").startswith("0 9 * * 0")


def test_launchd_plist_hourly_has_minute_0():
    plist = scheduler_install.launchd_plist("hourly")
    assert "<key>Minute</key><integer>0</integer>" in plist
    assert "<key>StartCalendarInterval</key>" in plist


def test_launchd_plist_daily_has_hour_9():
    plist = scheduler_install.launchd_plist("daily")
    assert "<key>Hour</key><integer>9</integer>" in plist


def test_launchd_plist_weekly_has_weekday_0():
    plist = scheduler_install.launchd_plist("weekly")
    assert "<key>Weekday</key><integer>0</integer>" in plist


def test_strip_managed_block_removes_marker_and_following_line():
    text = (
        "MAILTO=me\n"
        "0 0 * * * /other/job\n"
        "# notability-extractor-backup (managed)\n"
        "0 * * * * /path/to/notability-extractor --backup\n"
        "30 * * * * /yet/another\n"
    )
    out = scheduler_install._strip_managed_block(text)  # pylint: disable=protected-access
    assert "notability-extractor" not in out
    assert "MAILTO=me" in out
    assert "/other/job" in out
    assert "/yet/another" in out


def test_strip_managed_block_handles_empty():
    assert scheduler_install._strip_managed_block("") == ""  # pylint: disable=protected-access


def test_install_unsupported_platform():
    with patch.object(scheduler_install.platform, "system", return_value="Plan9"):
        ok, msg = scheduler_install.install("hourly")
    assert not ok
    assert "Unsupported" in msg


def test_install_cron_calls_crontab(monkeypatch):
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        if args[0] == ["crontab", "-l"]:
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            return mock
        # crontab -
        mock = MagicMock()
        mock.returncode = 0
        mock.stderr = ""
        return mock

    monkeypatch.setattr(scheduler_install.platform, "system", lambda: "Linux")
    monkeypatch.setattr(scheduler_install.subprocess, "run", fake_run)
    ok, _ = scheduler_install.install("hourly")
    assert ok
    # one read + one write
    assert len(calls) == 2
    # the second call should have the new line in stdin
    _, kwargs = calls[1]
    assert "--backup" in kwargs["input"]


def test_uninstall_cron_idempotent(monkeypatch):
    def fake_run(*args, **_kwargs):
        if args[0] == ["crontab", "-l"]:
            mock = MagicMock()
            mock.returncode = 1  # no crontab
            mock.stdout = ""
            return mock
        return MagicMock(returncode=0)

    monkeypatch.setattr(scheduler_install.platform, "system", lambda: "Linux")
    monkeypatch.setattr(scheduler_install.subprocess, "run", fake_run)
    ok, msg = scheduler_install.uninstall()
    assert ok
    assert "No crontab" in msg
