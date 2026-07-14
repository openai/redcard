---
name: redcard
description: Install, diagnose, and run the self-contained Red Card runtime through Codex in the ChatGPT macOS app from any task or project. Use when the user invokes $redcard or asks Codex to install, configure, troubleshoot, or run Red Card. Codex owns every shell command and requests scoped outside-sandbox execution for installation, dependency downloads, and real runs that need macOS hardware or app access; the user only handles required approval, macOS, Chrome, and Google-account UI actions.
---

# Red Card

## Run

When the user invokes `$redcard`, resolve `<skill-dir>` from the actual path of this loaded `SKILL.md`, then invoke:

```sh
<skill-dir>/scripts/run-redcard.sh
```

Replace `<skill-dir>` with the real directory containing this `SKILL.md`; do not execute the angle-bracket placeholder literally. The current task directory does not matter. The launcher enters `<skill-dir>/runtime` itself, so invoke it from any project or task without locating the source repository.

The launcher and runtime are bundled inside the installed skill. Never look for `run-redcard.sh`, `.venv`, configs, assets, or helpers in the current project. If the loaded skill path is unavailable, use `${CODEX_HOME:-$HOME/.codex}/skills/redcard` as the portable fallback. Verify `<skill-dir>/scripts/run-redcard.sh` and `<skill-dir>/runtime/.venv/bin/python` before launching. If either is missing, tell the user the installed skill is incomplete and ask them to open the Red Card source repository once so Codex can rerun its installer.

For a real run, invoke the launcher outside the workspace sandbox on the first attempt. Do not try the same real command inside the sandbox first. Request scoped escalation with a concise explanation that Red Card needs macOS Camera, Accessibility, Input Monitoring, System Events, and Chrome Apple Events access. When the execution tool supports reusable command approval, scope it to the absolute installed `run-redcard.sh` launcher path, not to a shell or general interpreter.

Treat plain `$redcard`, `--once`, `--list-cameras`, `--permissions-only`, `--force-permissions`, and any invocation that can open the camera or automate macOS apps as commands requiring outside-sandbox execution.

Keep `--dry-run`, `--help`, and `-h` inside the sandbox because they must not open the camera or automate apps. If `--list-cameras` is combined with another flag, treat the invocation as real and run it outside the sandbox.

After setup, use plain `$redcard` for the first real run. Do not add `--dry-run`, `--once`, or `--no-sleep` unless the user explicitly asks for a preview, bounded troubleshooting run, or no-sleep override.

Pass through any runtime flags the user requested:

```sh
<skill-dir>/scripts/run-redcard.sh --once
<skill-dir>/scripts/run-redcard.sh --dry-run
<skill-dir>/scripts/run-redcard.sh --list-cameras
<skill-dir>/scripts/run-redcard.sh --config /absolute/path/to/redcard.config.json
```

The launcher always runs from `<skill-dir>/runtime`, which contains the Python package, virtual environment, default configs, assets, Swift sources, native helpers, and runtime scripts. It does not read a repo path or inspect the current project. It runs the bundled `runtime/scripts/permissions-check.sh` when needed, then runs `runtime/scripts/run.sh`.

`--permissions-only` is an internal setup mode. It runs or confirms the installed runtime's permission preflight and exits without starting Red Card. Never pass it through as a normal runtime option.

`--force-permissions` is the internal install and repair mode. Run it outside the workspace sandbox to ignore an existing permission stamp, force the macOS preflight to request Camera and other required access again, update the stamp only after success, and exit without starting Red Card. Use it by itself.

For a real run, keep the command session open. When the runtime emits `Red Card is running and ready to go`, immediately tell the user: "Red Card is running and ready to go." Do not wait for the long-running watcher to exit before giving this confirmation. Do not claim readiness before that runtime message appears; if startup fails first, diagnose the error instead.

Skip the permissions preflight for `--dry-run`, `--help`, and `-h`, because those commands should not request camera access.

The permission preflight accepts any camera index that returns frames. This avoids failing on camera `0` when the working webcam is another index.

