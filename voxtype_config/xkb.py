"""Dispositions et variantes clavier xkb, lues depuis les règles evdev.

Source : /usr/share/X11/xkb/rules/evdev.lst — sections « ! layout » et « ! variant ».
"""

from __future__ import annotations

import functools
import re

_RULES = "/usr/share/X11/xkb/rules/evdev.lst"

# Dispositions à remonter en tête de liste (les plus courantes)
_PRIORITY = ["us", "fr", "gb", "de", "es", "it", "be", "ch", "ca", "pt", "nl"]


@functools.lru_cache(maxsize=1)
def _parse() -> tuple[list[tuple[str, str]], dict[str, list[tuple[str, str]]]]:
    layouts: list[tuple[str, str]] = []
    variants: dict[str, list[tuple[str, str]]] = {}
    section = None
    try:
        with open(_RULES, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("!"):
                    section = line[1:].strip()
                    continue
                m = re.match(r"\s+(\S+)\s+(.+?)\s*$", line)
                if not m:
                    continue
                code, desc = m.group(1), m.group(2)
                if section == "layout":
                    layouts.append((code, desc))
                elif section == "variant":
                    # desc = « fr: French (alt.) » → layout parent + libellé
                    parent, _, label = desc.partition(":")
                    parent = parent.strip()
                    label = label.strip() or desc
                    variants.setdefault(parent, []).append((code, label))
    except OSError:
        pass
    return layouts, variants


def layout_options() -> list[tuple[str, str]]:
    """[(code, « code — Nom »)], dispositions courantes d'abord."""
    layouts, _ = _parse()
    if not layouts:
        # repli minimal si les règles xkb sont absentes
        return [(c, c) for c in _PRIORITY]
    by_code = {c: d for c, d in layouts}
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for c in _PRIORITY:
        if c in by_code:
            ordered.append((c, f"{c} — {by_code[c]}"))
            seen.add(c)
    for c, d in layouts:
        if c not in seen:
            ordered.append((c, f"{c} — {d}"))
    return ordered


def variant_options(layout: str) -> list[tuple[str, str]]:
    """Variantes d'une disposition, précédées de l'option « par défaut » (valeur vide)."""
    _, variants = _parse()
    out: list[tuple[str, str]] = [("", "(par défaut)")]
    for code, label in variants.get(layout, []):
        out.append((code, f"{code} — {label}"))
    return out
