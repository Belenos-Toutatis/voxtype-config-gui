"""Key mapping: GDK keycode → evdev key name expected by VoxType.

VoxType names keys like the Linux KEY_* constants without the prefix
('PAUSE', 'SCROLLLOCK', 'RIGHTALT', 'F13'...). Under Wayland/X11, the hardware
keycode returned by GDK equals the evdev code + 8.
"""

from __future__ import annotations

import functools
import re

# Fallback table if python-evdev is missing (common keys for a hotkey)
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
    """Returns the VoxType name of a key from the GDK hardware keycode."""
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
    """Set of key names accepted by VoxType = evdev names without 'KEY_'.

    VoxType binds the evdev crate and recognizes these names; we align on the
    same source so we never suggest a rejected key.
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


# Suggestions, in order of usefulness. Filtered against the evdev table at use
# time, so any entry not recognized by VoxType is automatically discarded.
_SUGGESTED = [
    # 'dedicated' keys ideal for a hotkey
    "PAUSE", "SCROLLLOCK", "CAPSLOCK", "NUMLOCK", "SYSRQ", "MENU",
    # editing / navigation keys (useful for cancellation)
    "ESC", "BACKSPACE", "DELETE", "INSERT", "HOME", "END", "PAGEUP", "PAGEDOWN",
    "TAB", "SPACE",
    # modifiers
    "RIGHTALT", "RIGHTCTRL", "RIGHTSHIFT", "RIGHTMETA",
    "LEFTALT", "LEFTCTRL", "LEFTSHIFT", "LEFTMETA",
    # function keys
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "F13", "F14", "F15", "F16", "F17", "F18", "F19", "F20",
]


def suggested_keys() -> list[str]:
    """Suggestions guaranteed valid (filtered against evdev)."""
    valid = valid_key_names()
    if not valid:                       # evdev unavailable: keep the list as-is
        return list(_SUGGESTED)
    return [k for k in _SUGGESTED if k in valid]


# Compatibility: legacy constant, now filtered
COMMON_KEYS = suggested_keys()

# Raw keycode prefixes accepted by VoxType (see the parser's help message)
_KEYCODE_RE = re.compile(r"^(EVTEST|WEV|X11|XEV)_\d+$")


def is_valid_key(name: str) -> bool:
    """True if VoxType would accept this name: known evdev name or prefixed keycode."""
    name = (name or "").strip()
    if not name:
        return True                     # empty = 'unset', accepted
    if _KEYCODE_RE.match(name):
        return True
    valid = valid_key_names()
    if not valid:
        return True                     # evdev unavailable: don't block
    return name in valid
