from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees
from time import monotonic
from typing import Callable

import cv2
import numpy as np

from .quit_key import TerminalQuitKey


PREVIEW_WINDOW = "Red Card detector"


@dataclass(frozen=True)
class DetectionSettings:
    min_area_ratio: float = 0.004
    max_area_ratio: float = 0.35
    min_aspect_ratio: float = 0.22
    max_aspect_ratio: float = 3.2
    min_saturation: int = 130
    min_value: int = 90
    min_rectangularity: float = 0.5
    min_extent: float = 0.42
    min_solidity: float = 0.74
    polygon_epsilon_ratio: float = 0.04
    min_corner_angle_degrees: float = 65.0
    max_corner_angle_degrees: float = 115.0
    min_opposite_side_ratio: float = 0.65
    min_border_margin_ratio: float = 0.015
    min_screen_red: int = 135
    min_red_dominance: int = 55
    min_red_green_ratio: float = 1.8
    hold_seconds: float = 0.8
    miss_grace_seconds: float = 0.0
    debug_log_interval_seconds: float = 1.0
    debug_preview: bool = True

    @classmethod
    def from_config(cls, config: dict) -> "DetectionSettings":
        return cls(
            min_area_ratio=float(config.get("min_area_ratio", cls.min_area_ratio)),
            max_area_ratio=float(config.get("max_area_ratio", cls.max_area_ratio)),
            min_aspect_ratio=float(config.get("min_aspect_ratio", cls.min_aspect_ratio)),
            max_aspect_ratio=float(config.get("max_aspect_ratio", cls.max_aspect_ratio)),
            min_saturation=int(config.get("min_saturation", cls.min_saturation)),
            min_value=int(config.get("min_value", cls.min_value)),
            min_rectangularity=float(config.get("min_rectangularity", cls.min_rectangularity)),
            min_extent=float(config.get("min_extent", cls.min_extent)),
            min_solidity=float(config.get("min_solidity", cls.min_solidity)),
            polygon_epsilon_ratio=float(config.get("polygon_epsilon_ratio", cls.polygon_epsilon_ratio)),
            min_corner_angle_degrees=float(
                config.get("min_corner_angle_degrees", cls.min_corner_angle_degrees)
            ),
            max_corner_angle_degrees=float(
                config.get("max_corner_angle_degrees", cls.max_corner_angle_degrees)
            ),
            min_opposite_side_ratio=float(
                config.get("min_opposite_side_ratio", cls.min_opposite_side_ratio)
            ),
            min_border_margin_ratio=float(config.get("min_border_margin_ratio", cls.min_border_margin_ratio)),
            min_screen_red=int(config.get("min_screen_red", cls.min_screen_red)),
            min_red_dominance=int(config.get("min_red_dominance", cls.min_red_dominance)),
            min_red_green_ratio=float(config.get("min_red_green_ratio", cls.min_red_green_ratio)),
            hold_seconds=float(config.get("hold_seconds", cls.hold_seconds)),
            miss_grace_seconds=float(config.get("miss_grace_seconds", cls.miss_grace_seconds)),
            debug_log_interval_seconds=float(
                config.get("debug_log_interval_seconds", cls.debug_log_interval_seconds)
            ),
            debug_preview=bool(config.get("debug_preview", cls.debug_preview)),
        )


