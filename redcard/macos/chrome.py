from __future__ import annotations

import json
import tempfile
from pathlib import Path
from time import sleep
from urllib.parse import parse_qs, urlparse

from .osascript import run


GOOGLE_MEET_CHAT_JS = r"""
(() => {
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
  ].filter(Boolean).join(' ').toLowerCase();

  const clickFirst = (patterns) => {
    const controls = [...document.querySelectorAll('button, [role="button"]')].filter(visible);
    const match = controls.find((el) => {
      const text = textOf(el);
      return patterns.some((pattern) => text.includes(pattern));
    });
    if (match) {
      match.click();
      return true;
    }
    return false;
  };

  const focusInput = () => {
    const candidates = [
      ...document.querySelectorAll('textarea'),
      ...document.querySelectorAll('[contenteditable="true"]'),
      ...document.querySelectorAll('input[type="text"]')
    ].filter(visible);

    const match = candidates.find((el) => {
      const text = textOf(el);
      return text.includes('send') || text.includes('message') || text.includes('chat');
    }) || candidates[candidates.length - 1];

    if (match) {
      match.focus();
      match.click();
      return true;
    }
    return false;
  };

  if (focusInput()) return 'focused';

  clickFirst(['chat with everyone', 'open chat', 'show everyone', 'chat']);

  return new Promise((resolve) => {
    setTimeout(() => resolve(focusInput() ? 'focused' : 'not-found'), 500);
  });
})()
"""

GOOGLE_MEET_LEAVE_JS = r"""
(() => {
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
  ].filter(Boolean).join(' ').toLowerCase();

  const clickMatching = (patterns, rejectPatterns = []) => {
    const controls = [...document.querySelectorAll('button, [role="button"]')].filter(visible);
    const match = controls.find((el) => {
      const text = textOf(el);
      return patterns.some((pattern) => text.includes(pattern)) &&
        !rejectPatterns.some((pattern) => text.includes(pattern));
    });
    if (!match) return false;
    match.click();
    return true;
  };

  const controls = [...document.querySelectorAll('button, [role="button"]')].filter(visible);
  const leave = controls.find((el) => {
    const text = textOf(el);
    return text.includes('leave call') || text.includes('leave meeting') || text.includes('hang up');
  });

  if (!leave) return 'not-found';
  leave.click();

  return new Promise((resolve) => {
    setTimeout(() => {
      if (clickMatching(['just leave the call', 'just leave'], ['end'])) {
        resolve('clicked-confirmed');
      } else if (clickMatching(['leave'], ['end', 'hang up'])) {
        resolve('clicked-confirmed');
      } else {
        resolve('clicked');
      }
    }, 700);
  });
})()
"""

GOOGLE_MEET_ACTIVE_CALL_JS = r"""
(() => {
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
  ].filter(Boolean).join(' ').toLowerCase();

  const controls = [...document.querySelectorAll('button, [role="button"]')].filter(visible);
  const hasLeaveControl = controls.some((el) => {
    const text = textOf(el);
    return text.includes('leave call') || text.includes('leave meeting') || text.includes('hang up');
  });
  if (hasLeaveControl) return 'active';
  return `inactive title=${document.title} url=${location.href}`;
})()
"""


