from __future__ import annotations

import json
from pathlib import Path

from events_agents.common.ids import stable_hash
from events_agents.time_use.models import CanonicalJournalEvent


def iter_canonical_journal_events(data_dir: Path):
    journal_root = data_dir / "journal"
    for journal_path in sorted(journal_root.rglob("*.ndjson")):
        relative_path = journal_path.relative_to(data_dir).as_posix()
        bucket_date = f"{journal_path.parent.parent.name}-{journal_path.parent.name}-{journal_path.stem.zfill(2)}"
        with journal_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                raw_event = json.loads(line)
                event_id = raw_event.get("event_id")
                canonical_event_uid = event_id or stable_hash({
                    "journal_path": relative_path,
                    "journal_line_no": line_no,
                    "raw_line": line,
                })
                content = raw_event.get("content") if isinstance(raw_event.get("content"), dict) else {}
                producer = raw_event.get("producer") if isinstance(raw_event.get("producer"), dict) else {}
                ingress = raw_event.get("ingress") if isinstance(raw_event.get("ingress"), dict) else {}
                yield CanonicalJournalEvent(
                    canonical_event_uid=canonical_event_uid,
                    journal_path=relative_path,
                    journal_line_no=line_no,
                    journal_bucket_date=bucket_date,
                    event_id=event_id,
                    event_type=raw_event.get("kind", "unknown"),
                    schema_name=raw_event.get("schema_name"),
                    schema_version=str(raw_event.get("schema_version")) if raw_event.get("schema_version") is not None else None,
                    captured_at=raw_event["captured_at"],
                    committed_at=raw_event.get("received_at"),
                    source_client=producer.get("id"),
                    source_transport=ingress.get("transport"),
                    content_type=content.get("mime_type"),
                    text_body=content.get("text") if isinstance(content.get("text"), str) else None,
                    raw_event_json=raw_event,
                )
