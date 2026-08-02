"""System interactions: systemd daemon, VoxType detection."""

from __future__ import annotations

import shutil
import subprocess


def voxtype_installed() -> bool:
    return shutil.which("voxtype") is not None


def daemon_is_active() -> bool:
    try:
        res = subprocess.run(
            ["systemctl", "--user", "is-active", "voxtype"],
            capture_output=True, text=True, timeout=5,
        )
        return res.stdout.strip() == "active"
    except Exception:
        return False


def restart_daemon() -> tuple[bool, str]:
    """Restarts the voxtype user service. Returns (success, message)."""
    try:
        res = subprocess.run(
            ["systemctl", "--user", "restart", "voxtype"],
            capture_output=True, text=True, timeout=30,
        )
        if res.returncode == 0:
            return True, "VoxType daemon restarted."
        return False, res.stderr.strip() or "Restart failed."
    except FileNotFoundError:
        return False, "systemctl not found."
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def daemon_service_exists() -> bool:
    try:
        res = subprocess.run(
            ["systemctl", "--user", "list-unit-files", "voxtype.service"],
            capture_output=True, text=True, timeout=5,
        )
        return "voxtype.service" in res.stdout
    except Exception:
        return False
