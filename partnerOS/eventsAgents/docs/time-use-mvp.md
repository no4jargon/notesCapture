# Time-Use MVP

This document explains the implemented MVP in product terms.

## Goal

Build a read-only analyst that can answer:

> "Help me understand how I spent my week."

The analyst is intentionally narrow. It is **not** a general-purpose assistant and **not** a write-capable automation system.

## Source of truth

The only canonical analytical input is:

```txt
journal/YYYY/MM/DD.ndjson
```

Inside the live data directory.

The MVP deliberately does **not** use:
- `notes.txt`
- `views/notes.txt`
- `ingress/`
- `rejects/`
- the live data dir `state/`

## Implemented stages

### 1. Journal adapter + index

Implemented in:
- `src/events_agents/adapters/journal_fs.py`
- `src/events_agents/index/sqlite_store.py`
- `src/events_agents/index/schema.sql`

Behavior:
- scans `journal/**/*.ndjson`
- reads one JSON object per line
- normalizes each line into `CanonicalJournalEvent`
- stores raw JSON plus selected normalized fields in SQLite
- builds an FTS table for note text
- import is idempotent

### 2. Routing + relevance

Implemented in:
- `src/events_agents/time_use/routing.py`
- `src/events_agents/time_use/relevance.py`
- `src/events_agents/llm/backend.py`

Behavior:
- only `note.capture` with text/plain or text/markdown is eligible
- relevance is LLM-powered when `OPENAI_API_KEY` is set
- a conservative heuristic fallback remains for offline tests and local development
- plan-only notes are usually excluded
- notes with time-spent or actual activity language are usually included

### 3. Structured extraction

Implemented in:
- `src/events_agents/time_use/extract.py`
- `src/events_agents/llm/backend.py`

Behavior:
- extraction is LLM-powered when `OPENAI_API_KEY` is set
- the model is prompted to emit strict JSON evidence objects
- a conservative heuristic fallback remains for offline tests and local development
- current heuristic coverage supports these patterns best:
  - `spent the last 2 hours ...`
  - `from 2 to 4 PM I was ...`
  - `6:15 to 6:45 worked`
  - obvious plan-only notes like `need to ... later`
  - loose point observations like `still working ...`

### 4. Reconciliation

Implemented in:
- `src/events_agents/time_use/reconcile.py`

Behavior:
- only interval-like actual evidence becomes timeline blocks right now
- blocks are sorted within a day
- explicit gaps are emitted for uncovered time
- large uncovered stretches remain unknown instead of being smoothed over

### 5. Aggregation

Implemented in:
- `src/events_agents/time_use/aggregate.py`

Behavior:
- computes daily category totals from blocks
- computes unknown minutes as uncovered minutes in the day
- computes a weekly rollup by summing daily rollups

### 6. Report generation

Implemented in:
- `src/events_agents/time_use/report.py`

Behavior:
- writes a markdown weekly report under `state/reports/time_use/weekly/`
- includes coverage, category totals, citations, caveats, and narrative

### 7. Ask shell

Implemented in:
- `src/events_agents/time_use/ask.py`

Behavior:
- answers a small set of scoped questions from the derived weekly mart
- does not attempt to reason from the raw journal when a derived answer exists

## Current command surface

Implemented CLI commands:
- `partneros journal import --data-dir <path>`
- `partneros journal stats --data-dir <path>`
- `partneros time-use classify --data-dir <path> --since 14d`
- `partneros time-use extract --data-dir <path> --since 14d`
- `partneros time-use reconstruct --data-dir <path> --week <week>`
- `partneros time-use report --data-dir <path> --week <week>`
- `partneros time-use ask --data-dir <path> --week <week> "..."`
- `partneros time-use build --data-dir <path> --week <week>`

Note: `partneros` is exposed through `pyproject.toml`, but during local development the easiest invocation is still `python -m events_agents.cli` with `PYTHONPATH` set.

## Provenance model

The package preserves provenance in two layers:

1. Imported journal events retain:
- journal path
- line number
- raw JSON
- stable event ID when present

2. Derived claims retain links to prior layers:
- relevance decisions point to `canonical_event_uid`
- evidence points to `canonical_event_uid`
- blocks point to `source_evidence_ids`
- reports cite event IDs where possible

## Current limitations

This is important: the current implementation is honest but incomplete.

### Known limitations
- No robust resolution for `yesterday`, `last night`, `this morning`
- No sophisticated merging of adjacent evidence
- No explicit confidence breakdown in weekly report beyond stored totals
- No daily markdown report yet
- No evaluation script yet
- No LLM-backed ambiguity handling yet
- No future-source adapters yet

### Why that is acceptable for now

The MVP preserves the most important invariant:

> uncertain time remains unknown instead of being invented.

That is the right tradeoff for sparse note reconstruction.
