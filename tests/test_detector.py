from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from redcard.detector import DetectionSettings, RedCardDetector, diagnose_red_card, find_red_card


class RedCardShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = DetectionSettings(debug_preview=False)

    def test_face_on_card_triggers(self) -> None:
        frame = _blank_frame()
        cv2.rectangle(frame, (250, 130), (390, 350), (0, 0, 230), -1)
        self.assertTrue(find_red_card(frame, self.settings)[0])

    def test_slightly_tilted_card_triggers(self) -> None:
        frame = _blank_frame()
        points = cv2.boxPoints(((320, 240), (140, 220), 12)).astype(np.int32)
        cv2.fillConvexPoly(frame, points, (0, 0, 230))
        self.assertTrue(find_red_card(frame, self.settings)[0])

    def test_card_with_any_covered_corner_triggers(self) -> None:
        for corner in ((250, 130), (390, 130), (390, 350), (250, 350)):
            with self.subTest(corner=corner):
                frame = _blank_frame()
                cv2.rectangle(frame, (250, 130), (390, 350), (0, 0, 230), -1)
                cv2.circle(frame, corner, 28, (80, 150, 205), -1)
                self.assertTrue(find_red_card(frame, self.settings)[0])

    def test_red_hat_does_not_trigger(self) -> None:
        frame = _blank_frame()
        cv2.ellipse(frame, (320, 240), (110, 85), 0, 180, 360, (0, 0, 230), -1)
        cv2.rectangle(frame, (210, 235), (430, 295), (0, 0, 230), -1)
        cv2.ellipse(frame, (375, 295), (100, 28), 0, 0, 360, (0, 0, 230), -1)
        self.assertFalse(find_red_card(frame, self.settings)[0])

    def test_diagnose_red_card_reports_area_gate(self) -> None:
        frame = _blank_frame()
        cv2.rectangle(frame, (300, 220), (330, 260), (0, 0, 230), -1)
        settings = DetectionSettings(min_area_ratio=0.05, debug_preview=False)

        diagnosis = diagnose_red_card(frame, settings)

        self.assertIn("largest clean red area", diagnosis)
        self.assertIn("below min_area_ratio 5.0%", diagnosis)


class RedCardWatcherTests(unittest.TestCase):
    @patch("redcard.detector.monotonic", side_effect=[0.0, 0.1, 0.36])
    def test_brief_missed_recognition_keeps_hold_timer(self, _monotonic: MagicMock) -> None:
        on_trigger = MagicMock(return_value=None)
        detector = RedCardDetector(
            0,
            DetectionSettings(hold_seconds=0.35, miss_grace_seconds=0.2, debug_preview=False),
            on_trigger,
        )

        self.assertFalse(detector._update_trigger_state(True))
        self.assertFalse(detector._update_trigger_state(False))
        self.assertTrue(detector._update_trigger_state(True))
        on_trigger.assert_called_once_with()

    @patch("redcard.detector.monotonic", side_effect=[0.0, 0.21, 0.36])
    def test_expired_missed_recognition_grace_resets_hold_timer(self, _monotonic: MagicMock) -> None:
        on_trigger = MagicMock(return_value=None)
        detector = RedCardDetector(
            0,
            DetectionSettings(hold_seconds=0.35, miss_grace_seconds=0.2, debug_preview=False),
            on_trigger,
        )

        self.assertFalse(detector._update_trigger_state(True))
        self.assertFalse(detector._update_trigger_state(False))
        self.assertFalse(detector._update_trigger_state(True))
        on_trigger.assert_not_called()

    @patch("redcard.detector.cv2.destroyAllWindows")
    @patch("redcard.detector.find_red_card", return_value=(True, None, 0.1))
    @patch("redcard.detector.TerminalQuitKey")
    @patch("redcard.detector._open_camera")
    def test_successful_trigger_exits_watcher_cleanly(
        self,
        open_camera: MagicMock,
        terminal_quit_key: MagicMock,
        _find_red_card: MagicMock,
        _destroy_all_windows: MagicMock,
    ) -> None:
        capture = MagicMock()
        capture.read.return_value = (True, _blank_frame())
        open_camera.return_value = (capture, 0)
        terminal_quit_key.return_value.__enter__.return_value.pressed.return_value = False
        on_trigger = MagicMock(return_value=None)
        detector = RedCardDetector(0, DetectionSettings(hold_seconds=0, debug_preview=False), on_trigger)

        self.assertEqual(detector.watch(), "triggered")
        on_trigger.assert_called_once_with()
        capture.release.assert_called_once_with()

    @patch("redcard.detector.cv2.destroyAllWindows")
    @patch("redcard.detector.find_red_card", return_value=(True, None, 0.1))
    @patch("redcard.detector.TerminalQuitKey")
    @patch("redcard.detector._open_camera")
    def test_failed_guarded_trigger_keeps_watching(
        self,
        open_camera: MagicMock,
        terminal_quit_key: MagicMock,
        _find_red_card: MagicMock,
        _destroy_all_windows: MagicMock,
    ) -> None:
        capture = MagicMock()
        capture.read.return_value = (True, _blank_frame())
        open_camera.return_value = (capture, 0)
        terminal_quit_key.return_value.__enter__.return_value.pressed.side_effect = [False, False, True]
        on_trigger = MagicMock(return_value=False)
        detector = RedCardDetector(0, DetectionSettings(hold_seconds=0, debug_preview=False), on_trigger)

        self.assertEqual(detector.watch(), "quit")
        on_trigger.assert_called_once_with()
        self.assertEqual(capture.read.call_count, 3)
        capture.release.assert_called_once_with()


def _blank_frame() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


if __name__ == "__main__":
    unittest.main()
