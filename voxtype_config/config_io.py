"""Reading / writing VoxType's config.toml while preserving comments and ordering.

Uses tomlkit: the existing document is loaded, only the values changed by the
user are modified, and the file is rewritten identically for everything else
(comments, key order, formatting).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import tomlkit
from tomlkit import TOMLDocument


def default_config_path() -> Path:
    """Standard path of VoxType's config.toml."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "voxtype" / "config.toml"


class ConfigDocument:
    """Wrapper around a tomlkit document for dotted-path access.

    Keys are addressed by path: "hotkey.key", "output.notification.on_transcription"...
    Intermediate tables are created on demand when writing.
    """

    def __init__(self, path: Path, doc: TOMLDocument):
        self.path = path
        self.doc = doc

    # ---- loading / saving ------------------------------------------

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
        """Copies the previous file to .bak before writing. Returns the backup path."""
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

    # ---- dotted-path access ------------------------------------------

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
        """Removes a key if it exists (leaves empty tables in place)."""
        parts = dotted.split(".")
        *tables, leaf = parts
        node = self.doc
        for part in tables:
            if part not in node or not isinstance(node[part], dict):
                return
            node = node[part]
        if leaf in node:
            del node[leaf]
