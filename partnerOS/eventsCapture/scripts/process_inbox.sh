#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_ENV="$REPO_ROOT/config/config.env"
COMMIT_SCRIPT="$REPO_ROOT/scripts/commit_ingress.py"
MATERIALIZE_SCRIPT="$REPO_ROOT/scripts/materialize_notes.sh"

DATA_DIR="${1:-${NOTESCAPTURE_DATA_DIR:-}}"
if [[ -z "$DATA_DIR" && -f "$CONFIG_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_ENV"
  DATA_DIR="${DATA_DIR:-}"
fi

if [[ -z "$DATA_DIR" ]]; then
  echo "Usage: $0 <data-dir>"
  exit 1
fi

mkdir -p "$DATA_DIR"

summary="$(python3 "$COMMIT_SCRIPT" "$DATA_DIR")"
committed_count="$(printf '%s\n' "$summary" | awk -F= '/^COMMITTED_COUNT=/{print $2}')"

if [[ -z "$committed_count" ]]; then
  echo "Failed to parse commit summary from $COMMIT_SCRIPT" >&2
  exit 1
fi

if [[ "$committed_count" -gt 0 || ! -f "$DATA_DIR/views/notes.txt" ]]; then
  "$MATERIALIZE_SCRIPT" "$DATA_DIR"
fi
