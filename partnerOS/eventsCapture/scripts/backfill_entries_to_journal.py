#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill legacy entries into the canonical journal.")
    parser.add_argument("data_dir", help="notesCapture data directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir).expanduser().resolve()
    summary = backfill_entries_to_journal(data_dir)

    print(f"BACKFILLED_COUNT={summary['backfilled_count']}")
    print(f"SKIPPED_COUNT={summary['skipped_count']}")
    print(f"EMPTY_COUNT={summary['empty_count']}")
    return 0


def backfill_entries_to_journal(data_dir: Path) -> dict[str, int]:
    entries_dir = data_dir / "entries"
    journal_dir = data_dir / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)

    existing_note_keys = load_existing_note_keys(journal_dir)

    backfilled_count = 0
    skipped_count = 0
    empty_count = 0

    for entry_path in sorted(entries_dir.rglob("*.txt")):
        raw_text = entry_path.read_text(encoding="utf-8")
        text = normalize_text(raw_text)
        if not text:
            empty_count += 1
            continue

        captured_at = infer_captured_at(entry_path)
        note_key = make_note_key(captured_at, text)
        if note_key in existing_note_keys:
            skipped_count += 1
            continue

        source_name, device_name = infer_source_and_device(entry_path)
        event = {
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "kind": "note.capture",
            "captured_at": captured_at,
            "received_at": captured_at,
            "producer": {
                "type": infer_producer_type(source_name),
                "id": device_name,
                "version": "backfill-from-entries",
            },
            "client_event_id": f"entry-backfill:{hashlib.sha256(entry_path.relative_to(data_dir).as_posix().encode('utf-8')).hexdigest()}",
            "content": {
                "mime_type": "text/plain",
                "text": text,
            },
            "metadata": {
                "backfilled_from_entry": entry_path.relative_to(data_dir).as_posix(),
                "entry_source_name": source_name,
                "entry_device": device_name,
            },
            "blobs": [],
            "parents": [],
            "ingress": {
                "transport": "entries-backfill",
                "path": entry_path.relative_to(data_dir).as_posix(),
            },
        }
        append_event_to_journal(journal_dir, event)
        existing_note_keys.add(note_key)
        backfilled_count += 1

    return {
        "backfilled_count": backfilled_count,
        "skipped_count": skipped_count,
        "empty_count": empty_count,
    }


def load_existing_note_keys(journal_dir: Path) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
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
            keys.add(make_note_key(captured_at, normalized_text))
    return keys


def infer_captured_at(entry_path: Path) -> str:
    base = entry_path.stem
    prefix = base.split("--", 1)[0]
    try:
        parsed = datetime.strptime(prefix, TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise ValueError(f"Could not parse entry timestamp from {entry_path}") from exc

    local_tz = datetime.now().astimezone().tzinfo
    return parsed.replace(tzinfo=local_tz).isoformat()


def infer_source_and_device(entry_path: Path) -> tuple[str, str]:
    parts = entry_path.stem.split("--")
    source_name = parts[1] if len(parts) >= 2 and parts[1] else "entry-backfill"
    device_name = parts[2] if len(parts) >= 3 and parts[2] else "entries"
    return source_name, device_name


def infer_producer_type(source_name: str) -> str:
    if source_name == "mobile-capture":
        return "mobile-file-drop"
    if source_name == "mac-hotkey":
        return "mac-hotkey"
    if source_name == "legacy-import":
        return "legacy-import"
    return source_name


def append_event_to_journal(journal_dir: Path, event: dict[str, Any]) -> None:
    captured_at = parse_timestamp(event["captured_at"])
    journal_path = journal_dir / captured_at.strftime("%Y") / captured_at.strftime("%m") / f"{captured_at.strftime('%d')}.ndjson"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False))
        handle.write("\n")


def parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def make_note_key(captured_at: str, text: str) -> tuple[str, str]:
    return captured_at, normalize_text(text)


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


if __name__ == "__main__":
    sys.exit(main())
