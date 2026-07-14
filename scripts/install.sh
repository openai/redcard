#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

find_python() {
  for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
        command -v "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON="$(find_python || true)"
if [ -z "$PYTHON" ]; then
  echo "Python 3.11 or newer is required. Install it, then ask Codex to resume Red Card setup."
  exit 1
fi

echo "Using Python: $PYTHON"
if [ -e "$repo_root/.venv" ] || [ -L "$repo_root/.venv" ]; then
  echo "Removing existing Red Card virtual environment: $repo_root/.venv"
  rm -rf -- "$repo_root/.venv"
fi
echo "Creating a fresh Red Card virtual environment."
"$PYTHON" -m venv .venv

pip_install() {
  description="$1"
  shift
  if .venv/bin/python -m pip install "$@"; then
    return 0
  fi

  echo
  echo "Red Card could not install $description using this machine's configured Python package index."
  if [ "${REDCARD_ALLOW_PUBLIC_PYPI:-}" = "1" ]; then
    echo "Retrying $description from public PyPI because REDCARD_ALLOW_PUBLIC_PYPI=1 is set."
    .venv/bin/python -m pip install --index-url https://pypi.org/simple "$@"
    return $?
  fi

  echo "If this machine's package registry is timing out or blocking packages, ask the user before retrying with public PyPI."
  echo "With approval, rerun this installer with REDCARD_ALLOW_PUBLIC_PYPI=1."
  return 1
}

pip_install "pip itself" --upgrade pip
pip_install "Red Card dependencies" --require-hashes -r requirements.txt
./scripts/build-local-overlay.sh
./scripts/build-global-escape.sh

echo "Installed."
echo "Next, Codex should run: ./scripts/install-codex-skill.sh"
echo "Then start Red Card from Codex with: \$redcard"
