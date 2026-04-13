from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from events_agents.adapters.journal_fs import iter_canonical_journal_events
from events_agents.time_use.models import DailyRollup, PurposeRelevanceDecision, TimeUseBlock, TimeUseEvidence, WeeklyRollup


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        schema_path = Path(__file__).with_name("schema.sql")
        with self._connect() as conn:
            conn.executescript(schema_path.read_text(encoding="utf-8"))

    def import_journal(self, data_dir: Path) -> dict[str, int]:
        imported = 0
        with self._connect() as conn:
            for event in iter_canonical_journal_events(data_dir):
                cursor = conn.execute(
                    """
                    insert or ignore into journal_events (
                      canonical_event_uid, journal_path, journal_line_no, journal_bucket_date, event_id,
                      event_type, schema_name, schema_version, captured_at, committed_at,
                      source_client, source_transport, content_type, text_body, raw_event_json
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.canonical_event_uid, event.journal_path, event.journal_line_no, event.journal_bucket_date,
                        event.event_id, event.event_type, event.schema_name, event.schema_version, event.captured_at,
                        event.committed_at, event.source_client, event.source_transport, event.content_type,
                        event.text_body, json.dumps(event.raw_event_json, ensure_ascii=False),
                    ),
                )
                if cursor.rowcount:
                    imported += 1
                    conn.execute(
                        "insert into journal_events_fts (canonical_event_uid, text_body) values (?, ?)",
                        (event.canonical_event_uid, event.text_body or ""),
                    )
            conn.commit()
        return {"imported": imported}

    def load_journal_events(self) -> list[dict[str, object]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute("select * from journal_events order by captured_at")]

    def save_relevance_decision(self, decision: PurposeRelevanceDecision) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert or replace into purpose_relevance (decision_id, purpose_id, canonical_event_uid, eligible, relevant, confidence, reason, decided_by, classifier_version) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    decision.decision_id, decision.purpose_id, decision.canonical_event_uid, int(decision.eligible),
                    int(decision.relevant), decision.confidence, decision.reason, decision.decided_by,
                    decision.classifier_version,
                ),
            )
            conn.commit()

    def save_evidence(self, evidence: list[TimeUseEvidence]) -> None:
        with self._connect() as conn:
            for item in evidence:
                conn.execute(
                    "insert or replace into time_use_evidence (evidence_id, canonical_event_uid, source_event_type, actuality, observed_day_local, observed_start_at, observed_end_at, anchor_time_at, temporal_mode, activity_text, category, subcategory, confidence, supporting_snippet, derivation_notes) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        item.evidence_id, item.canonical_event_uid, item.source_event_type, item.actuality,
                        item.observed_day_local, item.observed_start_at, item.observed_end_at, item.anchor_time_at,
                        item.temporal_mode, item.activity_text, item.category, item.subcategory, item.confidence,
                        item.supporting_snippet, item.derivation_notes,
                    ),
                )
            conn.commit()

    def replace_blocks_for_week(self, week_start: str, blocks: list[TimeUseBlock]) -> None:
        with self._connect() as conn:
            conn.execute("delete from time_use_blocks where week_start = ?", (week_start,))
            for block in blocks:
                conn.execute(
                    "insert into time_use_blocks (block_id, day_local, start_at, end_at, category, label, confidence, source_evidence_ids, derivation_type, week_start) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        block.block_id, block.day_local, block.start_at, block.end_at, block.category, block.label,
                        block.confidence, json.dumps(block.source_evidence_ids), block.derivation_type, week_start,
                    ),
                )
            conn.commit()

    def replace_daily_rollups(self, rollups: list[DailyRollup]) -> None:
        with self._connect() as conn:
            for rollup in rollups:
                conn.execute("delete from time_use_daily_rollups where day_local = ?", (rollup.day_local,))
                for category, total_minutes in rollup.category_totals.items():
                    conn.execute(
                        "insert into time_use_daily_rollups (day_local, category, total_minutes, high_confidence_minutes, low_confidence_minutes, unknown_minutes, supporting_blocks) values (?, ?, ?, ?, ?, ?, ?)",
                        (rollup.day_local, category, total_minutes, total_minutes, 0, rollup.unknown_minutes, rollup.number_of_blocks),
                    )
            conn.commit()

    def replace_weekly_rollup(self, rollup: WeeklyRollup, supporting_blocks: int) -> None:
        with self._connect() as conn:
            conn.execute("delete from time_use_weekly_rollups where week_start = ?", (rollup.week_start,))
            for category, total_minutes in rollup.category_totals.items():
                conn.execute(
                    "insert into time_use_weekly_rollups (week_start, category, total_minutes, high_confidence_minutes, low_confidence_minutes, unknown_minutes, supporting_blocks) values (?, ?, ?, ?, ?, ?, ?)",
                    (rollup.week_start, category, total_minutes, total_minutes, 0, rollup.unknown_minutes, supporting_blocks),
                )
            conn.commit()

    def fetch_blocks_for_week(self, week_start: str) -> list[dict[str, object]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute("select * from time_use_blocks where week_start = ? order by start_at", (week_start,))]

    def fetch_weekly_rollup(self, week_start: str) -> list[dict[str, object]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute("select * from time_use_weekly_rollups where week_start = ? order by total_minutes desc", (week_start,))]

    def citation_for_evidence_id(self, evidence_id: str) -> str:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select je.event_id, je.journal_path, je.journal_line_no
                from time_use_evidence tue
                join journal_events je on je.canonical_event_uid = tue.canonical_event_uid
                where tue.evidence_id = ?
                """,
                (evidence_id,),
            ).fetchone()
        if row is None:
            return f"[evidence: {evidence_id}]"
        if row["event_id"]:
            return f"[event: {row['event_id']}]"
        return f"[journal: {row['journal_path']}:L{row['journal_line_no']}]"

    def record_pipeline_run(self, command_name: str, metadata: dict[str, object]) -> None:
        run_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "insert into pipeline_runs (run_id, command_name, started_at, finished_at, status, metadata_json) values (?, ?, datetime('now'), datetime('now'), ?, ?)",
                (run_id, command_name, "ok", json.dumps(metadata, ensure_ascii=False)),
            )
            conn.commit()
