from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import timedelta
from pathlib import Path

from events_agents.common.time import resolve_week_start, week_dates
from events_agents.index.sqlite_store import SQLiteStore
from events_agents.time_use.aggregate import build_daily_rollup, build_weekly_rollup
from events_agents.time_use.ask import answer_question
from events_agents.time_use.extract import extract_time_use_evidence
from events_agents.time_use.models import CanonicalJournalEvent
from events_agents.time_use.reconcile import reconcile_day
from events_agents.time_use.relevance import classify_relevance
from events_agents.time_use.report import render_weekly_report, write_weekly_report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="partneros")
    parser.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[2] / "state"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    journal = subparsers.add_parser("journal")
    journal_sub = journal.add_subparsers(dest="journal_command", required=True)
    for name in ["import", "stats"]:
        cmd = journal_sub.add_parser(name)
        cmd.add_argument("--data-dir", required=True)

    time_use = subparsers.add_parser("time-use")
    time_sub = time_use.add_subparsers(dest="time_command", required=True)

    classify = time_sub.add_parser("classify")
    classify.add_argument("--data-dir", required=True)
    classify.add_argument("--since", default="14d")

    extract = time_sub.add_parser("extract")
    extract.add_argument("--data-dir", required=True)
    extract.add_argument("--since", default="14d")

    reconstruct = time_sub.add_parser("reconstruct")
    reconstruct.add_argument("--data-dir", required=True)
    reconstruct.add_argument("--week", required=True)

    report = time_sub.add_parser("report")
    report.add_argument("--data-dir", required=True)
    report.add_argument("--week", required=True)

    ask = time_sub.add_parser("ask")
    ask.add_argument("--data-dir", required=True)
    ask.add_argument("--week", required=True)
    ask.add_argument("question")

    build = time_sub.add_parser("build")
    build.add_argument("--data-dir", required=True)
    build.add_argument("--week", required=True)

    return parser.parse_args(argv)


def row_to_event(row: dict[str, object]) -> CanonicalJournalEvent:
    return CanonicalJournalEvent(
        canonical_event_uid=row["canonical_event_uid"],
        journal_path=row["journal_path"],
        journal_line_no=row["journal_line_no"],
        journal_bucket_date=row["journal_bucket_date"],
        event_id=row["event_id"],
        event_type=row["event_type"],
        schema_name=row["schema_name"],
        schema_version=row["schema_version"],
        captured_at=row["captured_at"],
        committed_at=row["committed_at"],
        source_client=row["source_client"],
        source_transport=row["source_transport"],
        content_type=row["content_type"],
        text_body=row["text_body"],
        raw_event_json=json.loads(row["raw_event_json"]),
    )


def _store(state_dir: str) -> SQLiteStore:
    return SQLiteStore(Path(state_dir) / "time_use.db")


def cmd_journal_import(args: argparse.Namespace) -> int:
    store = _store(args.state_dir)
    result = store.import_journal(Path(args.data_dir))
    store.record_pipeline_run("journal import", result)
    print(json.dumps(result))
    return 0


def cmd_journal_stats(args: argparse.Namespace) -> int:
    store = _store(args.state_dir)
    rows = store.load_journal_events()
    counts = {}
    for row in rows:
        counts[row["event_type"]] = counts.get(row["event_type"], 0) + 1
    print(json.dumps({"event_types": counts, "total": len(rows)}))
    return 0


def cmd_time_use_classify(args: argparse.Namespace) -> int:
    store = _store(args.state_dir)
    store.import_journal(Path(args.data_dir))
    rows = store.load_journal_events()
    for row in rows:
        decision = classify_relevance(row_to_event(row))
        store.save_relevance_decision(decision)
    return 0


def cmd_time_use_extract(args: argparse.Namespace) -> int:
    store = _store(args.state_dir)
    store.import_journal(Path(args.data_dir))
    rows = store.load_journal_events()
    for row in rows:
        event = row_to_event(row)
        decision = classify_relevance(event)
        store.save_relevance_decision(decision)
        if decision.relevant:
            store.save_evidence(extract_time_use_evidence(event))
    return 0