def google_meet_send_message_js(message: str, delay_seconds: float) -> str:
    return f"""
(() => {{
  const message = {json.dumps(message)};
  const delayMs = {max(0, int(delay_seconds * 1000))};

  const visible = (el) => {{
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  }};

  const textOf = (el) => [
    el.getAttribute('aria-label'),
    el.getAttribute('data-tooltip'),
    el.getAttribute('title'),
    el.getAttribute('placeholder'),
    ...[...el.querySelectorAll('[aria-label], [data-tooltip], [title]')].flatMap((child) => [
      child.getAttribute('aria-label'),
      child.getAttribute('data-tooltip'),
      child.getAttribute('title')
    ]),
    el.textContent
  ].filter(Boolean).join(' ').trim().toLowerCase();

  const clickFirst = (patterns) => {{
    const controls = [...document.querySelectorAll('button, [role="button"]')].filter(visible);
    const match = controls.find((el) => {{
      const text = textOf(el);
      return patterns.some((pattern) => text.includes(pattern));
    }});
    if (!match) return false;
    match.click();
    return true;
  }};

  const chatInput = () => {{
    const candidates = [
      ...document.querySelectorAll('textarea'),
      ...document.querySelectorAll('[contenteditable="true"]'),
      ...document.querySelectorAll('[role="textbox"]'),
      ...document.querySelectorAll('input[type="text"]')
    ].filter(visible);
    return candidates.find((el) => {{
      const text = textOf(el);
      return text.includes('send') || text.includes('message') || text.includes('chat') || text.includes('everyone');
    }}) || candidates[candidates.length - 1] || null;
  }};

  const setText = (el, value) => {{
    el.focus();
    el.click();
    const tag = el.tagName.toLowerCase();
    if (tag === 'textarea' || tag === 'input') {{
      const setter = Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value')?.set;
      if (setter) setter.call(el, value);
      else el.value = value;
      el.selectionStart = el.selectionEnd = value.length;
    }} else {{
      document.execCommand('selectAll', false, null);
      document.execCommand('insertText', false, value);
      if ((el.textContent || '').trim() !== value) {{
        el.textContent = value;
        const range = document.createRange();
        range.selectNodeContents(el);
        range.collapse(false);
        const selection = window.getSelection();
        if (selection) {{
          selection.removeAllRanges();
          selection.addRange(range);
        }}
      }}
    }}
    el.dispatchEvent(new InputEvent('input', {{bubbles: true, inputType: 'insertText', data: value}}));
    el.dispatchEvent(new Event('change', {{bubbles: true}}));
  }};

  const typeText = (el, value) => new Promise((resolve) => {{
    setText(el, '');
    if (!value) {{
      resolve();
      return;
    }}
    let index = 0;
    const typeNext = () => {{
      index += 1;
      setText(el, value.slice(0, index));
      if (index >= value.length) {{
        resolve();
        return;
      }}
      setTimeout(typeNext, delayMs);
    }};
    setTimeout(typeNext, delayMs);
  }});

  const currentText = (el) => {{
    const tag = el.tagName.toLowerCase();
    return (tag === 'textarea' || tag === 'input' ? el.value : el.textContent || '').trim();
  }};

  const sendButton = () => {{
    const controls = [...document.querySelectorAll('button, [role="button"]')].filter(visible);
    return controls.find((el) => {{
      const text = textOf(el);
      return text.includes('send message') || text === 'send' || text.includes('send a message');
    }});
  }};

  const pressEnter = (el) => {{
    const options = {{
      bubbles: true,
      cancelable: true,
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      which: 13
    }};
    el.focus();
    el.dispatchEvent(new KeyboardEvent('keydown', options));
    el.dispatchEvent(new KeyboardEvent('keypress', options));
    el.dispatchEvent(new KeyboardEvent('keyup', options));
  }};

  const waitForInputToClear = (el, resolve, startedAt = Date.now()) => {{
    if (currentText(el) !== message.trim()) {{
      resolve('sent');
      return;
    }}
    if (Date.now() - startedAt > 1500) {{
      resolve(`message-not-sent current=${{currentText(el)}}`);
      return;
    }}
    setTimeout(() => waitForInputToClear(el, resolve, startedAt), 150);
  }};

  const openChat = () => clickFirst(['chat with everyone', 'open chat', 'show everyone', 'in-call messages', 'chat']);

  return new Promise((resolve) => {{
    const startedAt = Date.now();
    const findInput = () => {{
      const input = chatInput();
      if (input) {{
        resolve(input);
        return;
      }}
      if (Date.now() - startedAt > 2500) {{
        resolve(null);
        return;
      }}
      openChat();
      setTimeout(findInput, 250);
    }};
    findInput();
  }}).then((input) => {{
    if (!input) return 'chat-input-not-found';
    return typeText(input, message).then(() => new Promise((resolve) => {{
      setTimeout(() => {{
        if (currentText(input) !== message.trim()) {{
          resolve(`message-not-entered current=${{currentText(input)}}`);
          return;
        }}
        const button = sendButton();
        if (button && !button.disabled && button.getAttribute('aria-disabled') !== 'true') {{
          button.click();
        }} else {{
          pressEnter(input);
        }}
        setTimeout(() => {{
          if (currentText(input) === message.trim()) pressEnter(input);
          waitForInputToClear(input, resolve);
        }}, 250);
      }}, 150);
    }}));
  }});
}})()
"""


