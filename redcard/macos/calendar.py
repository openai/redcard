from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import subprocess
import tempfile
from time import sleep
from urllib.parse import urlencode

from .osascript import run


def create_block(title: str, start: datetime, end: datetime, calendar_name: str | None = None) -> None:
    calendar_target = f'calendar "{_escape(calendar_name)}"' if calendar_name else "calendar 1"
    script = f'''
set eventTitle to "{_escape(title)}"
set startDate to date "{_apple_date(start)}"
set endDate to date "{_apple_date(end)}"
tell application "Calendar"
    activate
    tell {calendar_target}
        make new event with properties {{summary:eventTitle, start date:startDate, end date:endDate}}
    end tell
end tell
'''
    result = run(script, timeout_seconds=8)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Calendar could not create the block. Details: {message}")


def create_google_calendar_block(
    title: str,
    start: datetime,
    end: datetime,
    details: str = "",
    calendar_id: str | None = None,
    recurrence_rule: str | None = None,
    auto_save: bool = True,
) -> None:
    event_url = _google_calendar_template_url(
        title=title,
        start=start,
        end=end,
        details=details,
        calendar_id=calendar_id,
        recurrence_rule=recurrence_rule,
    )
    script = f'''
tell application "Google Chrome"
    activate
    set foundCalendarTab to false
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if tabUrl contains "calendar.google.com" then
                set targetWindow to window windowIndex
                set targetTabIndex to tabIndex as integer
                set index of targetWindow to 1
                set active tab index of targetWindow to targetTabIndex
                set URL of tab targetTabIndex of targetWindow to "{_escape(event_url)}"
                set foundCalendarTab to true
                exit repeat
            end if
        end repeat
        if foundCalendarTab then exit repeat
    end repeat
    if not foundCalendarTab then
        if (count of windows) = 0 then make new window
        tell front window
            make new tab at end of tabs with properties {{URL:"{_escape(event_url)}"}}
            set active tab index to count of tabs
        end tell
    end if
end tell
'''
    result = run(script)
    if result.returncode != 0:
        result = subprocess.run(["open", "-a", "Google Chrome", event_url], text=True, capture_output=True, check=False)
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Chrome could not open Google Calendar. Details: {message}")

    if auto_save:
        _click_google_calendar_save()


def open_google_calendar_homepage() -> None:
    print("Opening Google Calendar homepage.")
    result = _open_url_in_front_chrome_tab("https://calendar.google.com/calendar/u/0/r")
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Chrome could not open Google Calendar homepage. Details: {message}")


def open_google_calendar_event_editor(
    start: datetime,
    end: datetime,
    details: str = "",
    calendar_id: str | None = None,
    recurrence_rule: str | None = None,
) -> None:
    print("Opening Google Calendar event editor.")
    event_url = _google_calendar_template_url(
        title="",
        start=start,
        end=end,
        details=details,
        calendar_id=calendar_id,
        recurrence_rule=recurrence_rule,
    )
    script = f'''
tell application "Google Chrome"
    activate
    if (count of windows) = 0 then make new window
    tell front window
        make new tab at end of tabs with properties {{URL:"{_escape(event_url)}"}}
        set active tab index to count of tabs
    end tell
end tell
'''
    result = run(script)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Chrome could not open Google Calendar event editor. Details: {message}")
    _focus_google_calendar_event_title()


def save_google_calendar_event(scroll_to_top: bool = False) -> None:
    print("Saving Google Calendar event.")
    _click_google_calendar_save(scroll_to_top=scroll_to_top)


def type_title_in_google_calendar_event(text: str, delay_seconds: float) -> None:
    js_path = _write_temp_js(_calendar_animated_title_js(text=text, delay_seconds=delay_seconds))
    try:
        result = _execute_on_calendar_event_tab(js_path)
        output = (result.stdout or result.stderr or "").strip()
        if result.returncode != 0 or "started" not in output:
            raise RuntimeError(f"Google Calendar could not type the event title. Last result: {output}")
        sleep(max(0.1, len(text) * delay_seconds * 1.3 + 0.3))
    finally:
        js_path.unlink(missing_ok=True)


