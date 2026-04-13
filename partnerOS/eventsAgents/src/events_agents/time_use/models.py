from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CanonicalJournalEvent:
    canonical_event_uid: str
    journal_path: str
    journal_line_no: int
    journal_bucket_date: str
    event_id: str | None
    event_type: str
    schema_name: str | None
    schema_version: str | None
    captured_at: str
    committed_at: str | None
    source_client: str | None
    source_transport: str | None
    content_type: str | None
    text_body: str | None
    raw_event_json: dict[str, Any]


@dataclass
class PurposeRelevanceDecision:
    decision_id: str
    purpose_id: str
    canonical_event_uid: str
    eligible: bool
    relevant: bool
    confidence: float
    reason: str
    decided_by: str
    classifier_version: str


@dataclass
class TimeUseEvidence:
    evidence_id: str
    canonical_event_uid: str
    source_event_type: str
    actuality: str
    observed_day_local: str | None
    observed_start_at: str | None
    observed_end_at: str | None
    anchor_time_at: str
    temporal_mode: str
    activity_text: str
    category: str
    subcategory: str | None
    confidence: str
    supporting_snippet: str
    derivation_notes: str


@dataclass
class TimeUseBlock:
    block_id: str
    day_local: str
    start_at: str
    end_at: str
    category: str
    label: str
    confidence: str
    source_evidence_ids: list[str]
    derivation_type: str


@dataclass
class DailyRollup:
    day_local: str
    category_totals: dict[str, int]
    unknown_minutes: int
    number_of_blocks: int
    low_confidence_blocks: int
    citations: list[str] = field(default_factory=list)


@dataclass
class WeeklyRollup:
    week_start: str
    category_totals: dict[str, int]
    unknown_minutes: int
    high_confidence_minutes: int
    low_confidence_minutes: int
    day_totals: dict[str, dict[str, int]]
    largest_gaps: list[dict[str, str | int]]
