from __future__ import annotations

import uuid
from datetime import timedelta

from events_agents.common.time import end_of_day, parse_iso_datetime, start_of_day
from events_agents.time_use.models import TimeUseBlock, TimeUseEvidence


def reconcile_day(day_local: str, evidence: list[TimeUseEvidence], merge_threshold_minutes: int, bridge_threshold_minutes: int):
    eligible = [item for item in evidence if item.observed_start_at and item.observed_end_at and item.actuality != "planned" and item.observed_day_local == day_local]
    eligible.sort(key=lambda item: item.observed_start_at)

    blocks: list[TimeUseBlock] = []
    for item in eligible:
        blocks.append(
            TimeUseBlock(
                block_id=str(uuid.uuid4()),
                day_local=day_local,
                start_at=item.observed_start_at or item.anchor_time_at,
                end_at=item.observed_end_at or item.anchor_time_at,
                category=item.category,
                label=item.activity_text,
                confidence=item.confidence,
                source_evidence_ids=[item.evidence_id],
                derivation_type="direct",
            )
        )

    gaps = []
    cursor = start_of_day(day_local)
    for block in blocks:
        start = parse_iso_datetime(block.start_at)
        if start > cursor:
            gaps.append({"start_at": cursor.isoformat(), "end_at": start.isoformat(), "minutes": int((start - cursor).total_seconds() // 60)})
        cursor = max(cursor, parse_iso_datetime(block.end_at))
    day_end = end_of_day(day_local)
    if cursor < day_end:
        gaps.append({"start_at": cursor.isoformat(), "end_at": day_end.isoformat(), "minutes": int((day_end - cursor).total_seconds() // 60)})
    return blocks, gaps
