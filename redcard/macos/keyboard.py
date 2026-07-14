from __future__ import annotations

import subprocess

from .osascript import run


MODIFIER_NAMES = {
    "command": "command down",
    "cmd": "command down",
    "shift": "shift down",
    "option": "option down",
    "alt": "option down",
    "control": "control down",
    "ctrl": "control down",
}


def type_text(text: str) -> None:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    run(f'tell application "System Events" to keystroke "{escaped}"')


def paste_text(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True, check=False)
    press_shortcut(["command", "v"])


def press_key(key: str) -> None:
    run(f'tell application "System Events" to key code {key_code(key)}')


def press_shortcut(keys: list[str]) -> None:
    if not keys:
        return

    modifiers = [MODIFIER_NAMES[k.lower()] for k in keys[:-1] if k.lower() in MODIFIER_NAMES]
    key = keys[-1]
    if modifiers:
        run(f'tell application "System Events" to keystroke "{key}" using {{{", ".join(modifiers)}}}')
    else:
        run(f'tell application "System Events" to keystroke "{key}"')


def key_code(key: str) -> int:
    codes = {
        "return": 36,
        "enter": 36,
        "escape": 53,
        "space": 49,
        "tab": 48,
    }
    try:
        return codes[key.lower()]
    except KeyError as exc:
        raise ValueError(f"No key code is configured for {key!r}. Use press_shortcut for printable keys.") from exc
