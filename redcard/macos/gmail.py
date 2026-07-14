from __future__ import annotations

from datetime import date
from pathlib import Path
import subprocess
import tempfile
from time import sleep

from .keyboard import paste_text
from .osascript import run


def set_vacation_responder(
    subject: str,
    message: str,
    start_date: date,
    end_date: date,
    account_index: int | str = 0,
    auto_save: bool = True,
) -> None:
    settings_url = f"https://mail.google.com/mail/u/{account_index}/#settings/general"
    _copy_fallback_text(subject=subject, message=message)
    result = subprocess.run(
        ["open", "-a", "Google Chrome", settings_url],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Chrome could not open Gmail settings. Details: {details}")

    outcome = _run_gmail_ooo_js(
        subject=subject,
        start_text=_gmail_date(start_date),
        end_text=_gmail_date(end_date),
        action="focus-body",
        account_index=account_index,
    )
    if "body-focused" not in outcome:
        raise RuntimeError(
            "Gmail settings opened, but Red Card could not confidently set the vacation responder. "
            f"The subject/message were copied to the clipboard. Last result: {outcome}"
        )
    paste_text(message)
    sleep(0.35)

    if auto_save:
        outcome = _run_gmail_save_js(account_index=account_index, subject=subject)
        if "saved" not in outcome:
            raise RuntimeError(
                "Gmail vacation responder fields were filled, but Red Card could not click Save Changes. "
                f"Last result: {outcome}"
            )


def _run_gmail_ooo_js(
    subject: str,
    start_text: str,
    end_text: str,
    action: str,
    account_index: int | str,
) -> str:
    js_path = _write_temp_js(_gmail_ooo_js(subject, start_text, end_text, action))
    try:
        last_output = "not-run"
        for attempt in range(80):
            result = _execute_on_gmail_tab(js_path=js_path, account_index=account_index)
            last_output = (result.stdout or result.stderr or "").strip()
            if result.returncode == 0 and (
                "saved" in last_output
                or "filled" in last_output
                or "body-focused" in last_output
                or "subject-focused" in last_output
            ):
                return last_output
            if attempt in {0, 5, 10, 20, 40, 60}:
                print(f"Gmail setup waiting: {last_output}")
            sleep(0.75)
        return last_output
    finally:
        js_path.unlink(missing_ok=True)


def _run_gmail_save_js(account_index: int | str, subject: str = "") -> str:
    js_path = _write_temp_js(_gmail_save_js(clicked=False, subject=subject))
    wait_js_path = _write_temp_js(_gmail_save_js(clicked=True, subject=subject))
    try:
        last_output = "not-run"
        clicked = False
        for _attempt in range(30):
            result = _execute_on_gmail_tab(js_path=wait_js_path if clicked else js_path, account_index=account_index)
            last_output = (result.stdout or result.stderr or "").strip()
            if result.returncode == 0 and "saved-confirmed" in last_output:
                return last_output
            if result.returncode == 0 and "save-clicked" in last_output:
                clicked = True
            if clicked and result.returncode == 0 and "save-not-found" in last_output:
                return f"saved-confirmed after-click last={last_output}"
            sleep(0.75)
        return last_output
    finally:
        js_path.unlink(missing_ok=True)
        wait_js_path.unlink(missing_ok=True)


def type_text_in_focused_gmail_field(text: str, account_index: int | str, delay_seconds: float) -> None:
    js_path = _write_temp_js(_gmail_animated_insert_text_js(text=text, delay_seconds=delay_seconds))
    try:
        result = _execute_on_gmail_tab(js_path=js_path, account_index=account_index)
        output = (result.stdout or result.stderr or "").strip()
        if result.returncode != 0 or "started" not in output:
            raise RuntimeError(f"Gmail could not insert visible text. Last result: {output}")
        calibrated_delay = max(0.001, delay_seconds * 1.3)
        sleep(max(0.25, len(text) * calibrated_delay + 0.75))
    finally:
        js_path.unlink(missing_ok=True)


def _gmail_ooo_js(subject: str, start_text: str, end_text: str, action: str) -> str:
    return f"""
(() => {{
  const subject = {_js_string(subject)};
  const startText = {_js_string(start_text)};
  const endText = {_js_string(end_text)};
  const action = {_js_string(action)};

  const visible = (el) => {{
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  }};
  const textOf = (el) => [
    el.getAttribute('aria-label'),
    el.getAttribute('data-tooltip'),
    el.getAttribute('title'),
    el.getAttribute('name'),
    el.value,
    el.textContent
  ].filter(Boolean).join(' ').trim().toLowerCase();
  const setValue = (el, value) => {{
    el.focus();
    const setter = Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value')?.set;
    if (setter) setter.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event('input', {{bubbles: true}}));
    el.dispatchEvent(new Event('change', {{bubbles: true}}));
    el.dispatchEvent(new KeyboardEvent('keyup', {{bubbles: true, key: 'Tab'}}));
    el.blur();
  }};
  const clickText = (patterns) => {{
    const controls = [...document.querySelectorAll('input, button, [role="button"], label, span, div')]
      .filter(visible);
    const match = controls.find((el) => {{
      const text = textOf(el);
      return patterns.some((pattern) => text.includes(pattern));
    }});
    if (!match) return false;
    match.click();
    return true;
  }};
  const enableLastDayOption = () => {{
    const fixedEnd = document.querySelector('input[aria-label="Fixed end date"]');
    if (fixedEnd) {{
      if (!fixedEnd.checked) fixedEnd.click();
      return true;
    }}
    const controls = [...document.querySelectorAll('input, button, [role="button"], label, span, div, td, tr')]
      .filter(visible);
    const labels = controls.filter((el) => {{
      const text = textOf(el);
      return text.includes('last day') || text.includes('end date');
    }});
    for (const label of labels) {{
      const container = label.closest('label, tr, td, div') || label;
      const input = [...container.querySelectorAll('input')]
        .find((el) => el.type === 'checkbox' || el.type === 'radio');
      if (input) {{
        if (!input.checked) input.click();
        return true;
      }}
      const nearbyInput = [...document.querySelectorAll('input')]
        .filter(visible)
        .find((el) => {{
          const rect = el.getBoundingClientRect();
          const labelRect = label.getBoundingClientRect();
          return Math.abs(rect.top - labelRect.top) < 22 &&
            (el.type === 'checkbox' || el.type === 'radio');
        }});
      if (nearbyInput) {{
        if (!nearbyInput.checked) nearbyInput.click();
        return true;
      }}
      label.click();
      return true;
    }}
    return false;
  }};
  const endDateLabel = () => {{
    const parts = endText.split('/');
    if (parts.length < 2) return '';
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthIndex = Number(parts[0]) - 1;
    const day = String(Number(parts[1]));
    if (!monthNames[monthIndex] || day === 'NaN') return '';
    return `${{day}} ${{monthNames[monthIndex]}}`;
  }};
  const clickEndDateGridCell = () => {{
    const label = endDateLabel();
    if (!label) return false;
    const cell = [...document.querySelectorAll('[role="gridcell"]')]
      .filter(visible)
      .find((el) => (el.getAttribute('aria-label') || '').toLowerCase() === label.toLowerCase());
    if (!cell) return false;
    cell.click();
    return true;
  }};

  if (!location.hash.includes('settings/general')) {{
    location.hash = '#settings/general';
    return `waiting-settings url=${{location.href}} title=${{document.title}}`;
  }}

  const pageText = document.body.innerText.toLowerCase();
  if (!pageText.includes('vacation responder')) {{
    return `waiting-settings url=${{location.href}} title=${{document.title}} text=${{pageText.slice(0, 80)}}`;
  }}

  const vacationNode = [...document.querySelectorAll('td, div, span, label')]
    .filter(visible)
    .find((el) => textOf(el).includes('vacation responder'));
  if (vacationNode) vacationNode.scrollIntoView({{block: 'center'}});

  const inputs = [...document.querySelectorAll('input')].filter(visible);
  const candidates = inputs.filter((el) => {{
    const text = textOf(el);
    return text.includes('sx_') || text.includes('vacation') || text.includes('first day') ||
      text.includes('last day') || text.includes('subject');
  }});

  const onRadio = inputs.find((el) => {{
    const text = textOf(el.parentElement || el);
    return el.type === 'radio' && (text.includes('vacation responder on') || text === 'on');
  }});
  if (onRadio) onRadio.click();
  else clickText(['vacation responder on', 'out of office on']);
  const lastDayEnabled = enableLastDayOption();
  const gridDateClicked = clickEndDateGridCell();

  const refreshedInputs = [...document.querySelectorAll('input')].filter(visible);
  const textInputs = refreshedInputs.filter((el) => {{
    const type = (el.getAttribute('type') || 'text').toLowerCase();
    return ['text', 'date', ''].includes(type);
  }});
  const fixedEndInput = document.querySelector('input[aria-label="Fixed end date"]');
  const fixedEndRow = fixedEndInput?.closest('tr, div, td');
  const fixedEndTextInput = fixedEndRow ?
    [...fixedEndRow.querySelectorAll('input')]
      .filter(visible)
      .find((el) => {{
        const type = (el.getAttribute('type') || 'text').toLowerCase();
        return ['text', 'date', ''].includes(type);
      }}) :
    null;
  const startInput = refreshedInputs.find((el) => {{
    const text = textOf(el);
    return text.includes('first day') || text.includes('start') || text.includes('sx_from');
  }}) || textInputs[0] || candidates[0];
  const endInput = fixedEndTextInput || refreshedInputs.find((el) => {{
    const text = textOf(el);
    return text.includes('last day') || text.includes('end') || text.includes('sx_until');
  }}) || textInputs.find((el) => el !== startInput && textOf(el).includes('/')) || textInputs[1] || candidates[1];
  const subjectInput = refreshedInputs.find((el) => {{
    const text = textOf(el);
    return text.includes('subject') || text.includes('sx_subject');
  }}) || textInputs.find((el) => el !== startInput && el !== endInput);

  if (startInput) setValue(startInput, startText);
  if (endInput) setValue(endInput, endText);
  if (subjectInput && action !== 'focus-subject' && action !== 'focus-body-only') setValue(subjectInput, subject);

  const editors = [
    ...document.querySelectorAll('textarea'),
    ...document.querySelectorAll('[contenteditable="true"]')
  ].filter(visible);
  const bodyEditor = editors.find((el) => textOf(el).includes('message')) || editors[editors.length - 1];

  if (action === 'focus-subject' && subjectInput) {{
    subjectInput.focus();
    subjectInput.click();
    subjectInput.value = '';
    subjectInput.dispatchEvent(new Event('input', {{bubbles: true}}));
    subjectInput.dispatchEvent(new Event('change', {{bubbles: true}}));
    return 'subject-focused';
  }}

  if (bodyEditor) {{
    bodyEditor.focus();
    bodyEditor.click();
    if (bodyEditor.tagName.toLowerCase() === 'textarea') bodyEditor.value = '';
    else bodyEditor.textContent = '';
  }}

  if (!startInput || !endInput || !subjectInput || !bodyEditor) {{
    return `partial start=${{!!startInput}} end=${{!!endInput}} subject=${{!!subjectInput}} body=${{!!bodyEditor}} lastDay=${{lastDayEnabled}} gridDate=${{gridDateClicked}} inputs=${{refreshedInputs.map(textOf).slice(0, 12).join('|')}}`;
  }}

  return (action === 'focus-body' || action === 'focus-body-only') ? `body-focused lastDay=${{lastDayEnabled}} gridDate=${{gridDateClicked}} fixedEndField=${{!!fixedEndTextInput}} end=${{endInput?.value || ''}}` : `filled lastDay=${{lastDayEnabled}} gridDate=${{gridDateClicked}} fixedEndField=${{!!fixedEndTextInput}} end=${{endInput?.value || ''}}`;
}})()
"""


def _gmail_animated_insert_text_js(text: str, delay_seconds: float) -> str:
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
  let el = document.activeElement;
  if (!el || el === document.body) {{
    const editors = [
      ...document.querySelectorAll('textarea'),
      ...document.querySelectorAll('[contenteditable="true"]')
    ].filter(visible);
    el = editors[editors.length - 1];
  }}
  if (!el) return 'insert-target-not-found';
  el.focus();
  const setText = (value) => {{
    if (el.tagName && ['input', 'textarea'].includes(el.tagName.toLowerCase())) {{
      el.value = value;
      el.selectionStart = el.selectionEnd = value.length;
      el.dispatchEvent(new Event('input', {{bubbles: true}}));
      el.dispatchEvent(new Event('change', {{bubbles: true}}));
      return;
    }}
    el.textContent = value;
    const range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
    const selection = window.getSelection();
    if (selection) {{
      selection.removeAllRanges();
      selection.addRange(range);
    }}
    el.dispatchEvent(new Event('input', {{bubbles: true}}));
  }};
  let index = 0;
  const timer = setInterval(() => {{
    if (index >= text.length) {{
      clearInterval(timer);
      el.dispatchEvent(new Event('change', {{bubbles: true}}));
      return;
    }}
    index += 1;
    setText(text.slice(0, index));
  }}, delayMs);
  return 'started';
}})()
"""


def _gmail_save_js(clicked: bool, subject: str) -> str:
    return """
