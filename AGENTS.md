# Red Card Codex Guide

This repo is designed to be opened in the ChatGPT macOS app and operated through Codex. The normal Codex activation path is the repo-owned `$redcard` skill.

## Operating Style

- Act like a hands-on project guide, not a docs search engine.
- Guide one step at a time when the user is setting up or troubleshooting the app.
- Do not dump a full build plan unless the user asks for one. Give the next concrete action, wait for the user to do the physical step or report output, then continue.
- Run all shell commands and project scripts for the user through Codex. Never ask the user to open Terminal, paste a command, or run a script themselves.
- Before fresh setup, tell the user to open **ChatGPT > Settings > General > Permissions** and turn **Auto-review** off. Wait for the user to confirm before running the installer so required outside-sandbox requests are presented to the user instead of being auto-reviewed.
- Run `./scripts/install-codex-skill.sh` outside the workspace sandbox on the first attempt during fresh setup. It installs the complete self-contained runtime, so do not run the repo development installer first. Request narrowly scoped approval for the exact skill installer; do not grant a shell or the whole project unrestricted access.
- If dependency installation fails or times out while using the machine's configured Python package index, stop and preserve the installer output. Ask the user whether they want Codex to retry the installer using public PyPI. Only retry with `REDCARD_ALLOW_PUBLIC_PYPI=1` after explicit approval; never silently bypass a corporate or internal package registry, and never commit private registry URLs.
- Launch real Red Card and camera diagnostics outside the workspace sandbox on the first attempt. Request narrowly scoped approval for the installed Red Card launcher; do not switch the whole project or ChatGPT session to unrestricted access.
- Resolve the launcher from the actual directory of the loaded `$redcard` `SKILL.md`. Never look for `run-redcard.sh` in the repo's top-level `scripts/` directory. Use `${CODEX_HOME:-$HOME/.codex}/skills/redcard` only as the portable fallback.
- Before each command you run, say what it does and why it happens now.
- After each step, say what success looks like.
- If a step fails, stop and diagnose before continuing.
- Only ask the user to perform actions Codex cannot do, such as responding to a macOS permission prompt, changing a System Settings toggle, signing into Google, or enabling a Chrome menu option.
- Prefer exact commands in tool calls and exact UI labels in user instructions over conceptual summaries.
- Use practical, reassuring language. Avoid extra background unless the user asks.
- Do not ask the user to paste passwords, API keys, or private tokens into chat.
- Do not run destructive commands unless the user explicitly approves.
- Do not revert user changes unless explicitly asked.

## Project Summary

Red Card watches for a physical red card through the webcam. When detected during a Google Meet call, it runs the full sequence:

1. Sends a configured goodbye message in Google Meet.
2. Leaves the Meet call.
3. Creates and saves a Google Calendar block.
4. Opens Gmail settings and saves a vacation responder.
5. Shows the native referee overlay and final goodbye screen.

The default entrypoint is:

```text
$redcard
```

The default config is:

```text
redcard.config.json
```

## Guide Behavior

The README is the public handoff. Once the user asks for help setting up, running, or debugging Red Card, Codex should become the guide.

Start with a short response like:

```text
You are in the right place. I will walk through this one step at a time. We will start by checking the local setup, then confirm macOS permissions, then run Red Card and fix anything that comes up.
```

Do not tell the user to read `AGENTS.md`. Load project files yourself as needed.

For each setup or troubleshooting step, use this rhythm:

1. Say the goal of this step in one sentence.
2. Run the required command yourself, or give the one physical/UI action only the user can perform.
3. Say what success looks like.
4. For a required UI action, ask the user to tell you when it is done. For commands, inspect the tool output yourself.

Examples:

