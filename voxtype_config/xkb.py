"""xkb keyboard layouts and variants, read from the evdev rules.

Source: /usr/share/X11/xkb/rules/evdev.lst — '! layout' and '! variant' sections.
"""

from __future__ import annotations

import functools
import re

_RULES = "/usr/share/X11/xkb/rules/evdev.lst"

# Layouts to bring to the top of the list (the most common ones)
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
                    # desc = 'fr: French (alt.)' → parent layout + label
                    parent, _, label = desc.partition(":")
                    parent = parent.strip()
                    label = label.strip() or desc
                    variants.setdefault(parent, []).append((code, label))
    except OSError:
        pass
    return layouts, variants


def layout_options() -> list[tuple[str, str]]:
    """[(code, 'code — Name')], common layouts first."""
    layouts, _ = _parse()
    if not layouts:
        # minimal fallback if the xkb rules are missing
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
    """Variants of a layout, preceded by the 'default' option (empty value)."""
    _, variants = _parse()
    out: list[tuple[str, str]] = [("", "(default)")]
    for code, label in variants.get(layout, []):
        out.append((code, f"{code} — {label}"))
    return out
