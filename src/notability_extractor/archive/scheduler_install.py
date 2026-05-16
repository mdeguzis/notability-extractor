"""Install / uninstall a periodic 'notability-extractor --backup' job.

Linux: a crontab entry guarded by a marker comment so we can find and
remove our own line later without disturbing the user's existing crontab.

macOS: a LaunchAgent plist at ~/Library/LaunchAgents/. Modern, survives
reboots cleanly, no Full Disk Access dance.

Windows is not supported here. Users on Windows can run --backup from
Task Scheduler manually.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path
from typing import Literal

Cadence = Literal["hourly", "daily", "weekly"]

_CRON_MARKER = "# notability-extractor-backup (managed)"
_LAUNCHD_LABEL = "com.local.notability-extractor-backup"
# public so settings.py can display the path without a protected-access warning
LAUNCHD_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{_LAUNCHD_LABEL}.plist"


def system_supported() -> bool:
    return platform.system() in {"Linux", "Darwin"}


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_linux() -> bool:
    return platform.system() == "Linux"


def binary_path() -> str:
    found = shutil.which("notability-extractor")
    return found if found else "notability-extractor"


def cron_line(cadence: Cadence) -> str:
    schedule = {
        "hourly": "0 * * * *",
        "daily": "0 9 * * *",
        "weekly": "0 9 * * 0",
    }[cadence]
    return f"{schedule} {binary_path()} --backup"


def launchd_plist(cadence: Cadence) -> str:
    if cadence == "hourly":
        cal = "<dict><key>Minute</key><integer>0</integer></dict>"
    elif cadence == "daily":
        cal = (
            "<dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>"
        )
    else:  # weekly
        cal = (
            "<dict><key>Weekday</key><integer>0</integer>"
            "<key>Hour</key><integer>9</integer>"
            "<key>Minute</key><integer>0</integer></dict>"
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{_LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{binary_path()}</string>
        <string>--backup</string>
    </array>
    <key>StartCalendarInterval</key>
    {cal}
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
"""


def install(cadence: Cadence) -> tuple[bool, str]:
    """Install (or replace) the periodic backup job. Returns (ok, message)."""
    if is_macos():
        return _install_launchd(cadence)
    if is_linux():
        return _install_cron(cadence)
    return False, f"Unsupported platform: {platform.system()}"


def uninstall() -> tuple[bool, str]:
    """Remove the installed job. Returns (ok, message). Idempotent."""
    if is_macos():
        return _uninstall_launchd()
    if is_linux():
        return _uninstall_cron()
    return False, f"Unsupported platform: {platform.system()}"


def is_installed() -> bool:
    if is_macos():
        return LAUNCHD_PLIST.is_file()
    if is_linux():
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
        return _CRON_MARKER in (result.stdout or "")
    return False


def _install_cron(cadence: Cadence) -> tuple[bool, str]:
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    existing = current.stdout if current.returncode == 0 else ""
    filtered = _strip_managed_block(existing)
    new_block = f"{_CRON_MARKER}\n{cron_line(cadence)}\n"
    combined = (filtered.rstrip() + "\n\n" + new_block) if filtered.strip() else new_block
    result = subprocess.run(
        ["crontab", "-"], input=combined, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        return False, f"crontab install failed: {result.stderr.strip()}"
    return True, f"Installed cron: {cron_line(cadence)}"


def _uninstall_cron() -> tuple[bool, str]:
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    if current.returncode != 0:
        return True, "No crontab to clean up"
    filtered = _strip_managed_block(current.stdout)
    result = subprocess.run(
        ["crontab", "-"], input=filtered + "\n", text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        return False, f"crontab update failed: {result.stderr.strip()}"
    return True, "Removed scheduled backup from crontab"


def _strip_managed_block(crontab_text: str) -> str:
    """Remove the marker line and the line directly after it."""
    out: list[str] = []
    skip = False
    for line in crontab_text.splitlines():
        if skip:
            skip = False
            continue
        if _CRON_MARKER in line:
            skip = True
            continue
        out.append(line)
    return "\n".join(out)


def _install_launchd(cadence: Cadence) -> tuple[bool, str]:
    LAUNCHD_PLIST.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHD_PLIST.write_text(launchd_plist(cadence))
    # unload any prior version so reload picks up the new plist
    subprocess.run(
        ["launchctl", "unload", str(LAUNCHD_PLIST)],
        capture_output=True,
        check=False,
    )
    result = subprocess.run(
        ["launchctl", "load", str(LAUNCHD_PLIST)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False, f"launchctl load failed: {result.stderr.strip()}"
    return True, f"Installed LaunchAgent at {LAUNCHD_PLIST}"


def _uninstall_launchd() -> tuple[bool, str]:
    if not LAUNCHD_PLIST.is_file():
        return True, "No LaunchAgent to clean up"
    subprocess.run(
        ["launchctl", "unload", str(LAUNCHD_PLIST)],
        capture_output=True,
        check=False,
    )
    LAUNCHD_PLIST.unlink()
    return True, "Removed scheduled backup LaunchAgent"
