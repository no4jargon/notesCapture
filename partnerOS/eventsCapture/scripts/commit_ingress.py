#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceConfig:
    root: Path
    source_name: str
    producer_type: str
    producer_id: str
    transport: str


@dataclass
class Summary:
    committed_count: int = 0
    duplicate_count: int = 0
    rejected_count: int = 0
    empty_count: int = 0


class ValidationError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Commit ingress captures into the canonical journal.")
    parser.add_argument("data_dir", help="notesCapture data directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir).expanduser().resolve()
    summary = commit_ingress(data_dir)

    print(f"COMMITTED_COUNT={summary.committed_count}")
    print(f"DUPLICATE_COUNT={summary.duplicate_count}")
    print(f"REJECTED_COUNT={summary.rejected_count}")
    print(f"EMPTY_COUNT={summary.empty_count}")
    return 0


def commit_ingress(data_dir: Path) -> Summary:
    summary = Summary()

    ingress_dir = data_dir / "ingress"
    journal_dir = data_dir / "journal"
    rejects_dir = data_dir / "rejects"
    dedupe_dir = data_dir / "state" / "dedupe"

    for path in [ingress_dir, journal_dir, rejects_dir, dedupe_dir]:
        path.mkdir(parents=True, exist_ok=True)

    sources = [
        SourceConfig(
            root=ingress_dir / "dropbox",
            source_name="mobile-capture",
            producer_type="mobile-file-drop",
            producer_id="dropbox-ingress",
            transport="dropbox-file-drop",
        ),
        SourceConfig(
            root=ingress_dir / "local",
            source_name="mac-hotkey",
            producer_type="mac-hotkey",
            producer_id="local-ingress",
            transport="local-file-drop",
        ),
    ]

    for source in sources:
        source.root.mkdir(parents=True, exist_ok=True)
        for file_path in iter_ingress_files(source.root):
            outcome = process_file(
                data_dir=data_dir,
                journal_dir=journal_dir,
                rejects_dir=rejects_dir,
                dedupe_dir=dedupe_dir,
                source=source,
                file_path=file_path,
            )
            if outcome == "committed":
                summary.committed_count += 1
            elif outcome == "duplicate":
                summary.duplicate_count += 1
            elif outcome == "rejected":
                summary.rejected_count += 1
            elif outcome == "empty":
                summary.empty_count += 1

    return summary


def iter_ingress_files(source_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        if "archive" in path.parts:
            continue
        if path.suffix.lower() not in {".txt", ".md", ".json"}:
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.as_posix())


def process_file(
    *,
    data_dir: Path,
    journal_dir: Path,
    rejects_dir: Path,
    dedupe_dir: Path,
    source: SourceConfig,
    file_path: Path,
) -> str:
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        reject_file(
            rejects_dir=rejects_dir,
            source=source,
            file_path=file_path,
            reason=f"File is not valid UTF-8: {exc}",
        )
        return "rejected"

    if not raw_text.strip():
        archive_file(source_root=source.root, file_path=file_path, suffix=".empty")
        return "empty"

    received_at_dt = datetime.now().astimezone().replace(microsecond=0)

    try:
        if file_path.suffix.lower() == ".json":
            event = build_event_from_json(
                data_dir=data_dir,
                source=source,
                file_path=file_path,
                raw_text=raw_text,
                received_at_dt=received_at_dt,
            )
        else:
            event = build_event_from_text(
                data_dir=data_dir,
                source=source,
                file_path=file_path,
                raw_text=raw_text,
                received_at_dt=received_at_dt,
            )
    except ValidationError as exc:
        reject_file(rejects_dir=rejects_dir, source=source, file_path=file_path, reason=str(exc))
        return "rejected"

    dedupe_marker_path: Path | None = None
    dedupe_key = build_dedupe_key(event)
    if dedupe_key is not None:
        dedupe_marker_path = dedupe_dir / f"{hashlib.sha256(dedupe_key.encode('utf-8')).hexdigest()}.json"
        if dedupe_marker_path.exists():
            archive_file(source_root=source.root, file_path=file_path, suffix=".duplicate")
            return "duplicate"

    append_event_to_journal(journal_dir=journal_dir, event=event)

    if dedupe_marker_path is not None:
        marker_payload = {
            "event_id": event["event_id"],
            "client_event_id": event["client_event_id"],
            "producer_id": event["producer"]["id"],
            "received_at": event["received_at"],
        }
        write_json_file(dedupe_marker_path, marker_payload)

    archive_file(source_root=source.root, file_path=file_path, suffix=".imported")
    return "committed"


def build_event_from_text(
    *,
    data_dir: Path,
    source: SourceConfig,
    file_path: Path,
    raw_text: str,
    received_at_dt: datetime,
) -> dict[str, Any]:
    captured_at_dt = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc).astimezone().replace(microsecond=0)
    normalized_text = normalize_text(raw_text)
    mime_type = "text/markdown" if file_path.suffix.lower() == ".md" else "text/plain"

    event: dict[str, Any] = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "kind": "note.capture",
        "captured_at": format_timestamp(captured_at_dt),
        "received_at": format_timestamp(received_at_dt),
        "producer": {
            "type": source.producer_type,
            "id": source.producer_id,
            "version": "transitional-file-drop",
        },
        "content": {
            "mime_type": mime_type,
            "text": normalized_text,
        },
        "metadata": {},
        "blobs": [],
        "parents": [],
        "ingress": {
            "transport": source.transport,
            "path": file_path.relative_to(data_dir).as_posix(),
        },
    }
    return event


