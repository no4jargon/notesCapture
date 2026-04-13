from __future__ import annotations

from pathlib import Path

from events_agents.common.time import format_minutes
from events_agents.time_use.models import WeeklyRollup


CATEGORY_LABELS = {
    "deep_work": "Deep work",
    "meetings": "Meetings",
    "communication": "Communication",
    "admin": "Admin",
    "planning": "Planning",
    "exercise": "Exercise",
    "meals": "Meals",
    "chores": "Chores",
    "transit": "Transit",
    "social": "Social",
    "leisure": "Leisure",
    "sleep": "Sleep",
    "errands": "Errands",
    "unknown": "Unknown",
}


def render_weekly_report(week_start: str, week_end: str, rollup: WeeklyRollup, citations: list[str], narrative: str) -> str:
    lines = [f"# Time Use Report — Week of {week_start} to {week_end}", "", "## Coverage"]
    observed = sum(rollup.category_totals.values())
    lines.extend([
        f"- Observed / inferred time: {format_minutes(observed)}",
        f"- Unknown time: {format_minutes(rollup.unknown_minutes)}",
        f"- High-confidence time: {format_minutes(rollup.high_confidence_minutes)}",
        f"- Low-confidence time: {format_minutes(rollup.low_confidence_minutes)}",
        "",
        "## Category totals",
    ])
    for category, minutes in sorted(rollup.category_totals.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- {CATEGORY_LABELS.get(category, category.title())}: {format_minutes(minutes)}")
    lines.extend(["", "## Largest gaps"])
    for gap in rollup.largest_gaps[:5]:
        lines.append(f"- {gap['start_at']}–{gap['end_at']} ({format_minutes(int(gap['minutes']))})")
    lines.extend(["", "## Evidence highlights"])
    for citation in citations[:5]:
        lines.append(f"- {citation}")
    lines.extend(["", "## Caveats", "This reconstruction is based on sparse manual note.capture events taken at uneven times.", "Unknown time has been preserved where the evidence is weak.", "", "## Narrative", narrative])
    return "\n".join(lines) + "\n"


def write_weekly_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
