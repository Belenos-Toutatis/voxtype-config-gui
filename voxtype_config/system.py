"""Interactions avec le système : daemon systemd, détection de VoxType."""

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
    """Redémarre le service utilisateur voxtype. Renvoie (succès, message)."""
    try:
        res = subprocess.run(
            ["systemctl", "--user", "restart", "voxtype"],
            capture_output=True, text=True, timeout=30,
        )
        if res.returncode == 0:
            return True, "Daemon VoxType redémarré."
        return False, res.stderr.strip() or "Échec du redémarrage."
    except FileNotFoundError:
        return False, "systemctl introuvable."
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
