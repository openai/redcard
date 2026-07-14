#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_dir="$repo_root/codex-skill/redcard"
target_dir="${CODEX_HOME:-$HOME/.codex}/skills/redcard"
runtime_dir="$target_dir/runtime"

required_files="SKILL.md agents/openai.yaml scripts/install-runtime.sh scripts/run-redcard.sh"
for relative_path in $required_files; do
  if [ ! -f "$source_dir/$relative_path" ]; then
    echo "Could not find required Red Card skill source file:"
    echo "$source_dir/$relative_path"
    exit 1
  fi
done

rm -rf "$target_dir"
mkdir -p "$target_dir"
cp -R "$source_dir/SKILL.md" "$source_dir/agents" "$source_dir/scripts" "$target_dir/"
mkdir -p "$target_dir/references"
mkdir -p "$runtime_dir/scripts"
cp -R "$repo_root/redcard" "$repo_root/assets" "$repo_root/tools" "$runtime_dir/"
cp "$repo_root/requirements.txt" "$repo_root/redcard.config.json" "$runtime_dir/"
cp "$repo_root/scripts/run.sh" "$repo_root/scripts/permissions-check.sh" "$repo_root/scripts/check-chrome-javascript.sh" "$repo_root/scripts/build-local-overlay.sh" "$repo_root/scripts/build-global-escape.sh" "$runtime_dir/scripts/"
chmod +x "$target_dir/scripts/install-runtime.sh" "$target_dir/scripts/run-redcard.sh" "$runtime_dir/scripts/"*.sh
if [ ! -x "$target_dir/scripts/run-redcard.sh" ]; then
  echo "The installed Red Card skill launcher is missing or not executable:"
  echo "$target_dir/scripts/run-redcard.sh"
  exit 1
fi

for relative_path in $required_files; do
  if ! cmp -s "$source_dir/$relative_path" "$target_dir/$relative_path"; then
    echo "The installed Red Card skill does not match its source file:"
    echo "$relative_path"
    exit 1
  fi
done

for relative_path in redcard/__main__.py assets/sprites/goodbye-screen.png assets/referee-whistle.wav tools/LocalOverlay.swift tools/GlobalEscape.swift requirements.txt redcard.config.json scripts/run.sh scripts/permissions-check.sh scripts/check-chrome-javascript.sh scripts/build-local-overlay.sh scripts/build-global-escape.sh; do
  if [ ! -f "$runtime_dir/$relative_path" ]; then
    echo "The installed Red Card runtime is missing:"
    echo "$runtime_dir/$relative_path"
    exit 1
  fi
done

"$target_dir/scripts/install-runtime.sh"

echo "Installed the Red Card Codex skill at:"
echo "$target_dir"
echo
if [ "${REDCARD_SKIP_INSTALL_PERMISSIONS:-}" = "1" ]; then
  echo "Installed skill files only. The install-time permissions preflight was skipped because REDCARD_SKIP_INSTALL_PERMISSIONS=1."
  echo "Red Card installation is not complete until the permissions preflight passes."
else
  echo "Forcing a fresh check of required macOS permissions and Chrome automation on this machine."
  "$target_dir/scripts/run-redcard.sh" --force-permissions
  echo
  echo 'Red Card installation is complete. Invoke $redcard when you are ready to start it.'
fi