def open_calendar_view_at_top() -> None:
    open_google_calendar_homepage()
    _scroll_calendar_view_to_top()


def _calendar_scroll_top_js() -> str:
    return r'''
(() => {
  const scrollables = [...document.querySelectorAll('*')].filter((el) => {
    const style = window.getComputedStyle(el);
    return el.scrollHeight > el.clientHeight + 100 &&
      ['auto', 'scroll'].includes(style.overflowY);
  });
  const likely = scrollables.filter((el) => {
    const text = [el.getAttribute('aria-label'), el.className, el.id]
      .filter(Boolean).join(' ').toLowerCase();
    return text.includes('calendar') || text.includes('grid') || text.includes('scroll') || text.includes('body');
  });
  const targets = likely.length ? likely : scrollables;
  for (const el of targets) el.scrollTop = 0;
  window.scrollTo(0, 0);
  return `scrolled targets=${targets.length} url=${location.href} title=${document.title}`;
})()
'''


def _scroll_calendar_view_to_top() -> None:
    js_path = _write_temp_js(_calendar_scroll_top_js())
    try:
        last_output = ""
        for _attempt in range(20):
            result = _execute_on_calendar_view_tab(js_path)
            output = (result.stdout or result.stderr or "").strip()
            if output:
                last_output = output
            if result.returncode == 0 and "scrolled" in output:
                print(f"Google Calendar view scrolled to top: {output}")
                return
            sleep(0.5)
        print(f"Google Calendar view scroll-to-top was inconclusive. Last result: {last_output}")
    finally:
        js_path.unlink(missing_ok=True)


def _apple_date(value: datetime) -> str:
    return value.strftime("%A, %B %d, %Y at %I:%M:%S %p")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _open_url_in_front_chrome_tab(url: str):
    script = f'''
tell application "Google Chrome"
    activate
    if (count of windows) = 0 then make new window
    tell front window
        make new tab at end of tabs with properties {{URL:"{_escape(url)}"}}
        set active tab index to count of tabs
    end tell
end tell
'''
    return run(script, timeout_seconds=8)


def _google_calendar_template_url(
    title: str,
    start: datetime,
    end: datetime,
    details: str,
    calendar_id: str | None = None,
    recurrence_rule: str | None = None,
) -> str:
    params = {
        "action": "TEMPLATE",
        "dates": f"{_google_date(start)}/{_google_date(end)}",
    }
    if title:
        params["text"] = title
    if details:
        params["details"] = details
    if calendar_id:
        params["src"] = calendar_id
    if recurrence_rule:
        params["recur"] = recurrence_rule
    return f"https://calendar.google.com/calendar/render?{urlencode(params)}"