class RedCardDetector:
    def __init__(
        self,
        camera_index: int | str,
        settings: DetectionSettings,
        on_trigger: Callable[[], bool | None],
        once: bool = False,
    ) -> None:
        self.camera_index = camera_index
        self.settings = settings
        self.on_trigger = on_trigger
        self.once = once
        self._visible_since: float | None = None
        self._last_visible_at: float | None = None
        self._next_debug_log_at = 0.0
        self._armed = True

    def watch(self, should_continue: Callable[[], bool] | None = None) -> str:
        capture, camera_index = _open_camera(self.camera_index)

        print(f"Watching for a red card on camera index {camera_index}. Press Esc to quit.")
        try:
            with TerminalQuitKey() as quit_key:
                next_continue_check = monotonic() + 2.0
                while True:
                    if should_continue is not None and monotonic() >= next_continue_check:
                        next_continue_check = monotonic() + 2.0
                        if not should_continue():
                            return "inactive"

                    ok, frame = capture.read()
                    if not ok:
                        raise RuntimeError("Camera frame could not be read.")

                    found, box, area_ratio = find_red_card(frame, self.settings)
                    if self._update_trigger_state(found):
                        return "triggered"

                    if self.settings.debug_preview:
                        if not found:
                            self._log_detection_debug(frame)
                        self._draw_preview(frame, found, box, area_ratio)
                        key = cv2.waitKey(1) & 0xFF
                        if key in (ord("q"), 27):
                            return "quit"
                    if quit_key.pressed():
                        return "quit"
        finally:
            capture.release()
            cv2.destroyAllWindows()
        return "stopped"

    def _update_trigger_state(self, found: bool) -> bool:
        now = monotonic()
        if not found:
            if (
                self._visible_since is not None
                and self._last_visible_at is not None
                and now - self._last_visible_at <= self.settings.miss_grace_seconds
            ):
                return False
            self._clear_detection_hold()
            return False

        if self._visible_since is None:
            self._visible_since = now
        self._last_visible_at = now
        if now - self._visible_since < self.settings.hold_seconds:
            return False

        if self._armed:
            self._armed = False
            if self.settings.debug_preview:
                cv2.destroyWindow(PREVIEW_WINDOW)
            handled = self.on_trigger()
            return handled is not False
        return False

    def _clear_detection_hold(self) -> None:
        self._visible_since = None
        self._last_visible_at = None
        self._armed = True

    def _log_detection_debug(self, frame: np.ndarray) -> None:
        now = monotonic()
        if now < self._next_debug_log_at:
            return
        self._next_debug_log_at = now + max(self.settings.debug_log_interval_seconds, 0.1)
        print(f"Detector debug: {diagnose_red_card(frame, self.settings)}")

    def _draw_preview(
        self,
        frame: np.ndarray,
        found: bool,
        box: tuple[int, int, int, int] | None,
        area_ratio: float,
    ) -> None:
        label = "RED CARD" if found else "watching"
        details = f"area {area_ratio * 100:.1f}% / min {self.settings.min_area_ratio * 100:.1f}%"
        color = (0, 0, 255) if found else (255, 255, 255)
        if box:
            x, y, w, h = box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        cv2.putText(frame, label, (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, details, (24, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.imshow(PREVIEW_WINDOW, frame)


def _open_camera(camera_index: int | str) -> tuple[cv2.VideoCapture, int]:
    indexes = range(8) if str(camera_index).lower() == "auto" else [int(camera_index)]
    failures: list[str] = []
    for index in indexes:
        capture = cv2.VideoCapture(index)
        if not capture.isOpened():
            failures.append(f"{index}: did not open")
            capture.release()
            continue
        for _attempt in range(12):
            ok, frame = capture.read()
            if ok and frame is not None and frame.size > 0:
                return capture, index
        failures.append(f"{index}: opened but returned no frames")
        capture.release()
    raise RuntimeError("Could not find a working camera. " + "; ".join(failures))


def find_red_card(frame: np.ndarray, settings: DetectionSettings) -> tuple[bool, tuple[int, int, int, int] | None, float]:
    height, width = frame.shape[:2]
    frame_area = height * width
    mask = _red_mask(frame, settings)

    best: tuple[float, tuple[int, int, int, int], float] | None = None
    largest_area_ratio = 0.0

    for candidate_mask in _candidate_masks(mask):
        contours, _ = cv2.findContours(candidate_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            area_ratio = area / frame_area
            largest_area_ratio = max(largest_area_ratio, area_ratio)
            if area_ratio < settings.min_area_ratio:
                continue
            if area_ratio > settings.max_area_ratio:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            if w == 0 or h == 0:
                continue
            if _touches_frame_edge(x, y, w, h, width, height, settings.min_border_margin_ratio):
                continue

            aspect_ratio = w / h
            if not settings.min_aspect_ratio <= aspect_ratio <= settings.max_aspect_ratio:
                continue

            rect_area = float(w * h)
            rectangularity = area / rect_area
            card_region = mask[y : y + h, x : x + w]
            extent = cv2.countNonZero(card_region) / rect_area
            if rectangularity < settings.min_rectangularity or extent < settings.min_extent:
                continue
            if _solidity(contour) < settings.min_solidity:
                continue
            if not _is_card_like_quadrilateral(contour, settings):
                continue

            score = area_ratio * (0.6 + min(rectangularity, 1.0)) * (0.6 + min(extent, 1.0))
            if best is None or score > best[0]:
                best = (score, (x, y, w, h), area_ratio)

    if best is None:
        return False, None, largest_area_ratio

    _, box, area_ratio = best
    return True, box, area_ratio


def diagnose_red_card(frame: np.ndarray, settings: DetectionSettings) -> str:
    height, width = frame.shape[:2]
    frame_area = height * width
    mask = _red_mask(frame, settings)
    largest: tuple[float, tuple[int, int, int, int], np.ndarray] | None = None

    for candidate_mask in _candidate_masks(mask):
        contours, _ = cv2.findContours(candidate_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area_ratio = cv2.contourArea(contour) / frame_area
            if largest is None or area_ratio > largest[0]:
                largest = (area_ratio, cv2.boundingRect(contour), contour)

    if largest is None:
        return "largest clean red area 0.0%; rejected: no red pixels matched the shade thresholds"

    area_ratio, (x, y, w, h), contour = largest
    prefix = f"largest clean red area {area_ratio * 100:.1f}%"
    if area_ratio < settings.min_area_ratio:
        return f"{prefix}; rejected: below min_area_ratio {settings.min_area_ratio * 100:.1f}%"
    if area_ratio > settings.max_area_ratio:
        return f"{prefix}; rejected: above max_area_ratio {settings.max_area_ratio * 100:.1f}%"
    if w == 0 or h == 0:
        return f"{prefix}; rejected: empty bounding box"
    if _touches_frame_edge(x, y, w, h, width, height, settings.min_border_margin_ratio):
        return f"{prefix}; rejected: touches frame edge"

    aspect_ratio = w / h
    if not settings.min_aspect_ratio <= aspect_ratio <= settings.max_aspect_ratio:
        return (
            f"{prefix}; rejected: aspect ratio {aspect_ratio:.2f} outside "
            f"{settings.min_aspect_ratio:.2f}-{settings.max_aspect_ratio:.2f}"
        )

    rect_area = float(w * h)
    rectangularity = cv2.contourArea(contour) / rect_area
    card_region = mask[y : y + h, x : x + w]
    extent = cv2.countNonZero(card_region) / rect_area
    if rectangularity < settings.min_rectangularity:
        return (
            f"{prefix}; rejected: rectangularity {rectangularity:.2f} below "
            f"{settings.min_rectangularity:.2f}"
        )
    if extent < settings.min_extent:
        return f"{prefix}; rejected: extent {extent:.2f} below {settings.min_extent:.2f}"

    solidity = _solidity(contour)
    if solidity < settings.min_solidity:
        return f"{prefix}; rejected: solidity {solidity:.2f} below {settings.min_solidity:.2f}"
    if not _is_card_like_quadrilateral(contour, settings):
        return f"{prefix}; rejected: not a card-like quadrilateral"
    return f"{prefix}; accepted candidate, waiting for {settings.hold_seconds:.1f}s hold"


def _candidate_masks(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    compact_kernel = np.ones((5, 5), np.uint8)
    compact = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, compact_kernel, iterations=2)
    compact = cv2.morphologyEx(compact, cv2.MORPH_OPEN, compact_kernel)

    marked_kernel = np.ones((13, 13), np.uint8)
    marked = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, marked_kernel, iterations=2)
    marked = cv2.morphologyEx(marked, cv2.MORPH_OPEN, compact_kernel)
    return compact, marked


def _touches_frame_edge(
    x: int,
    y: int,
    w: int,
    h: int,
    frame_width: int,
    frame_height: int,
    margin_ratio: float,
) -> bool:
    margin = round(min(frame_width, frame_height) * margin_ratio)
    return x <= margin or y <= margin or x + w >= frame_width - margin or y + h >= frame_height - margin


def _solidity(contour: np.ndarray) -> float:
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    if hull_area <= 0:
        return 0.0
    return cv2.contourArea(contour) / hull_area


def _is_card_like_quadrilateral(contour: np.ndarray, settings: DetectionSettings) -> bool:
    """Accept a face-on card while tolerating small corner occlusions.

    The convex hull removes inward finger notches. Polygon simplification can
    absorb a clipped corner, but hats and other rounded red objects retain more
    than four meaningful sides at the configured tolerance.
    """
    hull = cv2.convexHull(contour)
    perimeter = cv2.arcLength(hull, True)
    if perimeter <= 0:
        return False
    polygon = cv2.approxPolyDP(hull, settings.polygon_epsilon_ratio * perimeter, True)
    if len(polygon) != 4 or not cv2.isContourConvex(polygon):
        return False

    points = polygon.reshape(4, 2).astype(np.float64)
    side_lengths = [
        float(np.linalg.norm(points[(index + 1) % 4] - points[index]))
        for index in range(4)
    ]
    if min(side_lengths) <= 0:
        return False
    if _shorter_to_longer_ratio(side_lengths[0], side_lengths[2]) < settings.min_opposite_side_ratio:
        return False
    if _shorter_to_longer_ratio(side_lengths[1], side_lengths[3]) < settings.min_opposite_side_ratio:
        return False

    for index in range(4):
        previous = points[(index - 1) % 4] - points[index]
        following = points[(index + 1) % 4] - points[index]
        denominator = float(np.linalg.norm(previous) * np.linalg.norm(following))
        if denominator <= 0:
            return False
        cosine = float(np.dot(previous, following) / denominator)
        angle = degrees(acos(max(-1.0, min(1.0, cosine))))
        if not settings.min_corner_angle_degrees <= angle <= settings.max_corner_angle_degrees:
            return False
    return True


def _shorter_to_longer_ratio(first: float, second: float) -> float:
    return min(first, second) / max(first, second)


def _red_mask(frame: np.ndarray, settings: DetectionSettings) -> np.ndarray:
    """Return red pixels from both normal camera color and lit phone screens."""

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_red_a = np.array([0, settings.min_saturation, settings.min_value])
    upper_red_a = np.array([12, 255, 255])
    lower_red_b = np.array([170, settings.min_saturation, settings.min_value])
    upper_red_b = np.array([180, 255, 255])

    hsv_mask = cv2.inRange(hsv, lower_red_a, upper_red_a) | cv2.inRange(hsv, lower_red_b, upper_red_b)

    blue, green, red = cv2.split(frame)
    red_i = red.astype(np.int16)
    green_i = green.astype(np.int16)
    blue_i = blue.astype(np.int16)
    strongest_non_red = np.maximum(green_i, blue_i)
    red_green_ratio = red_i / np.maximum(green_i, 1)
    screen_red = (red_i >= settings.min_screen_red) & (
        red_i - strongest_non_red >= settings.min_red_dominance
    ) & (red_green_ratio >= settings.min_red_green_ratio)

    return hsv_mask | screen_red.astype(np.uint8) * 255
