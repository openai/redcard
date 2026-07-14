from __future__ import annotations

import subprocess


def _normalize_rect_to_overlay_coordinates(
    rect: tuple[float, float, float, float],
    *,
    width_height: bool = False,
) -> tuple[float, float, float, float]:
    """Return one rectangle in the overlay's global top-left bounds format.

    Chrome AppleScript bounds and Chrome/Accessibility screen rectangles already
    use the macOS global top-left origin. Do not add a display origin here. The
    native overlay performs the only top-left-to-Cocoa conversion when drawing.
    """
    left, top, third, fourth = rect
    right = left + third if width_height else third
    bottom = top + fourth if width_height else fourth
    if right < left or bottom < top:
        raise ValueError(f"Invalid screen rectangle: {rect}")
    return left, top, right, bottom


def _meet_window_bounds() -> tuple[int, int, int, int] | None:
    script = '''
tell application "Google Chrome"
    repeat with windowIndex from 1 to count of windows
        set tabUrl to URL of active tab of window windowIndex
        if tabUrl contains "meet.google.com" then
            set windowBounds to bounds of window windowIndex
            return "active," & (item 1 of windowBounds as text) & "," & (item 2 of windowBounds as text) & "," & (item 3 of windowBounds as text) & "," & (item 4 of windowBounds as text)
        end if
    end repeat
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if tabUrl contains "meet.google.com" then
                set windowBounds to bounds of window windowIndex
                return "background," & (item 1 of windowBounds as text) & "," & (item 2 of windowBounds as text) & "," & (item 3 of windowBounds as text) & "," & (item 4 of windowBounds as text)
            end if
        end repeat
    end repeat
end tell
'''
    result = subprocess.run(["osascript", "-e", script], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    parts = raw.split(",")
    if len(parts) == 5:
        source = parts[0]
        raw_bounds = parts[1:]
    else:
        source = "unknown"
        raw_bounds = parts
    try:
        left, top, right, bottom = [int(part) for part in raw_bounds]
    except ValueError:
        return None
    print(f"Corner referee: using {source} Meet tab from Chrome.")
    return left, top, right, bottom
