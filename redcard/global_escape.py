from __future__ import annotations

import os
import subprocess
from pathlib import Path


class GlobalEscapeAbort:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.process: subprocess.Popen | None = None

    def __enter__(self) -> "GlobalEscapeAbort":
        if not self.enabled:
            return self
        executable = _ensure_global_escape_executable()
        try:
            self.process = subprocess.Popen([str(executable), str(os.getpid())])
        except OSError as exc:
            print(f"Red Card global Escape helper could not start: {exc}")
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


def _ensure_global_escape_executable() -> Path:
    root = Path.cwd()
    executable = root / "bin" / "redcard-global-escape"
    source = root / "tools" / "GlobalEscape.swift"
    if executable.exists() and executable.stat().st_mtime >= source.stat().st_mtime:
        return executable
    if not source.exists():
        raise RuntimeError(f"Global Escape source not found: {source}")
    executable.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["swiftc", str(source), "-o", str(executable)], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Could not build global Escape helper. Details: {details}")
    return executable
