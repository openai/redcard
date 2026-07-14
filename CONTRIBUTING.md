# Contributing to Red Card

Thanks for helping improve Red Card.

## Before You Start

- Search existing issues before opening a new one.
- Keep changes focused and explain the user-facing behavior they affect.
- Never include passwords, tokens, private account data, meeting details, or
  other secrets in issues, logs, screenshots, configs, or pull requests.
- Report suspected vulnerabilities privately as described in SECURITY.md.
- Only contribute code, text, artwork, audio, or other media that you created
  or have the right to submit for open-source distribution.

## Local Setup

Red Card targets macOS and requires Python 3.11 or newer. Create the local
development environment and build both native helpers:

~~~sh
./scripts/install.sh
./scripts/build-local-overlay.sh
./scripts/build-global-escape.sh
~~~

The installer downloads hash-locked Python dependencies. If the configured
internal registry is unreachable, do not silently change package sources;
request explicit approval before retrying against official PyPI.

Do not grant permissions or run live automation merely to validate an
unrelated code change. The live flow can send a Meet message, leave a call,
create Calendar events, change a Gmail vacation responder, and sleep the Mac.

## Validation

Run the checks relevant to your change:

~~~sh
PYTHONPYCACHEPREFIX=/private/tmp/redcard-pycache python3 -m compileall redcard tests
.venv/bin/python -m unittest discover -s tests -v
CLANG_MODULE_CACHE_PATH=/private/tmp/redcard-clang-cache swiftc tools/LocalOverlay.swift -o /private/tmp/redcard-local-overlay-test
CLANG_MODULE_CACHE_PATH=/private/tmp/redcard-clang-cache swiftc tools/GlobalEscape.swift -o /private/tmp/redcard-global-escape-test
sh -n scripts/*.sh codex-skill/redcard/scripts/*.sh
~~~

Use ./scripts/run.sh --dry-run only after installing dependencies. Live testing
must use accounts, meetings, and data that you are authorized to modify.

## Pull Requests

- Describe what changed and why.
- Include validation results and list any checks that were skipped.
- Add or update documentation when behavior or configuration changes.
- Keep generated build outputs and local configuration out of commits.
- For artwork, audio, or other media, document its source and confirm that it
  is approved for open-source distribution.
- Complete any contributor license agreement check shown on the pull request;
  a required CLA check must pass before the contribution can be merged.

## Contribution License

By submitting a contribution, you represent that you have the right to submit
it and agree that it is licensed under the Apache License, Version 2.0. Nothing
in this document grants permission to use OpenAI trademarks or branding.
