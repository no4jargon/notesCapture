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

INBOX_DIR="$DATA_DIR/inbox"
ARCHIVE_DIR="$INBOX_DIR/archive"
ENTRIES_DIR="$DATA_DIR/entries"

mkdir -p "$INBOX_DIR" "$ARCHIVE_DIR" "$ENTRIES_DIR"

find "$INBOX_DIR" -maxdepth 1 -type f \( -name '*.txt' -o -name '*.md' \) | sort > "$DATA_DIR/.notesCapture-inbox-list.tmp" || true
INBOX_LIST="$DATA_DIR/.notesCapture-inbox-list.tmp"

imported_any=0
while IFS= read -r file; do
  [[ -n "$file" ]] || continue

  if ! grep -q '[^[:space:]]' "$file"; then
    mv "$file" "$ARCHIVE_DIR/$(basename "$file").empty"
    continue
  fi

  mtime="$(stat -f '%m' "$file")"
  timestamp="$(date -r "$mtime" '+%Y-%m-%d_%H-%M-%S')"
  year="$(date -r "$mtime" '+%Y')"
  month="$(date -r "$mtime" '+%m')"
  day="$(date -r "$mtime" '+%d')"
  device="dropbox-inbox"
  source_name="mobile-capture"
  unique_id="$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -c1-8)"

  entry_dir="$ENTRIES_DIR/$year/$month/$day"
  mkdir -p "$entry_dir"
  entry_file="$entry_dir/$timestamp--$source_name--$device--$unique_id.txt"

  cp "$file" "$entry_file"
  mv "$file" "$ARCHIVE_DIR/$(basename "$file").imported"
  imported_any=1
done < "$INBOX_LIST"

rm -f "$INBOX_LIST"

if [[ "$imported_any" -eq 1 || ! -f "$DATA_DIR/notes.txt" ]]; then
  "$MATERIALIZE_SCRIPT" "$DATA_DIR"
fi
