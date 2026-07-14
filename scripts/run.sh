#!/usr/bin/env sh
set -eu

if [ ! -x .venv/bin/python ]; then
  echo "Missing .venv. Codex should run ./scripts/install.sh first."
  exit 1
fi

export PYTHONUNBUFFERED=1
exec .venv/bin/python -m redcard "$@"