def build_event_from_json(
    *,
    data_dir: Path,
    source: SourceConfig,
    file_path: Path,
    raw_text: str,
    received_at_dt: datetime,
) -> dict[str, Any]:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValidationError("JSON payload must be an object")

    validate_capture_event_v1(payload)

    captured_at = format_timestamp(parse_rfc3339(payload["captured_at"], field_name="captured_at"))

    producer = dict(payload["producer"])
    producer["type"] = producer["type"].strip()
    producer["id"] = producer["id"].strip()

    content = dict(payload["content"])
    content["mime_type"] = content["mime_type"].strip()
    if isinstance(content.get("text"), str):
        content["text"] = normalize_text(content["text"])

    metadata = payload.get("metadata", {})
    blobs = payload.get("blobs", [])
    parents = payload.get("parents", [])

    event: dict[str, Any] = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "kind": payload["kind"].strip(),
        "captured_at": captured_at,
        "received_at": format_timestamp(received_at_dt),
        "producer": producer,
        "content": content,
        "metadata": metadata,
        "blobs": blobs,
        "parents": parents,
        "ingress": {
            "transport": source.transport,
            "path": file_path.relative_to(data_dir).as_posix(),
        },
    }

    client_event_id = payload.get("client_event_id")
    if client_event_id is not None:
        event["client_event_id"] = client_event_id.strip()

    return event


def validate_capture_event_v1(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != 1:
        raise ValidationError("schema_version must be 1")

    kind = payload.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        raise ValidationError("kind must be a non-empty string")

    parse_rfc3339(payload.get("captured_at"), field_name="captured_at")

    producer = payload.get("producer")
    if not isinstance(producer, dict):
        raise ValidationError("producer must be an object")
    if not isinstance(producer.get("type"), str) or not producer["type"].strip():
        raise ValidationError("producer.type must be a non-empty string")
    if not isinstance(producer.get("id"), str) or not producer["id"].strip():
        raise ValidationError("producer.id must be a non-empty string")

    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValidationError("content must be an object")
    if not isinstance(content.get("mime_type"), str) or not content["mime_type"].strip():
        raise ValidationError("content.mime_type must be a non-empty string")

    has_primary_content = False
    for field_name in ["text", "url", "blob_ref"]:
        value = content.get(field_name)
        if isinstance(value, str) and value.strip():
            has_primary_content = True
            break
    if not has_primary_content:
        raise ValidationError("content must include at least one non-empty field among text, url, or blob_ref")

    client_event_id = payload.get("client_event_id")
    if client_event_id is not None and (not isinstance(client_event_id, str) or not client_event_id.strip()):
        raise ValidationError("client_event_id must be a non-empty string when present")

    metadata = payload.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValidationError("metadata must be an object when present")

    blobs = payload.get("blobs")
    if blobs is not None and not isinstance(blobs, list):
        raise ValidationError("blobs must be a list when present")

    parents = payload.get("parents")
    if parents is not None and not isinstance(parents, list):
        raise ValidationError("parents must be a list when present")


def parse_rfc3339(value: Any, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty RFC 3339 timestamp")

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a valid RFC 3339 timestamp") from exc

    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must include a timezone offset")

    return parsed.astimezone().replace(microsecond=0)


def build_dedupe_key(event: dict[str, Any]) -> str | None:
    client_event_id = event.get("client_event_id")
    if not isinstance(client_event_id, str) or not client_event_id:
        return None

    producer = event.get("producer", {})
    producer_id = producer.get("id") if isinstance(producer, dict) else None
    if not isinstance(producer_id, str) or not producer_id:
        return None

    return f"{producer_id}\n{client_event_id}"


def append_event_to_journal(*, journal_dir: Path, event: dict[str, Any]) -> None:
    captured_at = parse_rfc3339(event["captured_at"], field_name="captured_at")
    journal_path = journal_dir / captured_at.strftime("%Y") / captured_at.strftime("%m") / f"{captured_at.strftime('%d')}.ndjson"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False))
        handle.write("\n")


def reject_file(*, rejects_dir: Path, source: SourceConfig, file_path: Path, reason: str) -> None:
    now = datetime.now().astimezone()
    reject_base = rejects_dir / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d") / sanitize_filename(source.root.name)
    relative_path = file_path.relative_to(source.root)
    destination = make_unique_path(reject_base / relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(file_path), str(destination))

    reason_path = destination.with_name(destination.name + ".reason.txt")
    reason_path.write_text(reason.rstrip("\n") + "\n", encoding="utf-8")


def archive_file(*, source_root: Path, file_path: Path, suffix: str) -> None:
    archive_root = source_root / "archive"
    relative_path = file_path.relative_to(source_root)
    destination = archive_root / relative_path
    destination = make_unique_path(destination.with_name(destination.name + suffix))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(file_path), str(destination))


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    candidate = path
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.{counter}")
        counter += 1
    return candidate


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def format_timestamp(value: datetime) -> str:
    return value.astimezone().replace(microsecond=0).isoformat()


def sanitize_filename(value: str) -> str:
    sanitized = []
    previous_dash = False
    for char in value:
        is_allowed = char.isalnum() or char in {"-", "_"}
        next_char = char if is_allowed else "-"
        if next_char == "-":
            if previous_dash:
                continue
            previous_dash = True
        else:
            previous_dash = False
        sanitized.append(next_char)

    result = "".join(sanitized).strip("-")
    return result or "unknown"


if __name__ == "__main__":
    sys.exit(main())
