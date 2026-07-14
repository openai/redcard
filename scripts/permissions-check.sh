#!/usr/bin/env sh
set -eu

HOST_APP_NAME="${REDCARD_HOST_APP_NAME:-ChatGPT}"
export HOST_APP_NAME

if [ ! -d .venv ]; then
  echo "Missing .venv. Codex should run ./scripts/install.sh first."
  exit 1
fi

. .venv/bin/activate

echo "Red Card permissions check"
echo
echo "macOS permission prompts are per app on this computer."
echo "This check asks macOS to show Camera and Input Monitoring prompts when access is missing, and it checks Accessibility access."
echo "It also verifies Chrome's JavaScript from Apple Events setting instead of assuming it is enabled."
echo "If access was previously denied, macOS may not prompt again; enable it in System Settings instead."
echo "Enable ${HOST_APP_NAME}, not Terminal."
echo
echo "1. Checking camera access. macOS may prompt you to allow ${HOST_APP_NAME} to use the camera."
python - <<'PY'
import cv2
import os

host_app_name = os.environ["HOST_APP_NAME"]

last_opened = None
for index in range(8):
    capture = cv2.VideoCapture(index)
    try:
        if not capture.isOpened():
            continue
        last_opened = index
        ok, frame = capture.read()
        if ok and frame is not None and frame.size > 0:
            height, width = frame.shape[:2]
            print(f"Camera access looks good on camera {index} ({width}x{height}).")
            break
    finally:
        capture.release()
else:
    if last_opened is None:
        raise SystemExit(f"No camera opened. Allow camera access for {host_app_name}, then invoke $redcard again.")
    raise SystemExit(
        "A camera opened but did not return a frame. Close other camera apps, check Camera permission, and invoke $redcard again."
    )
PY

echo
echo "2. Checking Accessibility. macOS may prompt you to allow ${HOST_APP_NAME} to control System Events."
if ACCESSIBILITY_APP="$(osascript <<'APPLESCRIPT' 2>/dev/null
tell application "System Events"
    if UI elements enabled is false then error "UI scripting is not enabled."
    set frontApp to first application process whose frontmost is true
    set frontName to name of frontApp
    return frontName
end tell
APPLESCRIPT
)"; then
  echo "Accessibility check looks good. Red Card can read UI state from: ${ACCESSIBILITY_APP}"
else
  echo "Accessibility access was not confirmed."
  echo "Enable ${HOST_APP_NAME} in System Settings > Privacy & Security > Accessibility."
  echo "Then quit and reopen ${HOST_APP_NAME} before invoking \$redcard again."
  exit 1
fi

echo
echo "3. Checking global Escape access. macOS should prompt for Input Monitoring if access has not been decided."
if [ ! -x ./bin/redcard-global-escape ]; then
  echo "The global Escape helper is missing. Codex should run ./scripts/build-global-escape.sh."
  exit 1
fi
if ./bin/redcard-global-escape --check; then
  echo "Global Escape access looks good."
else
  echo "Global Escape access was not confirmed."
  echo "If a macOS permission prompt is visible, allow ${HOST_APP_NAME}."
  echo "If macOS did not show a prompt because access was previously denied, enable ${HOST_APP_NAME} in System Settings > Privacy & Security > Input Monitoring."
  echo "Then quit and reopen ${HOST_APP_NAME} before invoking \$redcard again."
  exit 1
fi

echo
echo "4. Checking Chrome JavaScript from Apple Events. Chrome may open a temporary harmless tab."
if ! ./scripts/check-chrome-javascript.sh; then
  exit 1
fi

echo
echo "If ${HOST_APP_NAME} was not already listed, macOS should now show it in:"
echo "  System Settings > Privacy & Security > Camera"
echo "  System Settings > Privacy & Security > Accessibility"
echo "  System Settings > Privacy & Security > Input Monitoring"
echo
echo "Enable ${HOST_APP_NAME}. If it is missing, click + and add it from /Applications."
echo "After permission changes, quit and reopen ${HOST_APP_NAME} before invoking \$redcard again."