During a real run, Esc should abort Red Card globally, including while Chrome is focused. The global Esc preflight calls macOS's Input Monitoring request API so a first-time user receives a system permission prompt. Ask the user to use System Settings only if macOS does not prompt because access was previously denied or the prompt was dismissed.

## Setup Expectations

Codex runs all setup and diagnostic commands. Never ask the user to open Terminal, paste a command, run a script, or report shell output manually.

For first installation or an incomplete installed runtime, open the Red Card source repository once and run this through Codex:

```sh
./scripts/install-codex-skill.sh
```

Before running the installer, tell the user exactly: open **ChatGPT > Settings > General > Permissions** and turn **Auto-review** off. Wait for the user to confirm it is off before continuing. Do not substitute Full access and do not attempt to inspect or change this app setting from a shell command.

Run the installer outside the workspace sandbox on the first attempt. It writes under `${CODEX_HOME:-$HOME/.codex}`, copies the complete runtime payload, creates `<skill-dir>/runtime/.venv`, installs hash-locked dependencies, builds native helpers, and runs the permission preflight. Request narrowly scoped approval for the exact installer; do not request broad shell or project access.

If dependency installation fails or times out while using the machine's configured Python package index, preserve the installer output and stop. Ask the user whether they want Codex to retry the installer using public PyPI as the package source. Only after the user approves, rerun the same source-repo installer outside the sandbox with `REDCARD_ALLOW_PUBLIC_PYPI=1` set. Do not silently bypass a corporate or internal package registry, and do not hardcode any private registry URL in the repo or installed skill.

`scripts/install-codex-skill.sh` must replace the installed skill, copy the required runtime into `<skill-dir>/runtime`, build its environment locally, discard any old permission stamp, and invoke the new launcher with `--force-permissions` before reporting success. Never retain a dependency on the source repo or treat a matching path as proof of permissions. The preflight records success only after the current machine passes and exits without starting Red Card. Do not invoke the launcher a second time after the installer succeeds.

When the skill installer and its permission check succeed, stop. Do not retry the original real invocation or start `scripts/run.sh` in the same setup flow. Tell the user: "Red Card is installed and its permissions are checked. Invoke `$redcard` when you are ready to start it."

Only a separate, explicit `$redcard` invocation from the user starts the real sequence after fresh setup.

If the launcher reports an incomplete runtime, do not search the current project for runtime files. Ask the user to open the Red Card source repository once, rerun `./scripts/install-codex-skill.sh` through Codex, let its forced permission preflight finish, and stop before a real run.

## Permissions

The permissions preflight requests macOS prompts for the app running the skill. If prompted, guide the user to allow **ChatGPT**. Use these System Settings locations only when macOS does not prompt or access was previously denied:

- **System Settings > Privacy & Security > Camera**
- **System Settings > Privacy & Security > Accessibility**
- **System Settings > Privacy & Security > Input Monitoring**

The preflight must run `scripts/check-chrome-javascript.sh`, not merely remind the user about Chrome. This check must also run when a saved macOS permission stamp lets the launcher skip the other checks, including on install and every real run. Follow the checker's classified error: give the **View > Developer > Allow JavaScript from Apple Events** instruction only when Chrome explicitly reports that JavaScript through AppleScript is turned off. If it reports an Apple Events authorization, sandbox, or other execution error, preserve those details and diagnose that path instead of claiming the Chrome setting is off. Never allow a failure to pass quietly.

Only ask the user to perform UI actions Codex cannot complete, including responding to macOS permission prompts, changing System Settings, signing into Google, or enabling the Chrome menu option. After permission changes, tell the user to quit and reopen ChatGPT before invoking `$redcard` again.

To force the permissions preflight to run again:

```sh
<skill-dir>/scripts/run-redcard.sh --force-permissions
```

Invoke this outside the workspace sandbox on the first attempt. Request scoped approval for the absolute installed launcher path so Camera access is attributed to the host app correctly. Do not run `scripts/permissions-check.sh` directly unless the launcher mode itself is being diagnosed.

If the permissions preflight fails on camera access, Codex runs this from any working directory and interprets the result:

```sh
<skill-dir>/scripts/run-redcard.sh --list-cameras
```

Success means at least one camera reports `ok` with a resolution.
