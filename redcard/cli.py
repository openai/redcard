from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from time import sleep

import cv2

from .demo_sequence import DemoSequenceRunner
from .detector import DetectionSettings, RedCardDetector
from .global_escape import GlobalEscapeAbort
from .macos.chrome import has_active_google_meet_call, has_google_meet_call_tab
from .quit_key import TerminalQuitKey


DEFAULT_CONFIG = "redcard.config.json"


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    try:
        return _main()
    except KeyboardInterrupt:
        print("Red Card aborted.")
        return 130


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Watch for a red card and eject yourself from work.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Path to the JSON config file.")
    parser.add_argument("--dry-run", action="store_true", help="Detect and show effects without changing apps.")
    parser.add_argument("--once", action="store_true", help="Exit after the first trigger.")
    parser.add_argument("--no-sleep", action="store_true", help="Keep this Mac awake after the final goodbye screen.")
    parser.add_argument(
        "--list-cameras",
        action="store_true",
        help="Probe local camera indexes and show which ones open.",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    if args.no_sleep:
        config.setdefault("sequence", {})["sleep_after_goodbye"] = False
    if args.list_cameras:
        list_cameras(max_index=8)
        return 0

    settings = DetectionSettings.from_config(config.get("detection", {}))
    if not bool(config.get("demo_mode", {}).get("show_detector_preview", False)):
        settings = replace(settings, debug_preview=False)
    demo_runner = DemoSequenceRunner(config=config, dry_run=args.dry_run)
    if args.dry_run:
        demo_runner.run()
        return 0

    with GlobalEscapeAbort():
        _watch_when_meet_is_active(
            lambda: RedCardDetector(
                camera_index=config.get("camera_index", 0),
                settings=settings,
                on_trigger=_meet_guarded_trigger(demo_runner.run, dry_run=args.dry_run),
                once=args.once,
            ),
            dry_run=args.dry_run,
        )
    return 0


def _meet_guarded_trigger(action, dry_run: bool):
    def guarded():
        if dry_run:
            action()
            return True
        try:
            if not has_active_google_meet_call():
                print("Red card detected, but no active Google Meet call was found. Waiting for the next red card.")
                return False
            action()
            return True
        except RuntimeError as exc:
            print(f"Red card detected, but Meet could not be checked or controlled: {exc}")
            print("Continuing to watch for the next red card.")
            return False

    return guarded


def list_cameras(max_index: int = 8) -> None:
    for index in range(max_index):
        capture = cv2.VideoCapture(index)
        try:
            if not capture.isOpened():
                print(f"{index}: did not open")
                continue
            ok, frame = capture.read()
            if ok and frame is not None and frame.size > 0:
                height, width = frame.shape[:2]
                print(f"{index}: ok {width}x{height}")
            else:
                print(f"{index}: opened but returned no frame")
        finally:
            capture.release()


def _watch_when_meet_is_active(build_watcher, dry_run: bool) -> None:
    while True:
        if not _wait_for_active_google_meet_call():
            return
        reason = _run_watcher(build_watcher(), should_continue=_meet_still_active)
        if reason == "quit":
            return
        if reason == "inactive":
            print("Google Meet call ended. Camera stopped; waiting for the next active Meet call.")
            continue
        return


def _run_watcher(watcher, should_continue=None):
    if hasattr(watcher, "watch"):
        return watcher.watch(should_continue=should_continue)
    return watcher.run(should_continue=should_continue)


def _wait_for_active_google_meet_call() -> bool:
    print("Red Card is running and ready to go. Waiting for an active Google Meet call before starting the camera. Press Esc to quit.", flush=True)
    with TerminalQuitKey() as quit_key:
        while True:
            if _meet_call_tab_is_open(log_errors=True):
                print("Google Meet call tab found. Starting camera.")
                return True
            if quit_key.pressed():
                return False
            sleep(2.0)


def _meet_still_active(log_errors: bool = False) -> bool:
    return _meet_call_tab_is_open(log_errors=log_errors)


def _meet_call_tab_is_open(log_errors: bool = False) -> bool:
    try:
        return has_google_meet_call_tab()
    except RuntimeError as exc:
        if log_errors:
            print(f"Google Meet could not be checked yet: {exc}")
        return False
