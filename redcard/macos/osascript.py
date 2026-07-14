from __future__ import annotations

import subprocess


def run(script: str, timeout_seconds: float | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["osascript", "-e", script],
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout.decode("utf-8", errors="replace") if isinstance(error.stdout, bytes) else error.stdout
        return subprocess.CompletedProcess(
            ["osascript", "-e", script],
            124,
            stdout=stdout or "",
            stderr=f"AppleScript timed out after {timeout_seconds} seconds.",
        )
