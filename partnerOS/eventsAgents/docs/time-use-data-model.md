# Time-Use Data Model

This document explains the main objects used by the current implementation.

## 1. `CanonicalJournalEvent`

Defined in:
- `src/events_agents/time_use/models.py`

Purpose:
- normalized in-memory representation of one NDJSON journal line

Important fields:
- `canonical_event_uid`
- `journal_path`
- `journal_line_no`
- `journal_bucket_date`
- `event_id`
- `event_type`
- `captured_at`
- `committed_at`
- `content_type`
- `text_body`
- `raw_event_json`

Notes:
- If the source event has `event_id`, that becomes the canonical UID.
- Otherwise a deterministic hash can be used.
- This model is generic enough for future event types even though the current time-use pipeline only uses `note.capture`.

## 2. `PurposeRelevanceDecision`

Purpose:
- durable record of whether a journal event matters to the `time_use` analyst

Important fields:
- `decision_id`
- `purpose_id`
- `canonical_event_uid`
- `eligible`
- `relevant`
- `confidence`
- `reason`
- `decided_by`
- `classifier_version`

Current behavior:
- produced by `time_use/relevance.py`
- persisted in the `purpose_relevance` table

## 3. `TimeUseEvidence`

Purpose:
- structured activity evidence extracted from one relevant note

Important fields in the current implementation:
- `evidence_id`
- `canonical_event_uid`
- `source_event_type`
- `actuality`
- `observed_day_local`
- `observed_start_at`
- `observed_end_at`
- `anchor_time_at`
- `temporal_mode`
- `activity_text`
- `category`
- `subcategory`
- `confidence`
- `supporting_snippet`
- `derivation_notes`

Current `actuality` values seen:
- `actual`
- `retrospective_actual`
- `planned`
- `unknown`

Current `temporal_mode` values seen:
- `explicit_interval`
- `relative_interval`
- `point`
- `vague_reflection`

## 4. `TimeUseBlock`

Purpose:
- a reconciled timeline block for a day

Important fields:
- `block_id`
- `day_local`
- `start_at`
- `end_at`
- `category`
- `label`
- `confidence`
- `source_evidence_ids`
- `derivation_type`

Current behavior:
- only interval-like actual evidence becomes blocks
- derivation type is currently always `direct`

## 5. `DailyRollup`

Purpose:
- per-day summary built from blocks

Important fields:
- `day_local`
- `category_totals`
- `unknown_minutes`
- `number_of_blocks`
- `low_confidence_blocks`
- `citations`

## 6. `WeeklyRollup`

Purpose:
- week-level summary built from seven daily rollups

Important fields:
- `week_start`
- `category_totals`
- `unknown_minutes`
- `high_confidence_minutes`
- `low_confidence_minutes`
- `day_totals`
- `largest_gaps`

## SQLite tables

Defined in:
- `src/events_agents/index/schema.sql`

### `journal_events`
Normalized imported canonical events.

### `journal_events_fts`
Full-text search table for note text.

### `purpose_relevance`
Stored relevance decisions for the `time_use` purpose.

### `time_use_evidence`
Extracted structured evidence.

### `time_use_blocks`
Reconstructed timeline blocks for a week.

### `time_use_daily_rollups`
Per-day aggregated totals by category.

### `time_use_weekly_rollups`
Per-week aggregated totals by category.

### `pipeline_runs`
Basic run ledger for command executions.

## Provenance chain

The intended provenance chain is:

```txt
journal line
  -> CanonicalJournalEvent
  -> PurposeRelevanceDecision
  -> TimeUseEvidence
  -> TimeUseBlock
  -> DailyRollup / WeeklyRollup
  -> Report citation / ask answer
```

That chain is the backbone of the package.

## Important honesty rule

Not every relevant note must become a precise timeline block.

Examples:
- a broad summary can still be useful evidence
- a vague reflection can still matter to narrative
- planned activity should not be counted as actual time use
- absent evidence should remain unknown