def focus_google_meet_chat() -> None:
    _execute_on_meet_tab(GOOGLE_MEET_CHAT_JS, expected="focused", action="focus Google Meet chat")


def send_google_meet_chat_message(message: str, delay_seconds: float = 0.045) -> None:
    _execute_on_meet_tab(
        google_meet_send_message_js(message, delay_seconds),
        expected="sent",
        action="send Google Meet chat message",
    )


def leave_google_meet_call() -> None:
    _execute_on_meet_tab(GOOGLE_MEET_LEAVE_JS, expected="clicked", action="leave Google Meet call")
    close_chrome_picture_in_picture_windows()
    sleep(0.6)
    close_chrome_picture_in_picture_windows()


def google_meet_account_index(default: str = "0") -> str:
    url = _google_meet_tab_url(prefer_active=True)
    if not url:
        return default
    parsed = urlparse(url)
    authuser = parse_qs(parsed.query).get("authuser", [""])[0]
    return authuser or default


def has_google_meet_call_tab() -> bool:
    script = r'''
tell application "Google Chrome"
    if (count of windows) = 0 then return "no-chrome-window"
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if my isMeetCallUrl(tabUrl) then return "meet-call-tab"
        end repeat
    end repeat
    return "meet-call-tab-not-found"
end tell

on isMeetCallUrl(tabUrl)
    if tabUrl does not contain "meet.google.com" then return false
    if tabUrl is "https://meet.google.com" then return false
    if tabUrl is "https://meet.google.com/" then return false
    if tabUrl contains "meet.google.com/landing" then return false
    if tabUrl contains "meet.google.com/new" then return false
    if tabUrl contains "meet.google.com/lookup" then return false
    if tabUrl contains "meet.google.com/unsupported" then return false
    return true
end isMeetCallUrl
'''
    result = run(script, timeout_seconds=3)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Chrome could not check for a Google Meet tab. Details: {message}")
    return (result.stdout or "").strip() == "meet-call-tab"


def _google_meet_tab_url(prefer_active: bool = False) -> str | None:
    active_clause = '''
    if "{prefer_active}" is "true" then
        set activeUrl to URL of active tab of front window
        if my isMeetCallUrl(activeUrl) then return activeUrl
    end if
'''.replace("{prefer_active}", str(prefer_active).lower())
    script = f'''
tell application "Google Chrome"
    if (count of windows) = 0 then return "meet-call-tab-not-found"
{active_clause}
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if my isMeetCallUrl(tabUrl) then return tabUrl
        end repeat
    end repeat
    return "meet-call-tab-not-found"
end tell

on isMeetCallUrl(tabUrl)
    if tabUrl does not contain "meet.google.com" then return false
    if tabUrl is "https://meet.google.com" then return false
    if tabUrl is "https://meet.google.com/" then return false
    if tabUrl contains "meet.google.com/landing" then return false
    if tabUrl contains "meet.google.com/new" then return false
    if tabUrl contains "meet.google.com/lookup" then return false
    if tabUrl contains "meet.google.com/unsupported" then return false
    return true
end isMeetCallUrl
'''
    result = run(script, timeout_seconds=3)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Chrome could not read the Google Meet tab URL. Details: {message}")
    output = (result.stdout or "").strip()
    if output == "meet-call-tab-not-found":
        return None
    return output


