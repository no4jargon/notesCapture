#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repartition journal files by captured_at day.")
    parser.add_argument("data_dir", help="notesCapture data directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir).expanduser().resolve()
    summary = repartition_journal(data_dir)
    print(f"EVENT_COUNT={summary['event_count']}")
    print(f"SOURCE_FILE_COUNT={summary['source_file_count']}")
    print(f"OUTPUT_FILE_COUNT={summary['output_file_count']}")
    return 0


def repartition_journal(data_dir: Path) -> dict[str, int]:
    journal_dir = data_dir / "journal"
    if not journal_dir.exists():
        return {"event_count": 0, "source_file_count": 0, "output_file_count": 0}

    source_files = sorted(journal_dir.rglob("*.ndjson"))
    if not source_files:
        return {"event_count": 0, "source_file_count": 0, "output_file_count": 0}

    buckets: dict[Path, list[str]] = defaultdict(list)
    event_count = 0

    for source_file in source_files:
        for line in source_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            captured_at = parse_timestamp(payload["captured_at"])
            bucket = journal_dir / captured_at.strftime("%Y") / captured_at.strftime("%m") / f"{captured_at.strftime('%d')}.ndjson"
            buckets[bucket].append(json.dumps(payload, ensure_ascii=False))
            event_count += 1

    backup_dir = data_dir / "state" / "journal-repartition-backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(journal_dir), str(backup_dir))
    journal_dir.mkdir(parents=True, exist_ok=True)

    for output_file, lines in sorted(buckets.items(), key=lambda item: item[0].as_posix()):
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "event_count": event_count,
        "source_file_count": len(source_files),
        "output_file_count": len(buckets),
    }


def parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


if __name__ == "__main__":
    sys.exit(main())
