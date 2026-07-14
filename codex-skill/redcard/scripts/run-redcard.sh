#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
skill_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
runtime_dir="$skill_dir/runtime"
stamp_path="$skill_dir/references/permissions-ok"

if [ ! -d "$runtime_dir" ]; then
  echo "The installed Red Card skill does not contain its runtime payload:"
  echo "$runtime_dir"
  echo "Ask ChatGPT to reinstall the Red Card skill from its source repository."
  exit 1
fi

if [ ! -x "$runtime_dir/.venv/bin/python" ] || [ ! -x "$runtime_dir/scripts/run.sh" ]; then
  echo "The installed Red Card runtime is not set up yet."
  echo "Ask ChatGPT to reinstall the Red Card skill from its source repository."
  exit 1
fi

if [ ! -x "$runtime_dir/scripts/permissions-check.sh" ]; then
  echo "Missing executable permissions check script:"
  echo "$runtime_dir/scripts/permissions-check.sh"
  exit 1
fi

cd "$runtime_dir"

stamp_matches=false
if [ -f "$stamp_path" ] && grep -Fqx "runtime=$runtime_dir" "$stamp_path"; then
  stamp_matches=true
fi

skip_preflight=false
permissions_only=false
force_permissions=false
preflight_ran=false
for arg in "$@"; do
  case "$arg" in
    --dry-run|-h|--help)
      skip_preflight=true
      ;;
    --permissions-only)
      permissions_only=true
      ;;
    --force-permissions)
      permissions_only=true
      force_permissions=true
      ;;
  esac
done

if [ "$permissions_only" = true ] && [ "$#" -ne 1 ]; then
  echo "--permissions-only and --force-permissions must be used by themselves."
  exit 2
fi

if [ "$skip_preflight" = true ]; then
  echo "Skipping Red Card permissions preflight for this safe command."
elif [ "$force_permissions" = true ] || [ "${REDCARD_FORCE_PERMISSIONS:-}" = "1" ] || [ "$stamp_matches" = false ]; then
  echo "Checking Red Card permissions..."
  if ! ./scripts/permissions-check.sh; then
    echo
    echo "Red Card permissions preflight did not pass."
    echo "If this was a camera issue, Codex should run:"
    echo "$skill_dir/scripts/run-redcard.sh --list-cameras"
    echo
    echo "Success means at least one camera reports ok with a resolution."
    exit 1
  fi
  preflight_ran=true
  mkdir -p "$(dirname "$stamp_path")"
  {
    printf 'runtime=%s\n' "$runtime_dir"
    printf 'checked_at=%s\n' "$(date)"
  } > "$stamp_path"
else
  echo "Red Card permissions preflight already passed for this installed runtime. Use --force-permissions to run it again without starting Red Card."
fi

if [ "$skip_preflight" = false ] && [ "$preflight_ran" = false ]; then
  echo
  echo "Rechecking Chrome JavaScript from Apple Events before continuing..."
  if ! ./scripts/check-chrome-javascript.sh; then
    echo
    echo "Red Card cannot continue until Chrome allows JavaScript from Apple Events."
    exit 1
  fi
fi

if [ "$permissions_only" = true ]; then
  echo
  if [ "$force_permissions" = true ]; then
    echo "Red Card permissions preflight completed. Red Card was not started."
  else
    echo "Red Card setup and permissions are complete."
    echo 'When you are ready to start Red Card, invoke $redcard in ChatGPT.'
  fi
  exit 0
fi

echo
echo "Starting Red Card..."
exec ./scripts/run.sh "$@"