def has_active_google_meet_call() -> bool:
    js_path = _write_temp_js(GOOGLE_MEET_ACTIVE_CALL_JS)
    script = f'''
set jsSource to read POSIX file "{js_path}"
tell application "Google Chrome"
    if (count of windows) = 0 then return "no-chrome-window"
    set sawMeetTab to false
    set lastResult to "meet-tab-not-found"
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if tabUrl contains "meet.google.com" then
                set sawMeetTab to true
                set targetTabIndex to tabIndex as integer
                set checkResult to execute tab targetTabIndex of window windowIndex javascript jsSource
                if checkResult is "active" then return "active"
                set lastResult to checkResult
            end if
        end repeat
    end repeat
    if sawMeetTab then return "inactive " & lastResult
    return "meet-tab-not-found"
end tell
'''
    try:
        result = run(script, timeout_seconds=5)
    finally:
        js_path.unlink(missing_ok=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            "Chrome could not check for an active Google Meet call. In Chrome, enable View > Developer > "
            f"Allow JavaScript from Apple Events, then try again. Details: {message}"
        )
    return (result.stdout or "").strip() == "active"


def close_chrome_picture_in_picture_windows() -> None:
    script = r'''
tell application "System Events"
    if not (exists process "Google Chrome") then return "chrome-not-running"
    tell process "Google Chrome"
        set closedCount to 0
        repeat with chromeWindow in windows
            set windowName to name of chromeWindow
            set windowRoleDescription to value of attribute "AXRoleDescription" of chromeWindow
            set isPictureInPicture to false
            if windowName contains "Picture in picture" then set isPictureInPicture to true
            if windowName contains "Picture-in-Picture" then set isPictureInPicture to true
            if windowName contains "picture-in-picture" then set isPictureInPicture to true
            if windowRoleDescription contains "picture" then set isPictureInPicture to true
            if isPictureInPicture then
                try
                    click button 1 of chromeWindow
                    set closedCount to closedCount + 1
                end try
            end if
        end repeat
        return "closed=" & closedCount
    end tell
end tell
'''
    run(script, timeout_seconds=2)


def google_meet_chat_screen_rect() -> tuple[float, float, float, float] | None:
    js = r"""
(() => {
  const visible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const textOf = (el) => [
    el.getAttribute('aria-label'),
    el.getAttribute('placeholder'),
    el.getAttribute('data-tooltip'),
    el.getAttribute('title'),
    el.textContent
  ].filter(Boolean).join(' ').toLowerCase();
  const rectFor = (el) => {
    const rect = el.getBoundingClientRect();
    const chromeTop = Math.max(0, window.outerHeight - window.innerHeight);
    const chromeLeft = Math.max(0, (window.outerWidth - window.innerWidth) / 2);
    return [
      'rect',
      Math.round(window.screenX + chromeLeft + rect.left),
      Math.round(window.screenY + chromeTop + rect.top),
      Math.round(rect.width),
      Math.round(rect.height)
    ].join(',');
  };
  const candidates = [
    ...document.querySelectorAll('textarea'),
    ...document.querySelectorAll('[contenteditable="true"]'),
    ...document.querySelectorAll('[role="textbox"]'),
    ...document.querySelectorAll('input[type="text"]')
  ].filter(visible).filter((el) => {
    const rect = el.getBoundingClientRect();
    return rect.width > 100 && rect.height > 24;
  });
  const named = candidates.find((el) => {
    const text = textOf(el);
    return text.includes('send') || text.includes('message') || text.includes('chat') || text.includes('everyone');
  });
  const fallback = candidates.sort((a, b) => {
    const ar = a.getBoundingClientRect();
    const br = b.getBoundingClientRect();
    return (br.right + br.bottom) - (ar.right + ar.bottom);
  })[0];
  const match = named || fallback;
  return match ? rectFor(match) : 'rect-not-found';
})()
"""
    js_path = _write_temp_js(js)
    script = f'''
set jsSource to read POSIX file "{js_path}"
tell application "Google Chrome"
    activate
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if tabUrl contains "meet.google.com" then
                set targetWindow to window windowIndex
                set targetTabIndex to tabIndex as integer
                set active tab index of targetWindow to targetTabIndex
                set index of targetWindow to 1
                delay 0.2
                return execute tab targetTabIndex of targetWindow javascript jsSource
            end if
        end repeat
    end repeat
    return "rect-not-found"
end tell
'''
    try:
        result = run(script, timeout_seconds=3)
    finally:
        js_path.unlink(missing_ok=True)
    return _parse_screen_rect(result)


