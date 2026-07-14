from __future__ import annotations

import subprocess
from pathlib import Path


def _ensure_overlay_executable() -> Path:
    root = Path.cwd()
    executable = root / "bin" / "redcard-local-overlay"
    source = root / "tools" / "LocalOverlay.swift"
    if executable.exists() and executable.stat().st_mtime >= source.stat().st_mtime:
        return executable
    if not source.exists():
        raise RuntimeError(f"Local overlay source not found: {source}")
    executable.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["swiftc", str(source), "-o", str(executable)], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Could not build local overlay helper. Details: {details}")
    return executable
