from __future__ import annotations

from .osascript import run


def activate_app(name: str) -> None:
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    run(f'tell application "{escaped}" to activate')
