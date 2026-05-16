"""Cadence-driven backup scheduler.

The driver protocol lets the GUI swap in a QTimer-backed implementation while
tests use a manual-tick fake. The scheduler itself doesn't import Qt.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, Protocol

Cadence = Literal["off", "hourly", "daily", "weekly"]

_CADENCE_SECONDS: dict[str, int] = {
    "hourly": 3600,
    "daily": 86400,
    "weekly": 604800,
}


def cadence_to_seconds(cadence: Cadence) -> int | None:
    """Map cadence to interval in seconds. 'off' returns None."""
    return _CADENCE_SECONDS.get(cadence)


class TimerDriver(Protocol):
    """The bit of QTimer's surface the scheduler depends on."""

    def configure(self, interval_s: int, on_tick: Callable[[], None]) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...


class BackupScheduler:
    """Calls on_fire at the configured cadence. last_run_at tracks the last tick."""

    def __init__(
        self,
        cadence: Cadence,
        on_fire: Callable[[], None],
        driver: TimerDriver,
    ) -> None:
        self._cadence: Cadence = cadence
        self._on_fire = on_fire
        self._driver = driver
        self._last_run_at: datetime | None = None

    def start(self) -> None:
        seconds = cadence_to_seconds(self._cadence)
        if seconds is None:
            return
        self._driver.configure(seconds, self._tick)
        self._driver.start()

    def stop(self) -> None:
        self._driver.stop()

    @property
    def last_run_at(self) -> datetime | None:
        return self._last_run_at

    def _tick(self) -> None:
        self._on_fire()
        self._last_run_at = datetime.now(UTC)
