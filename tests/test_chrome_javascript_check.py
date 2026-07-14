from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check-chrome-javascript.sh"


class ChromeJavaScriptCheckTests(unittest.TestCase):
    def run_check(self, mode: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_osascript = Path(temp_dir) / "osascript"
            fake_osascript.write_text(
                """#!/bin/sh
case "$FAKE_OSASCRIPT_MODE" in
  success)
    printf '%s\\n' 'redcard-js-events-ok'
    ;;
  disabled)
    printf '%s\\n' 'Google Chrome got an error: Executing JavaScript through AppleScript is turned off. From the menu bar, go to View > Developer > Allow JavaScript from Apple Events. (-2700)' >&2
    exit 1
    ;;
  denied)
    printf '%s\\n' 'Not authorized to send Apple events to Google Chrome. (-1743)' >&2
    exit 1
    ;;
  unexpected)
    printf '%s\\n' 'wrong-result'
    ;;
esac
"""
            )
            fake_osascript.chmod(0o755)
            environment = os.environ.copy()
            environment["FAKE_OSASCRIPT_MODE"] = mode
            environment["PATH"] = f"{temp_dir}:{environment['PATH']}"
            return subprocess.run(
                [str(CHECK_SCRIPT)],
                cwd=REPO_ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_success(self) -> None:
        result = self.run_check("success")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("looks good", result.stdout)

    def test_disabled_setting_gets_exact_chrome_instruction(self) -> None:
        result = self.run_check("disabled")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Chrome has JavaScript from Apple Events turned off", result.stdout)
        self.assertIn("View > Developer > Allow JavaScript from Apple Events", result.stdout)

    def test_apple_events_denial_is_not_reported_as_disabled_setting(self) -> None:
        result = self.run_check("denied")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ChatGPT was not allowed to send Apple Events", result.stdout)
        self.assertIn("does not mean Chrome's JavaScript", result.stdout)
        self.assertIn("outside the workspace sandbox", result.stdout)
        self.assertNotIn("Chrome has JavaScript from Apple Events turned off", result.stdout)

    def test_unexpected_result_is_reported_verbatim(self) -> None:
        result = self.run_check("unexpected")
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not confirm", result.stdout)
        self.assertIn("Unexpected Chrome result: wrong-result", result.stdout)


if __name__ == "__main__":
    unittest.main()
