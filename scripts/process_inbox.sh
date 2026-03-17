#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_ENV="$REPO_ROOT/config/config.env"
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

ENTRIES_DIR="$DATA_DIR/entries"
INGRESS_DIR="$DATA_DIR/ingress"
DROPBOX_INGRESS_DIR="$INGRESS_DIR/dropbox"
LOCAL_INGRESS_DIR="$INGRESS_DIR/local"
TMP_LIST="$DATA_DIR/.notesCapture-inbox-list.tmp"

mkdir -p "$ENTRIES_DIR" "$DROPBOX_INGRESS_DIR" "$LOCAL_INGRESS_DIR"

imported_any=0

import_from_source_dir() {
  local source_dir="$1"
  local source_name="$2"
  local device="$3"
  local archive_dir="$source_dir/archive"

  mkdir -p "$source_dir" "$archive_dir"
  find "$source_dir" -maxdepth 1 -type f \( -name '*.txt' -o -name '*.md' \) | sort > "$TMP_LIST" || true

  while IFS= read -r file; do
    [[ -n "$file" ]] || continue

    if ! grep -q '[^[:space:]]' "$file"; then
      mv "$file" "$archive_dir/$(basename "$file").empty"
      continue
    fi

    local mtime timestamp year month day unique_id entry_dir entry_file
    mtime="$(stat -f '%m' "$file")"
    timestamp="$(date -r "$mtime" '+%Y-%m-%d_%H-%M-%S')"
    year="$(date -r "$mtime" '+%Y')"
    month="$(date -r "$mtime" '+%m')"
    day="$(date -r "$mtime" '+%d')"
    unique_id="$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -c1-8)"

    entry_dir="$ENTRIES_DIR/$year/$month/$day"
    mkdir -p "$entry_dir"
    entry_file="$entry_dir/$timestamp--$source_name--$device--$unique_id.txt"

    cp "$file" "$entry_file"
    mv "$file" "$archive_dir/$(basename "$file").imported"
    imported_any=1
  done < "$TMP_LIST"
}

import_from_source_dir "$DROPBOX_INGRESS_DIR" "mobile-capture" "dropbox-ingress"
import_from_source_dir "$LOCAL_INGRESS_DIR" "mac-hotkey" "local-ingress"

rm -f "$TMP_LIST"

if [[ "$imported_any" -eq 1 || ! -f "$DATA_DIR/notes.txt" ]]; then
  "$MATERIALIZE_SCRIPT" "$DATA_DIR"
fi