- For install, run `./scripts/install-codex-skill.sh` outside the sandbox because it writes under `${CODEX_HOME:-$HOME/.codex}` and downloads dependencies; verify the installed `SKILL.md`, `runtime/.venv`, bundled configs/assets, and native helpers.
- For skill setup, explain that `codex-skill/redcard` is the source instructions; `./scripts/install-codex-skill.sh` creates/replaces the discoverable `$redcard` skill and its complete self-contained runtime.
- For fresh setup, first wait for the user to turn off **Auto-review** at **ChatGPT > Settings > General > Permissions**. Then let `./scripts/install-codex-skill.sh` invoke the installed launcher with `--force-permissions`; do not invoke it a second time. Run `./scripts/permissions-check.sh` directly only when troubleshooting a failed installer preflight.
- For camera issues, run `<skill-dir>/scripts/run-redcard.sh --list-cameras` before changing config.
- For Chrome automation issues, run `./scripts/check-chrome-javascript.sh` through Codex outside the sandbox. It must preserve the actual AppleScript error and only direct the user to **View > Developer > Allow JavaScript from Apple Events** when Chrome explicitly reports that the setting is off. Apple Events authorization, sandbox, timing, and unexpected-result failures must not be mislabeled as a disabled Chrome setting.
- For overlay issues, run `./scripts/build-local-overlay.sh` and compile-check `tools/LocalOverlay.swift`.
- For first run, use plain `$redcard` so the real sequence runs and the default sleep-after-goodbye behavior is preserved.
- For explicit troubleshooting only, use `$redcard --dry-run`; it must not request camera access.
- For live-flow issues where the user explicitly wants a bounded test, use `$redcard --once`.
- Run plain `$redcard`, `--once`, `--list-cameras`, `--permissions-only`, and `--force-permissions` outside the sandbox immediately. Keep only `--dry-run`, `--help`, and `-h` sandboxed.
- During a real run, keep the command session open. As soon as the runtime reports `Red Card is running and ready to go`, explicitly tell the user that Red Card is running and ready. Do not wait for the watcher to exit, and do not announce readiness if startup fails before that message.

Use checklist-style progress internally, but keep the user-facing conversation focused on the current step. If the user asks "what's next?", answer with the next step, not the whole remaining setup.

## First Move

Infer where the user is in the Red Card flow before taking action:

- If they are setting up a fresh clone, first ask them to turn off **Auto-review** at **ChatGPT > Settings > General > Permissions** and wait for confirmation. Then run only `./scripts/install-codex-skill.sh` outside the sandbox. The installer copies and builds the runtime under the installed skill, then runs `--force-permissions`. Explain that Codex is registering a project-independent `$redcard` runtime and checking this machine; do not hand the command to the user. After success, stop and prompt the user to invoke `$redcard` separately when ready.
- If they are trying to run the app from any task, resolve the loaded skill directory, confirm `<skill-dir>/runtime/.venv/bin/python` exists, and invoke `<skill-dir>/scripts/run-redcard.sh`. Do not inspect the current project's `.venv` or look for the Red Card repo.
- If they report a macOS permission issue, start with the permissions check and the exact System Settings paths.
- If they report Chrome or Google automation failures, start by checking the relevant helper in `redcard/macos/` and confirm Chrome Apple Events is enabled.
- If they report camera behavior, start with `<skill-dir>/scripts/run-redcard.sh --list-cameras` and inspect `redcard/detector.py` only after confirming the camera opens.
- If they report overlay positioning, animation, or final-screen behavior, inspect `tools/LocalOverlay.swift`, `redcard/demo_overlay.py`, `redcard/demo_sequence.py`, and `assets/sprites/`.
- If they ask for a code change, inspect the relevant files first, then implement and verify.

Opening responses:

- Fresh setup: first require **Auto-review** to be off at **ChatGPT > Settings > General > Permissions** and wait for confirmation. Then run environment installation and skill registration outside the sandbox. The skill installer forces a new permission preflight for the current machine, including a real Chrome JavaScript-from-Apple-Events test. If a check fails, guide the exact macOS or Chrome UI setting and resume installation only after the user fixes it. After setup succeeds, stop and prompt the user to invoke `$redcard` separately for the first real run.
- After setup: tell the user to invoke plain `$redcard` for the first real run.
- Runtime error: ask for or inspect the traceback, identify the failing module, then make the smallest targeted fix.
- Visual/overlay issue: inspect the overlay and sprite code, then compile-check Swift before finishing.
- Git request: check status first, preserve unrelated user work, then stage/commit/push only after the requested change is complete.

Only ask a clarifying question if the request conflicts with local context or if making a reasonable assumption would be risky.

## Setup Guidance

For first-time setup, Codex runs from the Red Card source repository:

```sh
./scripts/install-codex-skill.sh
```

Before running the installer, Codex tells the user to open **ChatGPT > Settings > General > Permissions**, turn **Auto-review** off, and report when it is done. Codex must wait for that confirmation. Do not substitute Full access for this step.

Codex runs this command outside the workspace sandbox on its first attempt. It needs network access for hash-locked dependencies and write access to `${CODEX_HOME:-$HOME/.codex}`. Do not wait for a sandboxed install to fail.

If the installer fails while installing Python packages, preserve the pip output. When the error looks like a timeout, unreachable package index, or registry policy issue, ask the user whether they want to retry using public PyPI. If they approve, rerun the same installer outside the sandbox with `REDCARD_ALLOW_PUBLIC_PYPI=1`. Do not retry public PyPI automatically.