def focused_element_screen_rect() -> tuple[float, float, float, float] | None:
    js = r"""
(() => {
  const candidateFromSelection = () => {
    const selection = window.getSelection();
    const node = selection && selection.anchorNode;
    if (!node) return null;
    return node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
  };
  const visible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  let el = document.activeElement;
  if (!visible(el) || el === document.body) {
    el = candidateFromSelection();
  }
  if (!visible(el)) return 'rect-not-found';
  const editable = el.closest && el.closest('input, textarea, [contenteditable="true"]');
  if (visible(editable)) el = editable;
  const rect = el.getBoundingClientRect();
  const chromeTop = Math.max(0, window.outerHeight - window.innerHeight);
  const chromeLeft = Math.max(0, (window.outerWidth - window.innerWidth) / 2);
  return [
    'rect',
    Math.round(window.screenX + chromeLeft + rect.left),
    Math.round(window.screenY + chromeTop + rect.top),
    Math.round(rect.width),
    Math.round(rect.height)
  ].join(',');
})()
"""
    js_path = _write_temp_js(js)
    script = f'''
set jsSource to read POSIX file "{js_path}"
tell application "Google Chrome"
    activate
    if (count of windows) = 0 then return "rect-not-found"
    return execute active tab of front window javascript jsSource
end tell
'''
    try:
        result = run(script, timeout_seconds=3)
    finally:
        js_path.unlink(missing_ok=True)
    return _parse_screen_rect(result)


def _parse_screen_rect(result) -> tuple[float, float, float, float] | None:
    output = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0 or not output.startswith("rect,"):
        return None
    try:
        _label, left, top, width, height = output.split(",", 4)
        return float(left), float(top), float(width), float(height)
    except ValueError:
        return None


def _execute_on_meet_tab(source: str, expected: str, action: str) -> None:
    js_path = _write_temp_js(source)
    script = f'''
set jsSource to read POSIX file "{js_path}"
tell application "Google Chrome"
    activate
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if tabUrl contains "meet.google.com" then
                set targetWindow to window windowIndex
                set targetTabIndex to tabIndex as integer
                set active tab index of targetWindow to targetTabIndex
                set index of targetWindow to 1
                delay 0.2
                return execute tab targetTabIndex of targetWindow javascript jsSource
            end if
        end repeat
    end repeat
    error "No open meet.google.com tab found in Chrome."
end tell
'''
    result = run(script)
    js_path.unlink(missing_ok=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Chrome could not {action}. In Chrome, enable View > Developer > "
            f"Allow JavaScript from Apple Events, then try again. Details: {message}"
        )
    outcome = (result.stdout or "").strip()
    if outcome and expected not in outcome:
        raise RuntimeError(f"Chrome found Meet, but could not {action}. Result: {outcome}")


def _write_temp_js(source: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
    with handle:
        handle.write(source)
    return Path(handle.name)
