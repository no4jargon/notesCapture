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

mkdir -p "$DATA_DIR"

python3 - "$DATA_DIR" <<'PY'
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


data_dir = Path(sys.argv[1])
journal_dir = data_dir / "journal"
views_dir = data_dir / "views"
views_notes_file = views_dir / "notes.txt"
tmp_views_file = views_dir / ".notes.txt.tmp"

views_dir.mkdir(parents=True, exist_ok=True)

renderable_events = []
for journal_file in sorted(journal_dir.rglob("*.ndjson")):
    for line in journal_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("kind") != "note.capture":
            continue
        content = payload.get("content")
        if not isinstance(content, dict):
            continue
        if content.get("mime_type") not in {"text/plain", "text/markdown"}:
            continue
        text = content.get("text")
        captured_at = payload.get("captured_at")
        if not isinstance(text, str) or not isinstance(captured_at, str):
            continue
        normalized_text = normalize_text(text)
        if not normalized_text:
            continue
        renderable_events.append(
            {
                "captured_at": captured_at,
                "captured_at_dt": parse_timestamp(captured_at),
                "text": normalized_text,
                "event_id": str(payload.get("event_id", "")),
            }
        )

renderable_events.sort(key=lambda item: (item["captured_at_dt"], item["event_id"]))

rendered = "".join(
    f"[{item['captured_at_dt'].strftime('%Y-%m-%d %H:%M:%S')}]\n{item['text']}\n\n"
    for item in renderable_events
)

tmp_views_file.write_text(rendered, encoding="utf-8")
os.replace(tmp_views_file, views_notes_file)

legacy_notes_file = data_dir / "notes.txt"
if legacy_notes_file.exists():
    legacy_notes_file.unlink()
PY