`scripts/install.sh` remains available for repo development only. Normal users do not need a repo-local `.venv` because the skill installer builds `<skill-dir>/runtime/.venv`.

`scripts/install-codex-skill.sh` creates/replaces `${CODEX_HOME:-$HOME/.codex}/skills/redcard`, copies the runtime package, configs, assets, native sources, and runtime scripts into `<skill-dir>/runtime`, creates its virtual environment, builds its helpers, and invokes `<skill-dir>/scripts/run-redcard.sh --force-permissions`. It must not record or require the source repo path. After installation, `$redcard` runs from any task or project even if the source repo is not the task's working directory. If `$redcard` is not visible immediately, tell the user to start a fresh task or reload ChatGPT once.

The skill installer must not report success until Camera, System Events/Accessibility, Input Monitoring, and Chrome JavaScript-from-Apple-Events checks pass. The Chrome check opens a temporary harmless tab, executes a sentinel expression through Apple Events, and closes the tab. It must run even when the saved macOS permission stamp is still valid. Once setup succeeds, stop the setup flow and tell the user that setup is complete and they can invoke `$redcard` when ready. Never invoke the launcher again or automatically turn a successful fresh-install preflight into a real run.

### Skill Build Contract

- Treat `codex-skill/redcard/` as the only editable source of the `$redcard` skill. Never edit `${CODEX_HOME:-$HOME/.codex}/skills/redcard` directly.
- Keep `codex-skill/redcard/SKILL.md`, `codex-skill/redcard/agents/openai.yaml`, and both skill scripts synchronized when the workflow changes.
- Keep launcher examples anchored to `<skill-dir>`, with `${CODEX_HOME:-$HOME/.codex}/skills/redcard` only as the fallback. Never add a repo-relative `./scripts/run-redcard.sh` example.
- After changing the skill source, validate it with the skill validator, run `sh -n` on its scripts, run `./scripts/install-codex-skill.sh`, and verify the installed files match the source copy.
- `scripts/install-codex-skill.sh` must fail if a required skill file is missing, if the launcher is not executable, or if the installed copy differs from the source.
- The installed launcher must use only `<skill-dir>/runtime`; it must never infer runtime files from the current working directory or a recorded source repo path.
- `scripts/install-codex-skill.sh` must delete any old installed stamp and run the installed launcher with `--force-permissions` during normal installation. It must never accept a repo-path stamp as proof of permissions on the current machine. `REDCARD_SKIP_INSTALL_PERMISSIONS=1` is only for isolated maintainer validation and must never be set during user setup.

After setup, prompt the user to invoke plain `$redcard`, not `$redcard --dry-run`, `$redcard --once`, `$redcard --no-sleep`, or a runtime script directly. Setup uses the installed launcher's `--force-permissions` mode outside the sandbox; it records success for the installed runtime only after the current machine passes and exits before the real sequence. Only a later explicit `$redcard` invocation starts Red Card. Scope reusable approval to the absolute installed `run-redcard.sh` path. `$redcard --dry-run` and `$redcard --help` remain sandboxed and skip camera access.

For a permission repair, run `<skill-dir>/scripts/run-redcard.sh --force-permissions` outside the sandbox on the first attempt. This must ignore the repo-specific success stamp, rerun the macOS preflight so Camera can be requested correctly, update the stamp only on success, and stop without launching Red Card. Prefer this installed-launcher mode over running `scripts/permissions-check.sh` directly.

Required user-facing permissions and settings:

- **System Settings > Privacy & Security > Camera**: enable **ChatGPT**.
- **System Settings > Privacy & Security > Accessibility**: enable **ChatGPT**. If it is missing, click **+** and add ChatGPT from `/Applications`.
- **System Settings > Privacy & Security > Input Monitoring**: enable **ChatGPT** if macOS asks for it so global Esc can abort while Chrome is focused.
- Chrome: enable **View > Developer > Allow JavaScript from Apple Events**. The installer and every real launch verify this setting and stop with this exact instruction when Chrome blocks the test.
- Chrome must already be signed into the relevant Google Meet, Calendar, and Gmail accounts.

After permission changes, tell the user to quit and reopen ChatGPT before invoking `$redcard` again.

## Local Overlay

The native overlay helper is built locally from:

```text
tools/LocalOverlay.swift
```

The output is:

```text
bin/redcard-local-overlay
bin/redcard-global-escape
```

After pulling changes or switching machines, Codex runs:

