from __future__ import annotations

import json
import re
import uuid
from datetime import timedelta

from events_agents.common.time import parse_iso_datetime
from events_agents.llm.backend import default_backend, load_prompt
from events_agents.time_use.models import CanonicalJournalEvent, TimeUseEvidence

EXTRACT_SYSTEM_PROMPT = load_prompt("extract_system.txt")


def _category_for(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["debug", "worked", "cisco", "stocks"]):
        return "deep_work"
    if any(token in lowered for token in ["meeting", "session", "call", "spoke to"]):
        return "meetings"
    if any(token in lowered for token in ["instagram", "youtube", "doomscroll"]):
        return "leisure"
    if any(token in lowered for token in ["gym", "worked out", "exercise"]):
        return "exercise"
    if any(token in lowered for token in ["lunch", "breakfast", "dinner", "ate", "food"]):
        return "meals"
    if any(token in lowered for token in ["friends", "birthday", "social", "chill", "movie", "dentist"]):
        return "social"
    if any(token in lowered for token in ["message", "whatsapp", "replied"]):
        return "communication"
    if "sleep" in lowered or "slept" in lowered:
        return "sleep"
    return "unknown"


def _make_evidence(event: CanonicalJournalEvent, payload: dict) -> TimeUseEvidence:
    return TimeUseEvidence(
        evidence_id=str(uuid.uuid4()),
        canonical_event_uid=event.canonical_event_uid,
        source_event_type=event.event_type,
        actuality=str(payload["actuality"]),
        observed_day_local=payload.get("observed_day_local"),
        observed_start_at=payload.get("observed_start_at"),
        observed_end_at=payload.get("observed_end_at"),
        anchor_time_at=str(payload.get("anchor_time_at") or event.captured_at),
        temporal_mode=str(payload["temporal_mode"]),
        activity_text=str(payload["activity_text"]),
        category=str(payload.get("category") or _category_for(str(payload["activity_text"]))),
        subcategory=payload.get("subcategory"),
        confidence=str(payload.get("confidence") or "low"),
        supporting_snippet=str(payload.get("supporting_snippet") or event.text_body or ""),
        derivation_notes=str(payload.get("derivation_notes") or "llm extraction"),
    )


def _confidence_for(mode: str, actuality: str) -> str:
    if actuality == "planned":
        return "low"
    if mode in {"explicit_interval", "relative_interval"}:
        return "high"
    if mode == "point":
        return "medium"
    return "low"


def _heuristic_evidence(event: CanonicalJournalEvent, text: str, actuality: str, mode: str, start_at: str | None, end_at: str | None) -> TimeUseEvidence:
    anchor = event.captured_at
    observed_day = (start_at or end_at or anchor)[:10]
    return TimeUseEvidence(
        evidence_id=str(uuid.uuid4()),
        canonical_event_uid=event.canonical_event_uid,
        source_event_type=event.event_type,
        actuality=actuality,
        observed_day_local=observed_day,
        observed_start_at=start_at,
        observed_end_at=end_at,
        anchor_time_at=anchor,
        temporal_mode=mode,
        activity_text=text.strip(),
        category=_category_for(text),
        subcategory=None,
        confidence=_confidence_for(mode, actuality),
        supporting_snippet=text.strip(),
        derivation_notes="heuristic fallback extraction",
    )


def _resolve_hour(hour: int, minute: int, captured_hour: int) -> tuple[int, int]:
    if hour == 12:
        return hour, minute
    if hour <= 7 and captured_hour >= 12:
        return hour + 12, minute
    return hour, minute


def _heuristic_extract(event: CanonicalJournalEvent) -> list[TimeUseEvidence]:
    text = (event.text_body or "").strip()
    if not text:
        return []

    captured = parse_iso_datetime(event.captured_at)
    parts = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    evidence: list[TimeUseEvidence] = []

    for part in parts:
        lowered = part.lower()

        duration_match = re.search(r"spent the last (\d+) hours? (.+)", lowered)
        if duration_match:
            hours = int(duration_match.group(1))
            start = captured - timedelta(hours=hours)
            evidence.append(_heuristic_evidence(event, part, "retrospective_actual", "relative_interval", start.isoformat(), captured.isoformat()))
            continue

        explicit_match = re.search(r"from (\d{1,2}) to (\d{1,2}) ?(am|pm) i was (.+)", lowered)
        if explicit_match:
            start_hour = int(explicit_match.group(1)) % 12
            end_hour = int(explicit_match.group(2)) % 12
            meridiem = explicit_match.group(3)
            if meridiem == "pm":
                start_hour += 12
                end_hour += 12
            start = captured.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            end = captured.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            evidence.append(_heuristic_evidence(event, part, "actual", "explicit_interval", start.isoformat(), end.isoformat()))
            continue

        compact_interval = re.search(r"(\d{1,2})(?::(\d{2}))? to (\d{1,2})(?::(\d{2}))? (.+)", lowered)
        if compact_interval:
            start_hour = int(compact_interval.group(1))
            start_minute = int(compact_interval.group(2) or 0)
            end_hour = int(compact_interval.group(3))
            end_minute = int(compact_interval.group(4) or 0)
            start_hour, start_minute = _resolve_hour(start_hour, start_minute, captured.hour)
            end_hour, end_minute = _resolve_hour(end_hour, end_minute, captured.hour)
            start = captured.replace(hour=start_hour % 24, minute=start_minute, second=0, microsecond=0)
            end = captured.replace(hour=end_hour % 24, minute=end_minute, second=0, microsecond=0)
            if end <= start and end.hour < 12:
                end = end.replace(hour=end.hour + 12)
            evidence.append(_heuristic_evidence(event, part, "actual", "explicit_interval", start.isoformat(), end.isoformat()))
            continue

        if lowered.startswith("need to ") or " later" in lowered:
            evidence.append(_heuristic_evidence(event, part, "planned", "vague_reflection", None, None))
            continue

        if any(token in lowered for token in ["working on", "still working", "now it", "i was doing", "worked", "woke up", "slept"]):
            evidence.append(_heuristic_evidence(event, part, "actual", "point", None, None))
            continue

    if not evidence:
        evidence.append(_heuristic_evidence(event, text, "unknown", "vague_reflection", None, None))
    return evidence


def extract_time_use_evidence(event: CanonicalJournalEvent, backend=None) -> list[TimeUseEvidence]:
    text = (event.text_body or "").strip()
    if not text:
        return []

    backend = backend or default_backend()
    if backend and getattr(backend, "available", lambda: True)():
        user_prompt = json.dumps(
            {
                "captured_at": event.captured_at,
                "journal_bucket_date": event.journal_bucket_date,
                "event_type": event.event_type,
                "content_type": event.content_type,
                "text_body": event.text_body,
            },
            ensure_ascii=False,
            indent=2,
        )
        response = backend.complete_json(system_prompt=EXTRACT_SYSTEM_PROMPT, user_prompt=user_prompt)
        evidence_payloads = response.get("evidence")
        if not isinstance(evidence_payloads, list):
            raise RuntimeError("LLM extraction response missing evidence list")
        return [_make_evidence(event, payload) for payload in evidence_payloads]

    return _heuristic_extract(event)
