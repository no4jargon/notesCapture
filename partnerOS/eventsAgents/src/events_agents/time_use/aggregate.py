from __future__ import annotations

from events_agents.common.time import parse_iso_datetime
from events_agents.time_use.models import DailyRollup, TimeUseBlock, WeeklyRollup


def block_minutes(block: TimeUseBlock) -> int:
    return int((parse_iso_datetime(block.end_at) - parse_iso_datetime(block.start_at)).total_seconds() // 60)


def build_daily_rollup(day_local: str, blocks: list[TimeUseBlock]) -> DailyRollup:
    totals: dict[str, int] = {}
    for block in blocks:
        totals[block.category] = totals.get(block.category, 0) + block_minutes(block)
    known = sum(totals.values())
    return DailyRollup(
        day_local=day_local,
        category_totals=totals,
        unknown_minutes=max(0, 1440 - known),
        number_of_blocks=len(blocks),
        low_confidence_blocks=sum(1 for block in blocks if block.confidence == "low"),
        citations=[source_id for block in blocks for source_id in block.source_evidence_ids[:1]],
    )


def build_weekly_rollup(week_start: str, daily_rollups: list[DailyRollup], daily_gaps: dict[str, list[dict[str, str | int]]]) -> WeeklyRollup:
    totals: dict[str, int] = {}
    high_confidence_minutes = 0
    low_confidence_minutes = 0
    day_totals: dict[str, dict[str, int]] = {}
    largest_gaps = []
    unknown = 0
    for rollup in daily_rollups:
        day_totals[rollup.day_local] = dict(rollup.category_totals)
        for category, minutes in rollup.category_totals.items():
            totals[category] = totals.get(category, 0) + minutes
            high_confidence_minutes += minutes
        unknown += rollup.unknown_minutes
        largest_gaps.extend(daily_gaps.get(rollup.day_local, []))
    largest_gaps.sort(key=lambda gap: int(gap["minutes"]), reverse=True)
    return WeeklyRollup(
        week_start=week_start,
        category_totals=totals,
        unknown_minutes=unknown,
        high_confidence_minutes=high_confidence_minutes,
        low_confidence_minutes=low_confidence_minutes,
        day_totals=day_totals,
        largest_gaps=largest_gaps[:5],
    )