```sh
./scripts/build-local-overlay.sh
./scripts/build-global-escape.sh
```

The app can auto-build the helper if needed, but Codex should still run the explicit rebuild step during setup so the binary matches the local macOS toolchain.

## Running and Verification

Use the installed skill runtime from any task:

```text
$redcard
```

For user troubleshooting from any task, Codex uses the installed launcher. Repo scripts remain for development checks only:

```sh
./scripts/run.sh
./scripts/run.sh --once
./scripts/run.sh --dry-run
./scripts/run.sh --list-cameras
```

When validating code changes, prefer:

```sh
PYTHONPYCACHEPREFIX=/private/tmp/redcard-pycache python3 -m compileall redcard
CLANG_MODULE_CACHE_PATH=/private/tmp/redcard-clang-cache swiftc tools/LocalOverlay.swift -o /private/tmp/redcard-local-overlay-test
sh -n scripts/*.sh
```

Use cache paths under `/private/tmp` for Python and Swift compile checks so sandboxed runs do not write to user-level caches.

Do not run `./scripts/permissions-check.sh` casually during validation; it can open the camera and trigger macOS permission prompts.

## Development Notes

- Keep runtime console messages client-facing. Avoid internal wording like "demo" in printed output.
- Emit `Red Card is running and ready to go` only after runtime initialization succeeds and immediately before waiting for or watching a Meet call, so Codex has a reliable readiness signal to relay to the user.
- Keep `--dry-run` as a safe preview path.
- Keep global Esc abort available during real runs, including while Chrome is focused. The Swift helper is built from `tools/GlobalEscape.swift` and launched by `redcard/global_escape.py`.
- Have the global Esc helper call `CGRequestListenEventAccess()` when Input Monitoring access is missing so macOS presents its permission prompt. Use a listen-only event tap. Give manual System Settings instructions only after the request is denied, dismissed, or cannot be shown again.
- Keep Meet waiting passive. The idle wait should not activate Chrome, select the Meet tab, or steal focus from another Chrome tab.
- The stricter active Meet check can run when acting on a detected red card, but idle polling should avoid JavaScript that raises Chrome.
- If the camera is not needed yet, do not open it. The app should wait for a likely Meet call tab before starting the camera, and release the camera when the call ends.
- Gracefully continue if no active call is found after a red card detection.
- After a red card is successfully handled, return `"triggered"` from the detector and exit cleanly instead of reading another camera frame after the sequence. A guarded trigger that returns `False` must keep watching.
- Be careful with AppleScript changes: Chrome, Gmail, Calendar, and Meet UI automation can be brittle. Prefer small, targeted changes and clear error messages.
- For asset changes, keep sprite folders under `assets/sprites/`.
- The `pocket` sprite set is used for the opening red-card animation.
- The final goodbye screen uses `assets/sprites/goodbye-screen.png` as the only centered full-screen graphic.

## File Map

- `redcard/cli.py`: CLI, config loading, Meet wait loop, camera lifecycle.
- `redcard/detector.py`: webcam red-card detection.
- `redcard/demo_sequence.py`: full sequence choreography.
- `redcard/demo_overlay.py`: Python controller for the native overlay.
- `redcard/local_overlay.py`: builds or locates the Swift overlay helper.
- `redcard/global_escape.py`: builds or locates the Swift global Esc helper and starts it for real runs.
- `tools/LocalOverlay.swift`: native transparent overlay renderer.
- `tools/GlobalEscape.swift`: native global Esc listener that interrupts the Red Card Python process.
- `redcard/macos/chrome.py`: Google Meet and Chrome automation.
- `redcard/macos/calendar.py`: Google Calendar automation.
- `redcard/macos/gmail.py`: Gmail vacation responder automation.
- `scripts/install.sh`: local environment setup.
- `codex-skill/redcard/scripts/install-runtime.sh`: builds the installed skill's private runtime environment.
- `scripts/permissions-check.sh`: first-run macOS permission helper.
- `scripts/check-chrome-javascript.sh`: blocking Chrome JavaScript-from-Apple-Events probe.
- `scripts/run.sh`: main launcher through `.venv/bin/python`.
- `scripts/build-local-overlay.sh`: local Swift overlay rebuild.
- `scripts/build-global-escape.sh`: local Swift global Esc helper rebuild.

## Safety

- Never ask users to paste secrets into chat.
- Never assume macOS permissions are already granted; run the preflight through Codex and guide the user through any required System Settings changes.
- Never use destructive git commands unless explicitly requested.
- The user may have local uncommitted changes. Inspect status before broad edits, and preserve unrelated work.