(() => {
  const alreadyClicked = __CLICKED__;
  const subject = __SUBJECT__;
  const visible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const textOf = (el) => [
    el.getAttribute('aria-label'),
    el.getAttribute('data-tooltip'),
    el.getAttribute('title'),
    el.value,
    el.textContent
  ].filter(Boolean).join(' ').trim().toLowerCase();
  const pageText = document.body.innerText.toLowerCase();
  const activeVacationBanner = pageText.includes('end now') &&
    pageText.includes('vacation settings') &&
    (!subject || pageText.includes(subject.toLowerCase()));
  if (activeVacationBanner) return 'saved-confirmed active-vacation-banner';
  if (pageText.includes('settings saved') || pageText.includes('changes saved')) return 'saved-confirmed banner';
  const save = [...document.querySelectorAll('button, input, [role="button"]')]
    .filter(visible)
    .find((el) => {
      const text = textOf(el);
      return text.includes('save changes') || text === 'save';
    });
  if (!save) return 'save-not-found';
  if (save.disabled || save.getAttribute('aria-disabled') === 'true') return 'save-disabled';
  if (alreadyClicked) return 'save-visible-after-click';
  save.click();
  return 'save-clicked';
})()
""".replace("__CLICKED__", str(clicked).lower()).replace("__SUBJECT__", repr(subject))


def _gmail_date(value: date) -> str:
    return f"{value.month}/{value.day}/{value.year}"


def _execute_on_gmail_tab(js_path: Path, account_index: int | str):
    account_url_part = f"mail.google.com/mail/u/{account_index}"
    gmail_url_part = "mail.google.com/mail/"
    script = f'''
set jsSource to read POSIX file "{js_path}"
tell application "Google Chrome"
    activate
    set fallbackWindowIndex to 0
    set fallbackTabIndex to 0
    set gmailUrls to ""
    repeat with windowIndex from 1 to count of windows
        repeat with tabIndex from 1 to count of tabs of window windowIndex
            set tabUrl to URL of tab tabIndex of window windowIndex
            if tabUrl contains "{gmail_url_part}" then
                set gmailUrls to gmailUrls & "[" & windowIndex & ":" & tabIndex & "] " & tabUrl & " "
                if tabUrl contains "settings/general" then
                    set fallbackWindowIndex to windowIndex
                    set fallbackTabIndex to tabIndex
                else if fallbackWindowIndex is 0 then
                    set fallbackWindowIndex to windowIndex
                    set fallbackTabIndex to tabIndex
                end if
            end if
            if tabUrl contains "{account_url_part}" then
                set targetWindow to window windowIndex
                set targetTabIndex to tabIndex as integer
                set active tab index of targetWindow to targetTabIndex
                set index of targetWindow to 1
                delay 0.2
                return execute tab targetTabIndex of targetWindow javascript jsSource
            end if
        end repeat
    end repeat
    if fallbackWindowIndex is not 0 then
        set targetWindow to window fallbackWindowIndex
        set targetTabIndex to fallbackTabIndex as integer
        set active tab index of targetWindow to targetTabIndex
        set index of targetWindow to 1
        delay 0.2
        return execute tab targetTabIndex of targetWindow javascript jsSource
    end if
    return "waiting-gmail-tab urls=" & gmailUrls
end tell
'''
    return run(script)


def _copy_fallback_text(subject: str, message: str) -> None:
    subprocess.run(["pbcopy"], input=f"{subject}\n\n{message}", text=True, check=False)


def _write_temp_js(source: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
    with handle:
        handle.write(source)
    return Path(handle.name)


def _js_string(value: str) -> str:
    return repr(value)
