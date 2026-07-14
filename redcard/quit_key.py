from __future__ import annotations

import select
import sys
import termios
import tty


class TerminalQuitKey:
    def __init__(self, keys: tuple[str, ...] = ("q", "\x1b")) -> None:
        self.keys = tuple(key.lower() for key in keys)
        self._enabled = False
        self._original_settings: list[int | bytes] | None = None

    def __enter__(self) -> "TerminalQuitKey":
        if not sys.stdin.isatty():
            return self
        self._original_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        self._enabled = True
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        if self._enabled and self._original_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._original_settings)
        self._enabled = False
        self._original_settings = None

    def pressed(self) -> bool:
        if not self._enabled:
            return False
        readable, _, _ = select.select([sys.stdin], [], [], 0)
        if not readable:
            return False
        return sys.stdin.read(1).lower() in self.keys
