#!/usr/bin/env sh
set -eu

echo "Checking Chrome JavaScript from Apple Events."
echo "Chrome must have View > Developer > Allow JavaScript from Apple Events enabled."

ERROR_FILE=$(mktemp "${TMPDIR:-/tmp}/redcard-chrome-js.XXXXXX")
cleanup() {
  rm -f "$ERROR_FILE"
}
trap cleanup 0 HUP INT TERM

CHROME_JS_RESULT=""
CHROME_JS_STATUS=0
if CHROME_JS_RESULT=$(osascript 2>"$ERROR_FILE" <<'APPLESCRIPT'
tell application "Google Chrome"
    activate

    set createdWindow to false
    if (count of windows) is 0 then
        make new window
        set createdWindow to true
    end if

    set targetWindow to front window
    set checkTab to make new tab at end of tabs of targetWindow with properties {URL:"data:text/html,<title>Red%20Card%20JavaScript%20Check</title>"}
    set checkTabIndex to count of tabs of targetWindow
    set targetTabIndex to checkTabIndex as integer
    set active tab index of targetWindow to checkTabIndex
    set checkResult to ""
    set lastErrorMessage to ""
    set lastErrorNumber to 0

    try
        repeat with attemptNumber from 1 to 8
            try
                set checkResult to execute tab targetTabIndex of targetWindow javascript "\"redcard-js-events-ok\""
                if checkResult is "redcard-js-events-ok" then exit repeat
            on error errorMessage number errorNumber
                set lastErrorMessage to errorMessage
                set lastErrorNumber to errorNumber
                if errorMessage contains "JavaScript through AppleScript is turned off" then error errorMessage number errorNumber
            end try
            delay 0.25
        end repeat

        if checkResult is not "redcard-js-events-ok" and lastErrorMessage is not "" then
            error lastErrorMessage number lastErrorNumber
        end if
        try
            close checkTab
        end try
        if createdWindow then
            try
                close targetWindow
            end try
        end if
        return checkResult
    on error errorMessage number errorNumber
        try
            close checkTab
        end try
        if createdWindow then
            try
                close targetWindow
            end try
        end if
        error errorMessage number errorNumber
    end try
end tell
APPLESCRIPT
); then
  if [ "$CHROME_JS_RESULT" = "redcard-js-events-ok" ]; then
    echo "Chrome JavaScript from Apple Events looks good."
    exit 0
  fi
else
  CHROME_JS_STATUS=$?
fi

CHROME_JS_ERROR=$(sed -e 's/[[:space:]]*$//' "$ERROR_FILE")

echo
case "$CHROME_JS_ERROR" in
  *"JavaScript through AppleScript is turned off"*|*"Allow JavaScript from Apple Events"*)
    echo "Chrome has JavaScript from Apple Events turned off."
    echo "In Chrome, enable View > Developer > Allow JavaScript from Apple Events."
    echo "Then ask ChatGPT to resume Red Card setup or run the permission check again."
    ;;
  *"Not authorized to send Apple events"*|*"not authorized to send Apple events"*|*"Not authorised to send Apple events"*|*"Operation not permitted"*|*"privilege violation"*|*"-1743"*|*"-10004"*)
    echo "ChatGPT was not allowed to send Apple Events to Chrome."
    echo "This does not mean Chrome's JavaScript from Apple Events setting is off."
    echo "Codex must rerun the installed Red Card launcher outside the workspace sandbox."
    ;;
  *)
    echo "Red Card could not confirm Chrome JavaScript from Apple Events."
    echo "This does not prove that the Chrome setting is off."
    ;;
esac

if [ -n "$CHROME_JS_ERROR" ]; then
  echo "AppleScript details: $CHROME_JS_ERROR"
elif [ -n "$CHROME_JS_RESULT" ]; then
  echo "Unexpected Chrome result: $CHROME_JS_RESULT"
else
  echo "AppleScript exited with status $CHROME_JS_STATUS without returning a result."
fi
exit 1
