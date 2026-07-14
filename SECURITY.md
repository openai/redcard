# Security Policy

## Supported Versions

Security fixes are made on the current default branch. Older snapshots and
locally modified builds are not separately supported.

## Reporting a Vulnerability

Do not report a suspected vulnerability in a public issue.

Use the repository host's private vulnerability-reporting feature when it is
available. For vulnerabilities that affect OpenAI products or services, use
the OpenAI Coordinated Vulnerability Disclosure Program:
https://openai.com/security/disclosure/

Do not include passwords, tokens, private meeting links, email content, or
other secrets. Please include:

- A description of the issue and its impact.
- The affected file, version, or commit.
- Minimal reproduction steps that avoid real third-party accounts when
  possible.
- Any suggested mitigation.

Maintainers will investigate the report and coordinate remediation and
disclosure as appropriate.

## Security-Sensitive Behavior

Red Card uses the camera and macOS Accessibility, Input Monitoring, and
Automation permissions. It can control Chrome, type into Google Meet, leave a
call, create Google Calendar events, change a Gmail vacation responder, access
the clipboard, and sleep the Mac.

Only test the live flow with accounts, meetings, and data you are authorized
to use. Prefer dry-run mode during development:

~~~sh
./scripts/run.sh --dry-run
~~~

Do not publish configs, screenshots, or logs containing personal account
details. Treat UI automation changes as security-sensitive and obtain the
required Security and Legal reviews before a public release.
