#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TIMESTAMP_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]$")


@dataclass
class Entry:
    timestamp: datetime
    text: str


def parse_legacy_notes(content: str) -> list[Entry]:
    entries: list[Entry] = []
    current_timestamp: datetime | None = None
    current_lines: list[str] = []

    for raw_line in content.splitlines():
        match = TIMESTAMP_RE.match(raw_line.strip())
        if match:
            if current_timestamp is not None:
                text = "\n".join(current_lines).strip()
                if text:
                    entries.append(Entry(timestamp=current_timestamp, text=text))
            current_timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
            current_lines = []
            continue

        if current_timestamp is not None:
            current_lines.append(raw_line)

    if current_timestamp is not None:
        text = "\n".join(current_lines).strip()
        if text:
            entries.append(Entry(timestamp=current_timestamp, text=text))

    return entries


def materialize_notes(data_dir: Path) -> None:
    entries_dir = data_dir / "entries"
    notes_file = data_dir / "notes.txt"
    entry_files = sorted(entries_dir.rglob("*.txt"))

    chunks: list[str] = []
    for path in entry_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        prefix = path.stem.split("--", 1)[0]
        try:
            timestamp = datetime.strptime(prefix, "%Y-%m-%d_%H-%M-%S")
            display_ts = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            display_ts = prefix.replace("_", " ")
        chunks.append(f"[{display_ts}]\n{text}\n")

    notes_file.write_text("\n".join(chunks) + ("\n" if chunks else ""), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: import_legacy_notes.py <legacy-notes-file> <data-dir>")
        return 1

    legacy_file = Path(sys.argv[1]).expanduser().resolve()
    data_dir = Path(sys.argv[2]).expanduser().resolve()

    if not legacy_file.exists():
        print(f"Legacy notes file not found: {legacy_file}")
        return 1

    entries_dir = data_dir / "entries"
    legacy_dir = data_dir / "legacy"
    entries_dir.mkdir(parents=True, exist_ok=True)
    legacy_dir.mkdir(parents=True, exist_ok=True)

    content = legacy_file.read_text(encoding="utf-8")
    entries = parse_legacy_notes(content)
    if not entries:
        print(f"No timestamped entries found in {legacy_file}")
        return 1

    imported = 0
    for index, entry in enumerate(entries, start=1):
        day_dir = entries_dir / entry.timestamp.strftime("%Y") / entry.timestamp.strftime("%m") / entry.timestamp.strftime("%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{entry.timestamp.strftime('%Y-%m-%d_%H-%M-%S')}--legacy-import--migrated-{index:04d}.txt"
        target = day_dir / filename
        if target.exists():
            continue
        target.write_text(entry.text.rstrip() + "\n", encoding="utf-8")
        imported += 1

    archive_path = legacy_dir / f"{legacy_file.stem}-imported-source{legacy_file.suffix}"
    if not archive_path.exists():
        shutil.copy2(legacy_file, archive_path)

    materialize_notes(data_dir)
    print(f"Imported {imported} entries from {legacy_file} into {data_dir}")
    print(f"Archived source copy at {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
