#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_ENV="$REPO_ROOT/config/config.env"

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
NOTES_FILE="$DATA_DIR/notes.txt"
TMP_FILE="$DATA_DIR/.notes.txt.tmp"

mkdir -p "$DATA_DIR"

find "$ENTRIES_DIR" -type f -name '*.txt' 2>/dev/null | sort > "$DATA_DIR/.notesCapture-entry-list.tmp" || true
ENTRY_LIST="$DATA_DIR/.notesCapture-entry-list.tmp"

if [[ ! -s "$ENTRY_LIST" ]]; then
  rm -f "$ENTRY_LIST"
  if [[ ! -f "$NOTES_FILE" ]]; then
    : > "$NOTES_FILE"
  fi
  exit 0
fi

: > "$TMP_FILE"
while IFS= read -r file; do
  [[ -n "$file" ]] || continue
  if ! grep -q '[^[:space:]]' "$file"; then
    continue
  fi

  base="$(basename "$file")"
  prefix="${base%%--*}"
  if [[ "$prefix" == "$base" ]]; then
    prefix="${base%.txt}"
  fi

  display_ts="$(echo "$prefix" | sed -E 's/^([0-9]{4}-[0-9]{2}-[0-9]{2})_([0-9]{2})-([0-9]{2})-([0-9]{2})$/\1 \2:\3:\4/')"
  printf '[%s]\n' "$display_ts" >> "$TMP_FILE"
  cat "$file" >> "$TMP_FILE"
  printf '\n\n' >> "$TMP_FILE"
done < "$ENTRY_LIST"

mv "$TMP_FILE" "$NOTES_FILE"
rm -f "$ENTRY_LIST"
