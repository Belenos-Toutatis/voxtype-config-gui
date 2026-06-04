"""Lecture / écriture du config.toml de VoxType en préservant commentaires et ordre.

S'appuie sur tomlkit : on charge le document existant, on ne modifie que les
valeurs touchées par l'utilisateur, et on réécrit le fichier à l'identique pour
tout le reste (commentaires, ordre des clés, mise en forme).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import tomlkit
from tomlkit import TOMLDocument


def default_config_path() -> Path:
    """Chemin standard du config.toml de VoxType."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "voxtype" / "config.toml"


class ConfigDocument:
    """Enveloppe autour d'un document tomlkit pour un accès par chemin pointé.

    Les clés sont adressées par chemin : "hotkey.key", "output.notification.on_transcription"…
    Les tables intermédiaires sont créées à la demande lors de l'écriture.
    """

    def __init__(self, path: Path, doc: TOMLDocument):
        self.path = path
        self.doc = doc

    # ---- chargement / sauvegarde ------------------------------------------

    @classmethod
    def load(cls, path: Path | None = None) -> "ConfigDocument":
        path = path or default_config_path()
        if path.exists():
            text = path.read_text(encoding="utf-8")
            doc = tomlkit.parse(text)
        else:
            doc = tomlkit.document()
        return cls(path, doc)

    def backup(self) -> Path | None:
        """Copie l'ancien fichier en .bak avant d'écrire. Renvoie le chemin du backup."""
        if not self.path.exists():
            return None
        bak = self.path.with_suffix(self.path.suffix + ".bak")
        shutil.copy2(self.path, bak)
        return bak

    def save(self, make_backup: bool = True) -> Path | None:
        bak = self.backup() if make_backup else None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(tomlkit.dumps(self.doc), encoding="utf-8")
        return bak

    def dumps(self) -> str:
        return tomlkit.dumps(self.doc)

    # ---- accès par chemin pointé ------------------------------------------

    def get(self, dotted: str, default=None):
        node = self.doc
        for part in dotted.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def has(self, dotted: str) -> bool:
        sentinel = object()
        return self.get(dotted, sentinel) is not sentinel

    def set(self, dotted: str, value) -> None:
        parts = dotted.split(".")
        *tables, leaf = parts
        node = self.doc
        for part in tables:
            if part not in node or not isinstance(node[part], dict):
                node[part] = tomlkit.table()
            node = node[part]
        node[leaf] = value

    def unset(self, dotted: str) -> None:
        """Supprime une clé si elle existe (laisse les tables vides en place)."""
        parts = dotted.split(".")
        *tables, leaf = parts
        node = self.doc
        for part in tables:
            if part not in node or not isinstance(node[part], dict):
                return
            node = node[part]
        if leaf in node:
            del node[leaf]
