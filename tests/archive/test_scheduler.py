"""Tests for archive.scheduler. Uses a fake timer driver to avoid wall-clock waits."""

from unittest.mock import Mock

from notability_extractor.archive.scheduler import BackupScheduler, cadence_to_seconds


def test_cadence_to_seconds_known_values():
    assert cadence_to_seconds("off") is None
    assert cadence_to_seconds("hourly") == 3600
    assert cadence_to_seconds("daily") == 86400
    assert cadence_to_seconds("weekly") == 604800


def test_scheduler_off_does_not_fire():
    on_fire = Mock()
    sched = BackupScheduler(cadence="off", on_fire=on_fire, driver=_FakeDriver())
    sched.start()
    assert on_fire.call_count == 0
    assert sched.last_run_at is None


def test_scheduler_calls_callback_on_tick():
    on_fire = Mock()
    driver = _FakeDriver()
    sched = BackupScheduler(cadence="hourly", on_fire=on_fire, driver=driver)
    sched.start()
    driver.tick()
    assert on_fire.call_count == 1
    assert sched.last_run_at is not None


def test_scheduler_stop_prevents_further_calls():
    on_fire = Mock()
    driver = _FakeDriver()
    sched = BackupScheduler(cadence="hourly", on_fire=on_fire, driver=driver)
    sched.start()
    sched.stop()
    driver.tick()
    assert on_fire.call_count == 0


class _FakeDriver:
    def __init__(self) -> None:
        self._cb = None
        self._interval = 0
        self._running = False

    def configure(self, interval_s, on_tick):
        self._interval = interval_s
        self._cb = on_tick

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def tick(self) -> None:
        if self._running and self._cb is not None:
            self._cb()