def _google_date(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.astimezone()
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _click_google_calendar_save(scroll_to_top: bool = False) -> None:
    js = r'''
(() => {
  const url = window.location.href;
  const title = document.title;
  const visible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const textOf = (el) => [
    el.getAttribute('aria-label'),
    el.getAttribute('data-tooltip'),
    el.getAttribute('title'),
    el.textContent
  ].filter(Boolean).join(' ').trim().toLowerCase();
  const controls = [...document.querySelectorAll('button, [role="button"]')].filter(visible);
  const save = controls.find((el) => textOf(el) === 'save' || textOf(el).includes('save'));
  if (!save) return `not-found url=${url} title=${title} buttons=${controls.slice(0, 12).map(textOf).join('|')}`;
  save.click();
  return `clicked url=${url} title=${title}`;
})()
'''
    js_path = _write_temp_js(js)
    last_output = ""
    for _attempt in range(24):
        script = f'''
set jsSource to read POSIX file "{js_path}"
tell application "Google Chrome"
    activate
    set foundCalendarTab to false
    set calendarWindowIndex to 0
    set calendarTabIndex to 0
    set calendarTabUrl to ""
    set calendarUrls to ""
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if tabUrl contains "calendar.google.com" then
                set calendarUrls to calendarUrls & "[" & windowIndex & ":" & tabIndex & "] " & tabUrl & " "
            end if
            if tabUrl contains "calendar.google.com" and (tabUrl contains "action=TEMPLATE" or tabUrl contains "eventedit" or tabUrl contains "/event?") then
                set calendarWindowIndex to windowIndex
                set calendarTabIndex to tabIndex
                set calendarTabUrl to tabUrl
                set foundCalendarTab to true
                exit repeat
            end if
        end repeat
        if foundCalendarTab then exit repeat
    end repeat
    if not foundCalendarTab then return "calendar-event-tab-not-found calendarTabs=" & calendarUrls
    set targetWindow to window calendarWindowIndex
    set targetTabIndex to calendarTabIndex as integer
    set active tab index of targetWindow to targetTabIndex
    set clickResult to execute tab targetTabIndex of targetWindow javascript jsSource
    return "tab=" & calendarWindowIndex & ":" & calendarTabIndex & " tabUrl=" & calendarTabUrl & " result=" & clickResult
end tell
'''
        result = run(script, timeout_seconds=3)
        output = (result.stdout or result.stderr or "").strip()
        if output:
            last_output = output
        if result.returncode == 0 and "result=clicked" in output:
            js_path.unlink(missing_ok=True)
            if scroll_to_top:
                _scroll_front_calendar_view_to_top()
            else:
                sleep(2.0)
            return
        sleep(0.5)

    js_path.unlink(missing_ok=True)
    raise RuntimeError(
        "Google Calendar opened, but Red Card could not click Save. "
        "The event should be prefilled in Chrome; save it manually or try again after the page finishes loading. "
        f"Last result: {last_output}"
    )


def _scroll_front_calendar_view_to_top() -> None:
    js_path = _write_temp_js(_calendar_scroll_top_js())
    try:
        last_output = ""
        for _attempt in range(20):
            script = f'''
set jsSource to read POSIX file "{js_path}"
tell application "Google Chrome"
    activate
    if (count of windows) = 0 then return "no-chrome-window"
    set tabUrl to URL of active tab of front window
    if tabUrl does not contain "calendar.google.com" then return "not-calendar url=" & tabUrl
    if tabUrl contains "action=TEMPLATE" or tabUrl contains "eventedit" or tabUrl contains "/event?" then return "waiting-calendar-view url=" & tabUrl
    return execute active tab of front window javascript jsSource
end tell
'''
            result = run(script, timeout_seconds=2)
            output = (result.stdout or result.stderr or "").strip()
            if output:
                last_output = output
            if result.returncode == 0 and "scrolled" in output:
                print(f"Google Calendar view scrolled to top after save: {output}")
                return
            sleep(0.25)
        print(f"Google Calendar post-save scroll-to-top was inconclusive. Last result: {last_output}")
    finally:
        js_path.unlink(missing_ok=True)


def _focus_google_calendar_event_title() -> None:
    js = r'''
(() => {
  const visible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const textOf = (el) => [
    el.getAttribute('aria-label'),
    el.getAttribute('placeholder'),
    el.getAttribute('title'),
    el.textContent
  ].filter(Boolean).join(' ').trim().toLowerCase();
  const candidates = [
    ...document.querySelectorAll('input'),
    ...document.querySelectorAll('textarea'),
    ...document.querySelectorAll('[contenteditable="true"]')
  ].filter(visible);
  const title = candidates.find((el) => {
    const text = textOf(el);
    return text.includes('title') || text.includes('add title');
  }) || candidates[0];
  if (!title) return `title-not-found url=${location.href} title=${document.title}`;
  title.focus();
  title.click();
  return `title-focused url=${location.href} title=${document.title}`;
})()
'''
    js_path = _write_temp_js(js)
    try:
        last_output = ""
        print("Focusing Google Calendar event title.")
        for _attempt in range(8):
            result = _execute_on_calendar_event_tab(js_path)
            output = (result.stdout or result.stderr or "").strip()
            if output:
                last_output = output
            if result.returncode == 0 and "title-focused" in output:
                print(f"Google Calendar event title focused: {output}")
                return
            sleep(0.5)
        raise RuntimeError(f"Google Calendar event title could not be focused. Last result: {last_output}")
    finally:
        js_path.unlink(missing_ok=True)


def _calendar_animated_title_js(text: str, delay_seconds: float) -> str:
    calibrated_delay_ms = max(1, int(delay_seconds * 1000 * 1.3))
    return f"""
(() => {{
  const text = {_js_string(text)};
  const delayMs = {calibrated_delay_ms};
  const visible = (el) => {{
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  }};
  const textOf = (el) => [
    el.getAttribute('aria-label'),
    el.getAttribute('placeholder'),
    el.getAttribute('title'),
    el.getAttribute('name'),
    el.textContent
  ].filter(Boolean).join(' ').trim().toLowerCase();
  const candidates = [
    ...document.querySelectorAll('input'),
    ...document.querySelectorAll('textarea'),
    ...document.querySelectorAll('[contenteditable="true"]')
  ].filter(visible);
  const title = candidates.find((el) => {{
    const label = textOf(el);
    return label.includes('add title') || label === 'title' || label.includes('event title');
  }}) || candidates.find((el) => {{
    const label = textOf(el);
    return label.includes('title');
  }}) || candidates[0];
  if (!title) return `title-not-found url=${{location.href}} title=${{document.title}}`;
  title.focus();
  title.click();
  const setText = (value) => {{
    if (['input', 'textarea'].includes(title.tagName.toLowerCase())) {{
      const setter = Object.getOwnPropertyDescriptor(title.constructor.prototype, 'value')?.set;
      if (setter) setter.call(title, value);
      else title.value = value;
      title.selectionStart = title.selectionEnd = value.length;
    }} else {{
      title.textContent = value;
      const range = document.createRange();
      range.selectNodeContents(title);
      range.collapse(false);
      const selection = window.getSelection();
      if (selection) {{
        selection.removeAllRanges();
        selection.addRange(range);
      }}
    }}
    title.dispatchEvent(new Event('input', {{bubbles: true}}));
    title.dispatchEvent(new Event('change', {{bubbles: true}}));
  }};
  setText('');
  let index = 0;
  const timer = setInterval(() => {{
    if (index >= text.length) {{
      clearInterval(timer);
      title.dispatchEvent(new Event('change', {{bubbles: true}}));
      title.blur();
      title.focus();
      return;
    }}
    index += 1;
    setText(text.slice(0, index));
  }}, delayMs);
  return 'started';
}})()
"""


def _execute_on_calendar_event_tab(js_path: Path):
    script = f'''
set jsSource to read POSIX file "{js_path}"
tell application "Google Chrome"
    activate
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if tabUrl contains "calendar.google.com" and (tabUrl contains "action=TEMPLATE" or tabUrl contains "eventedit" or tabUrl contains "/event?") then
                set targetWindow to window windowIndex
                set targetTabIndex to tabIndex as integer
                set active tab index of targetWindow to targetTabIndex
                set index of targetWindow to 1
                delay 0.2
                return execute tab targetTabIndex of targetWindow javascript jsSource
            end if
        end repeat
    end repeat
    return "calendar-event-tab-not-found"
end tell
'''
    return run(script, timeout_seconds=5)


def _execute_on_calendar_view_tab(js_path: Path):
    script = f'''
set jsSource to read POSIX file "{js_path}"
tell application "Google Chrome"
    activate
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if tabUrl contains "calendar.google.com" and tabUrl does not contain "action=TEMPLATE" and tabUrl does not contain "eventedit" and tabUrl does not contain "/event?" then
                set targetWindow to window windowIndex
                set targetTabIndex to tabIndex as integer
                set active tab index of targetWindow to targetTabIndex
                set index of targetWindow to 1
                delay 0.2
                return execute tab targetTabIndex of targetWindow javascript jsSource
            end if
        end repeat
    end repeat
    return "calendar-view-tab-not-found"
end tell
'''
    return run(script, timeout_seconds=5)


def _write_temp_js(source: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
    with handle:
        handle.write(source)
    return Path(handle.name)


def _js_string(value: str) -> str:
    return repr(value)