def cmd_time_use_reconstruct(args: argparse.Namespace) -> int:
    store = _store(args.state_dir)
    store.import_journal(Path(args.data_dir))
    rows = store.load_journal_events()
    evidence_by_day = {}
    week_start = resolve_week_start(args.week).isoformat()
    for row in rows:
        event = row_to_event(row)
        decision = classify_relevance(event)
        store.save_relevance_decision(decision)
        if not decision.relevant:
            continue
        evidence = extract_time_use_evidence(event)
        store.save_evidence(evidence)
        for item in evidence:
            if item.observed_day_local:
                evidence_by_day.setdefault(item.observed_day_local, []).append(item)

    all_blocks = []
    daily_rollups = []
    daily_gaps = {}
    for day in week_dates(week_start):
        day_str = day.isoformat()
        blocks, gaps = reconcile_day(day_str, evidence_by_day.get(day_str, []), 30, 60)
        daily_gaps[day_str] = gaps
        all_blocks.extend(blocks)
        daily_rollups.append(build_daily_rollup(day_str, blocks))
    weekly_rollup = build_weekly_rollup(week_start, daily_rollups, daily_gaps)
    store.replace_blocks_for_week(week_start, all_blocks)
    store.replace_daily_rollups(daily_rollups)
    store.replace_weekly_rollup(weekly_rollup, len(all_blocks))
    return 0


def iso_week_slug(week_start: str) -> str:
    year, week_num, _ = Path(week_start).stem, None, None
    from datetime import date
    d = date.fromisoformat(week_start)
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def cmd_time_use_report(args: argparse.Namespace) -> int:
    store = _store(args.state_dir)
    week_start = resolve_week_start(args.week).isoformat()
    blocks = store.fetch_blocks_for_week(week_start)
    weekly_rows = store.fetch_weekly_rollup(week_start)
    category_totals = {row["category"]: row["total_minutes"] for row in weekly_rows}
    unknown_minutes = weekly_rows[0]["unknown_minutes"] if weekly_rows else 7 * 1440
    high_conf = sum(row["high_confidence_minutes"] for row in weekly_rows)
    low_conf = sum(row["low_confidence_minutes"] for row in weekly_rows)
    from events_agents.time_use.models import WeeklyRollup
    rollup = WeeklyRollup(
        week_start=week_start,
        category_totals=category_totals,
        unknown_minutes=unknown_minutes,
        high_confidence_minutes=high_conf,
        low_confidence_minutes=low_conf,
        day_totals={},
        largest_gaps=[],
    )
    citations = []
    for block in blocks[:5]:
        source_ids = json.loads(block["source_evidence_ids"])
        citation_id = source_ids[0] if source_ids else block["block_id"]
        citations.append(store.citation_for_evidence_id(citation_id))
    week_end = (resolve_week_start(args.week) + timedelta(days=6)).isoformat()
    narrative = answer_question("Where did my time go last week?", weekly_rows, blocks)
    content = render_weekly_report(week_start, week_end, rollup, citations, narrative)
    report_path = Path(args.state_dir) / "reports" / "time_use" / "weekly" / f"{iso_week_slug(week_start)}.md"
    write_weekly_report(report_path, content)
    print(str(report_path))
    return 0


def cmd_time_use_ask(args: argparse.Namespace) -> int:
    store = _store(args.state_dir)
    week_start = resolve_week_start(args.week).isoformat()
    print(answer_question(args.question, store.fetch_weekly_rollup(week_start), store.fetch_blocks_for_week(week_start)))
    return 0


def cmd_time_use_build(args: argparse.Namespace) -> int:
    cmd_time_use_classify(args)
    cmd_time_use_extract(args)
    reconstruct_args = argparse.Namespace(**vars(args))
    cmd_time_use_reconstruct(reconstruct_args)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or [])
    if args.command == "journal" and args.journal_command == "import":
        return cmd_journal_import(args)
    if args.command == "journal" and args.journal_command == "stats":
        return cmd_journal_stats(args)
    if args.command == "time-use" and args.time_command == "classify":
        return cmd_time_use_classify(args)
    if args.command == "time-use" and args.time_command == "extract":
        return cmd_time_use_extract(args)
    if args.command == "time-use" and args.time_command == "reconstruct":
        return cmd_time_use_reconstruct(args)
    if args.command == "time-use" and args.time_command == "report":
        return cmd_time_use_report(args)
    if args.command == "time-use" and args.time_command == "ask":
        return cmd_time_use_ask(args)
    if args.command == "time-use" and args.time_command == "build":
        return cmd_time_use_build(args)
    raise SystemExit(2)


def entrypoint() -> int:
    import sys
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(entrypoint())
