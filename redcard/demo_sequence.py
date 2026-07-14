from __future__ import annotations

import subprocess
from datetime import date, datetime, time
from pathlib import Path
from time import sleep

from .corner_referee import (
    _meet_window_bounds,
    _normalize_rect_to_overlay_coordinates,
)
from .demo_overlay import DemoReferee
from .macos import calendar, gmail
from .macos.apps import activate_app
from .macos.chrome import (
    focused_element_screen_rect,
    focus_google_meet_chat,
    google_meet_account_index,
    leave_google_meet_call,
    send_google_meet_chat_message,
)
from .macos.osascript import run


class DemoSequenceRunner:
    def __init__(self, config: dict, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run
        self.sequence = config.get("sequence", {})
        self.calendar = config.get("calendar", {})
        self.gmail = config.get("gmail", {})
        self.demo = config.get("demo_mode", {})
        self.referee = None if dry_run else DemoReferee(self.demo.get("referee", {}))

    def run(self) -> None:
        if self.dry_run:
            self._dry_run()
            return

        print("Red card detected. Starting full sequence.")
        _play_sequence_sound(str(self.sequence.get("sound_path", "assets/referee-whistle.wav")))
        if self.referee is None:
            raise RuntimeError("Referee overlay was not initialized.")
        self.referee.start()
        try:
            self._meeting_scene()
            self._calendar_scene()
            if bool(self.gmail.get("enabled", False)):
                self._gmail_scene()
            else:
                print("Gmail scene skipped because gmail.enabled is false.")
            print("Full sequence complete.")
        finally:
            self.referee.stop()

    def _meeting_scene(self) -> None:
        meet_bounds = _meet_window_bounds()
        bounds = (
            _normalize_rect_to_overlay_coordinates(meet_bounds)
            if meet_bounds is not None
            else _front_chrome_bounds() or (0, 0, 1440, 900)
        )
        left, top, right, bottom = bounds
        intro_scale = _seconds(self.demo, "intro_referee_scale", 2.4)
        action_scale = _seconds(self.demo, "action_referee_scale", 0.6)
        video_center_x = left + (right - left) * _seconds(self.demo, "meet_video_center_x_ratio", 0.41)
        video_center_y = top + (bottom - top) * _seconds(self.demo, "meet_video_center_y_ratio", 0.54)
        intro_x = video_center_x - 161 * intro_scale / 2
        intro_y = video_center_y - 198 * intro_scale / 2
        self.referee.show(intro_x, intro_y, animation="redcard", scale=intro_scale, facing="right")
        self.referee.animate("redcard", _seconds(self.demo, "red_card_seconds", 2.0), scale=intro_scale)

        activate_app(str(self.sequence.get("target_app", "Google Chrome")))
        focus_google_meet_chat()
        print("Meet chat field rect: using fixed chat-panel position.")
        chat_feet_x = right - _seconds(self.demo, "meet_chat_referee_feet_right_offset", 390.0)
        chat_feet_y = bottom - _seconds(self.demo, "meet_chat_referee_feet_bottom_offset", 55.0)
        self.referee.move_feet_to(
            chat_feet_x,
            chat_feet_y,
            duration=1.2,
            final_animation="pointing",
            scale=action_scale,
            final_facing="right",
            foot_anchor_x=0.82,
        )
        self.referee.show(animation="pointing", facing="right")
        send_google_meet_chat_message(
            str(self.sequence.get("message", "Red card! Ejected from meeting.")),
            delay_seconds=_seconds(self.demo, "meet_typing_delay_seconds", _seconds(self.demo, "typing_delay_seconds", 0.045)),
        )
        sleep(_seconds(self.demo, "meet_message_hold_seconds", 5.0))
        leave_google_meet_call()
        self.referee.animate("redcard", _seconds(self.demo, "page_transition_red_card_seconds", 0.8), facing="right")

    def _calendar_scene(self) -> None:
        bounds = _front_chrome_bounds() or (0, 0, 1440, 900)
        left, top, right, bottom = bounds

        start, end, recurrence_rule = self._calendar_event_times()
        calendar.open_google_calendar_event_editor(
            start=start,
            end=end,
            details=str(self.calendar.get("details", "Created by Red Card.")),
            calendar_id=str(self.calendar.get("google_calendar_id")) if self.calendar.get("google_calendar_id") else None,
            recurrence_rule=recurrence_rule,
        )
        sleep(_seconds(self.demo, "calendar_event_load_seconds", 1.5))
        bounds = _front_chrome_bounds() or bounds
        left, top, _right, _bottom = bounds
        title_rect = _focused_element_overlay_bounds()
        print(f"Calendar title field rect: {title_rect}")
        if title_rect is not None:
            _field_left, _field_top, field_right, field_bottom = title_rect
            title_feet_x = field_right + 24
            title_feet_y = field_bottom + 88
        else:
            title_feet_x = left + 760
            title_feet_y = top + 280
        self.referee.move_feet_to(
            title_feet_x,
            title_feet_y,
            duration=1.0,
            final_animation="pointing",
            final_facing="left",
            foot_anchor_x=0.18,
        )
        self.referee.show(animation="pointing", facing="left")
        calendar.type_title_in_google_calendar_event(
            text=str(self.calendar.get("title", "RED CARD!")),
            delay_seconds=_seconds(self.demo, "calendar_typing_delay_seconds", _seconds(self.demo, "typing_delay_seconds", 0.045)),
        )
        sleep(_seconds(self.demo, "calendar_title_hold_seconds", 2.0))
        calendar.save_google_calendar_event(scroll_to_top=True)
        bounds = _front_chrome_bounds() or bounds
        left, top, right, _bottom = bounds
        self.referee.move_feet_to(right - 330, top + 430, duration=0.8, final_animation="pointing", final_facing="left")
        self.referee.show(animation="pointing", facing="left")
        sleep(_seconds(self.demo, "calendar_saved_hold_seconds", 2.0))
        self.referee.animate("redcard", _seconds(self.demo, "page_transition_red_card_seconds", 0.8), facing="left")

    def _gmail_scene(self) -> None:
        account_index = self._gmail_account_index()
        _open_url_in_front_chrome_tab(f"https://mail.google.com/mail/u/{account_index}/#settings/general")
        sleep(_seconds(self.demo, "gmail_settings_load_seconds", 1.0))
        bounds = _front_chrome_bounds() or (0, 0, 1440, 900)
        left, top, right, _bottom = bounds
        settings_start_x = left + (right - left) * _seconds(self.demo, "gmail_settings_run_start_x_ratio", 0.22)
        settings_end_x = left + (right - left) * _seconds(self.demo, "gmail_settings_run_end_x_ratio", 0.48)
        settings_y = top + _seconds(self.demo, "gmail_settings_run_y_offset", 300.0)
        self.referee.move_feet_to(settings_start_x, settings_y, duration=0.6)
        self.referee.move_feet_to(
            settings_end_x,
            settings_y,
            duration=_seconds(self.demo, "gmail_settings_run_seconds", 2.0),
            final_animation="waiting",
        )
        self.referee.animate("waiting", _seconds(self.demo, "gmail_waiting_hold_seconds", 0.8))

        subject = str(self.gmail.get("subject", "Red card"))
        message = str(self.gmail.get("message", "I am out of the office."))
        start = _parse_date(str(self.gmail.get("start_date", "today")))
        end = _parse_date(str(self.gmail.get("end_date", "2026-07-19")))
        result = gmail._run_gmail_ooo_js(
            subject=subject,
            start_text=gmail._gmail_date(start),
            end_text=gmail._gmail_date(end),
            action="focus-subject",
            account_index=account_index,
        )
        print(f"Gmail subject setup: {result}")
        if "subject-focused" not in result:
            raise RuntimeError(f"Gmail autoreply subject could not be focused. Last result: {result}")
        sleep(_seconds(self.demo, "gmail_settings_load_seconds", 1.0))
        bounds = _front_chrome_bounds() or bounds
        left, top, _right, bottom = bounds
        subject_rect = _focused_element_overlay_bounds()
        print(f"Gmail subject field rect: {subject_rect}")
        if subject_rect is not None:
            _field_left, _field_top, field_right, field_bottom = subject_rect
            subject_feet_x = field_right + 24
            subject_feet_y = field_bottom + 80
        else:
            subject_feet_x = left + 760
            subject_feet_y = bottom - 170
        self.referee.move_feet_to(
            subject_feet_x,
            subject_feet_y,
            duration=1.0,
            final_animation="pointing",
            final_facing="left",
            foot_anchor_x=0.18,
        )
        self.referee.show(animation="pointing", facing="left")
        gmail.type_text_in_focused_gmail_field(
            text=subject,
            account_index=account_index,
            delay_seconds=_seconds(self.demo, "gmail_typing_delay_seconds", _seconds(self.demo, "typing_delay_seconds", 0.045)),
        )
        sleep(_seconds(self.demo, "gmail_subject_hold_seconds", 1.0))
        result = gmail._run_gmail_ooo_js(
            subject=subject,
            start_text=gmail._gmail_date(start),
            end_text=gmail._gmail_date(end),
            action="focus-body-only",
            account_index=account_index,
        )
        print(f"Gmail body setup: {result}")
        if "body-focused" not in result:
            raise RuntimeError(f"Gmail autoreply box could not be focused. Last result: {result}")
        body_rect = _focused_element_overlay_bounds()
        print(f"Gmail autoreply field rect: {body_rect}")
        if body_rect is not None:
            _field_left, field_top, field_right, field_bottom = body_rect
            body_feet_x = field_right + 24
            body_feet_y = field_top + min(field_bottom - field_top, 80) + 34
        else:
            body_feet_x = left + 760
            body_feet_y = bottom - 145
        self.referee.move_feet_to(
            body_feet_x,
            body_feet_y,
            duration=0.8,
            final_animation="pointing",
            final_facing="left",
            foot_anchor_x=0.18,
        )
        self.referee.show(animation="pointing", facing="left")
        gmail.type_text_in_focused_gmail_field(
            text=message,
            account_index=account_index,
            delay_seconds=_seconds(self.demo, "gmail_typing_delay_seconds", _seconds(self.demo, "typing_delay_seconds", 0.045)),
        )
        if bool(self.gmail.get("auto_save", True)):
            result = gmail._run_gmail_save_js(account_index=account_index, subject=subject)
            print(f"Gmail save: {result}")
            if "saved-confirmed" not in result:
                raise RuntimeError(f"Gmail vacation responder fields were filled, but Save failed. Last result: {result}")
            self.referee.show(animation="waving", facing="left")
            sleep(_seconds(self.demo, "gmail_saved_hold_seconds", 1.0))
        else:
            self.referee.show(animation="waving", facing="left")
        sleep(_seconds(self.demo, "pre_goodbye_hold_seconds", 2.0))
        self.referee.animate("goodbye", _seconds(self.demo, "goodbye_seconds", 3.0))
        if bool(self.sequence.get("sleep_after_goodbye", False)):
            print("Final goodbye screen shown. Sleeping this Mac.")
            _sleep_computer()

    def _gmail_account_index(self) -> str:
        configured = self.gmail.get("account_index", "meet")
        if isinstance(configured, str) and configured.lower() in {"meet", "auto", "active_meet"}:
            account_index = google_meet_account_index(default="0")
            print(f"Gmail account: using Meet tab account {account_index}.")
            return account_index
        return str(configured)

    def _calendar_event_times(self) -> tuple[datetime, datetime, str | None]:
        start = datetime.combine(date.today(), _parse_time(str(self.calendar.get("day_start", "00:00"))))
        end = datetime.combine(date.today(), _parse_time(str(self.calendar.get("day_end", "23:59"))))
        if str(self.calendar.get("layout", "")) != "daily_recurring_block":
            return start, end, None
        end_at = datetime.fromisoformat(str(self.calendar.get("end_at", "2026-07-19T15:00:00")))
        recurrence_until = datetime.combine(end_at.date(), _parse_time(str(self.calendar.get("day_end", "23:59"))))
        return start, end, f"RRULE:FREQ=DAILY;UNTIL={recurrence_until:%Y%m%dT%H%M%S}"

    def _dry_run(self) -> None:
        print("[dry-run] Referee appears and red-card animation plays.")
        print(f"[dry-run] Type Meet message slowly: {self.sequence.get('message')!r}.")
        print("[dry-run] Hold Meet message, leave call, open Calendar homepage.")
        print(f"[dry-run] Run directly to event title and type Calendar title slowly: {self.calendar.get('title')!r}.")
        print("[dry-run] Save Calendar event, open Gmail inbox/settings.")
        print(f"[dry-run] Type Gmail subject slowly: {self.gmail.get('subject')!r}.")
        print(f"[dry-run] Type Gmail autoreply slowly: {self.gmail.get('message')!r}.")
        print("[dry-run] Wave, then pull down final goodbye shade.")
        if bool(self.sequence.get("sleep_after_goodbye", False)):
            print("[dry-run] Sleep this Mac after the goodbye screen.")


def _front_chrome_bounds() -> tuple[float, float, float, float] | None:
    script = '''
tell application "Google Chrome"
    if (count of windows) = 0 then return ""
    set windowBounds to bounds of front window
    return (item 1 of windowBounds as text) & "," & (item 2 of windowBounds as text) & "," & (item 3 of windowBounds as text) & "," & (item 4 of windowBounds as text)
end tell
'''
    result = run(script)
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    try:
        bounds = tuple(float(part) for part in raw.split(","))
        return _normalize_rect_to_overlay_coordinates(bounds)  # type: ignore[arg-type]
    except ValueError:
        return None


def _focused_element_overlay_bounds() -> tuple[float, float, float, float] | None:
    rect = focused_element_screen_rect()
    if rect is None:
        return None
    return _normalize_rect_to_overlay_coordinates(rect, width_height=True)


def _open_url_in_front_chrome_tab(url: str) -> None:
    script = f'''
tell application "Google Chrome"
    activate
    if (count of windows) = 0 then make new window
    tell front window
        make new tab at end of tabs with properties {{URL:"{url}"}}
        set active tab index to count of tabs
    end tell
end tell
'''
    result = run(script)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Chrome could not open tab in the current window. Details: {message}")


def _sleep_computer() -> None:
    result = run('tell application "System Events" to sleep')
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Red Card could not sleep this Mac. Details: {message}")


def _play_sequence_sound(sound_path: str) -> None:
    path = Path(sound_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        path = Path("/System/Library/Sounds/Blow.aiff")
    subprocess.Popen(["afplay", str(path)])


def _parse_date(value: str) -> date:
    if value == "today":
        return date.today()
    return date.fromisoformat(value)


def _parse_time(value: str) -> time:
    hour, minute = value.split(":", maxsplit=1)
    return time(hour=int(hour), minute=int(minute))


def _seconds(config: dict, key: str, default: float) -> float:
    return float(config.get(key, default))
