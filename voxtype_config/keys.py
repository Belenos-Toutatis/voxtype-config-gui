"""Correspondance des touches : keycode GDK → nom de touche evdev attendu par VoxType.

VoxType nomme les touches comme les constantes Linux KEY_* sans le préfixe
(« PAUSE », « SCROLLLOCK », « RIGHTALT », « F13 »…). Sous Wayland/X11, le keycode
matériel renvoyé par GDK vaut le code evdev + 8.
"""

from __future__ import annotations

import functools
import re

# Table de secours si python-evdev est absent (touches usuelles pour un raccourci)
_FALLBACK = {
    1: "ESC", 14: "BACKSPACE", 15: "TAB", 28: "ENTER", 57: "SPACE",
    58: "CAPSLOCK", 69: "NUMLOCK", 70: "SCROLLLOCK", 119: "PAUSE",
    29: "LEFTCTRL", 97: "RIGHTCTRL", 42: "LEFTSHIFT", 54: "RIGHTSHIFT",
    56: "LEFTALT", 100: "RIGHTALT", 125: "LEFTMETA", 126: "RIGHTMETA",
    99: "SYSRQ", 110: "INSERT", 111: "DELETE", 102: "HOME", 107: "END",
    104: "PAGEUP", 109: "PAGEDOWN", 105: "LEFT", 106: "RIGHT",
    103: "UP", 108: "DOWN", 127: "COMPOSE",
}
for _i, _code in enumerate(range(59, 69)):      # F1..F10
    _FALLBACK[_code] = f"F{_i + 1}"
_FALLBACK[87], _FALLBACK[88] = "F11", "F12"
for _i, _code in enumerate(range(183, 195)):    # F13..F24
    _FALLBACK[_code] = f"F{_i + 13}"


def evdev_name_from_keycode(hw_keycode: int) -> str | None:
    """Renvoie le nom VoxType d'une touche à partir du keycode matériel GDK."""
    code = hw_keycode - 8
    if code < 0:
        return None
    try:
        from evdev import ecodes
        name = ecodes.KEY.get(code)
        if isinstance(name, (list, tuple)):
            name = name[0]
        if name and name.startswith("KEY_"):
            return name[4:]
    except Exception:
        pass
    return _FALLBACK.get(code)


@functools.lru_cache(maxsize=1)
def valid_key_names() -> frozenset[str]:
    """Ensemble des noms de touche acceptés par VoxType = noms evdev sans « KEY_ ».

    VoxType lie la crate evdev et reconnaît ces noms ; on s'aligne sur la même
    source pour ne jamais proposer une touche refusée.
    """
    names: set[str] = set()
    try:
        from evdev import ecodes
        for _code, name in ecodes.KEY.items():
            for n in (name if isinstance(name, (list, tuple)) else [name]):
                if isinstance(n, str) and n.startswith("KEY_"):
                    names.add(n[4:])
    except Exception:
        pass
    return frozenset(names)


# Suggestions, par ordre d'utilité. Filtrées contre la table evdev à l'usage,
# donc toute entrée non reconnue par VoxType est automatiquement écartée.
_SUGGESTED = [
    # touches « dédiées » idéales pour un raccourci
    "PAUSE", "SCROLLLOCK", "CAPSLOCK", "NUMLOCK", "SYSRQ", "MENU",
    # touches d'édition / navigation (utiles pour l'annulation)
    "ESC", "BACKSPACE", "DELETE", "INSERT", "HOME", "END", "PAGEUP", "PAGEDOWN",
    "TAB", "SPACE",
    # modificateurs
    "RIGHTALT", "RIGHTCTRL", "RIGHTSHIFT", "RIGHTMETA",
    "LEFTALT", "LEFTCTRL", "LEFTSHIFT", "LEFTMETA",
    # touches de fonction
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "F13", "F14", "F15", "F16", "F17", "F18", "F19", "F20",
]


def suggested_keys() -> list[str]:
    """Suggestions garanties valides (filtrées contre evdev)."""
    valid = valid_key_names()
    if not valid:                       # evdev indisponible : on garde la liste telle quelle
        return list(_SUGGESTED)
    return [k for k in _SUGGESTED if k in valid]


# Compat : ancienne constante, désormais filtrée
COMMON_KEYS = suggested_keys()

# Préfixes de keycode bruts acceptés par VoxType (cf. message d'aide du parseur)
_KEYCODE_RE = re.compile(r"^(EVTEST|WEV|X11|XEV)_\d+$")


def is_valid_key(name: str) -> bool:
    """Vrai si VoxType accepterait ce nom : nom evdev connu ou keycode préfixé."""
    name = (name or "").strip()
    if not name:
        return True                     # vide = « non défini », accepté
    if _KEYCODE_RE.match(name):
        return True
    valid = valid_key_names()
    if not valid:
        return True                     # evdev indisponible : on ne bloque pas
    return name in valid
