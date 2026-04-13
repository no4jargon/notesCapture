# Code Tour

This is a guided tour of the code currently written in `eventsAgents`.

If you want to understand the system quickly, read files in this order:

1. `src/events_agents/cli.py`
2. `src/events_agents/adapters/journal_fs.py`
3. `src/events_agents/index/sqlite_store.py`
4. `src/events_agents/time_use/models.py`
5. `src/events_agents/time_use/routing.py`
6. `src/events_agents/time_use/relevance.py`
7. `src/events_agents/time_use/extract.py`
8. `src/events_agents/time_use/reconcile.py`
9. `src/events_agents/time_use/aggregate.py`
10. `src/events_agents/time_use/report.py`
11. `src/events_agents/llm/backend.py`
12. `src/events_agents/time_use/ask.py`
13. `src/events_agents/common/time.py`
14. `src/events_agents/index/schema.sql`

---

## 1. `src/events_agents/cli.py`

This is the orchestration layer.

### What it does
- defines CLI commands
- creates a `SQLiteStore`
- imports journal events when needed
- runs classification, extraction, reconstruction, report generation, and ask flows

### Important functions

#### `parse_args(argv)`
Builds the full CLI tree.

Top-level groups:
- `journal`
- `time-use`

Time-use subcommands:
- `classify`
- `extract`
- `reconstruct`
- `report`
- `ask`
- `build`

#### `row_to_event(row)`
Converts a SQLite row back into an in-memory `CanonicalJournalEvent`.

This is a small but important seam because the pipeline stores normalized events in SQLite, then later reconstructs Python model objects from those rows.

#### `cmd_journal_import(args)`
Calls `store.import_journal(...)` and records a pipeline run.

#### `cmd_time_use_classify(args)`
Imports journal events if needed, loads all journal rows, converts each row to `CanonicalJournalEvent`, then stores a `PurposeRelevanceDecision`.

#### `cmd_time_use_extract(args)`
Runs classification again and, for relevant events only, stores extracted `TimeUseEvidence`.

#### `cmd_time_use_reconstruct(args)`
This is the most important command in the current pipeline.

It:
1. imports journal events
2. classifies relevance
3. extracts evidence from relevant notes
4. groups evidence by observed day
5. reconciles evidence into blocks for each day of the week
6. builds daily rollups
7. builds the weekly rollup
8. writes derived block and rollup tables back to SQLite

#### `cmd_time_use_report(args)`
Loads the derived weekly mart and writes a markdown report.

#### `cmd_time_use_ask(args)`
Answers a scoped question from the derived weekly mart.

#### `cmd_time_use_build(args)`
Convenience pipeline. Right now it simply chains:
- classify
- extract
- reconstruct

### Design note

`cli.py` currently owns a fair amount of orchestration logic. That is acceptable for the MVP, but if the package grows, this file will likely be refactored into a service layer.

---

## 2. `src/events_agents/adapters/journal_fs.py`

This file is the file-system adapter for the canonical journal.

### What it does
- walks `journal/**/*.ndjson`
- reads one line at a time
- parses JSON
- emits normalized `CanonicalJournalEvent` objects

### Important behavior
- preserves `journal_path` and `journal_line_no`
- derives `journal_bucket_date` from the file path
- extracts note text from `content.text`
- preserves the full raw event JSON
- uses `event_id` as canonical UID when present

### Why this matters

This is the boundary where append-only capture truth becomes normalized internal data.
Everything downstream depends on this adapter being stable and conservative.

---

## 3. `src/events_agents/index/sqlite_store.py`

This file is the persistence layer.

### What it does
- initializes the SQLite schema
- imports journal events into `journal_events`
- inserts FTS note text into `journal_events_fts`
- stores relevance decisions, evidence, blocks, and rollups
- fetches weekly blocks and rollups for reporting/ask
- resolves citations back to source event IDs or journal references

### Important methods

#### `import_journal(data_dir)`
Runs the adapter and inserts imported events into `journal_events` using `insert or ignore`.

This makes import idempotent.

#### `load_journal_events()`
Returns normalized journal rows ordered by `captured_at`.

#### `save_relevance_decision(...)`
Stores one `PurposeRelevanceDecision`.

#### `save_evidence(...)`
Stores one or more `TimeUseEvidence` rows.

#### `replace_blocks_for_week(...)`
Deletes existing blocks for a week and inserts the newly reconstructed set.

#### `replace_daily_rollups(...)`
Replaces daily rollup rows for each day.

#### `replace_weekly_rollup(...)`
Replaces the weekly rollup rows for a week.

#### `citation_for_evidence_id(...)`
Joins `time_use_evidence` back to `journal_events` and returns the preferred citation form:
- `[event: ...]` if `event_id` exists
- otherwise `[journal: path:Lline]`

### Design note

The store is intentionally thin. It does not perform the analysis itself; it just persists and retrieves the outputs of the analysis stages.

---

## 4. `src/events_agents/time_use/models.py`

This file defines the core in-memory dataclasses.

### Why it matters

The dataclasses make the pipeline readable by naming the intermediate artifacts explicitly:
- canonical journal event
- relevance decision
- extracted evidence
- reconciled block
- daily rollup
- weekly rollup

Without these models, the code would collapse into untyped dictionaries and lose clarity fast.

---

## 5. `src/events_agents/time_use/routing.py`

This file implements the first filter: eligibility.

### Current rule
An event is eligible for time-use analysis if:
- `event_type == "note.capture"`
- `content_type` is `text/plain` or `text/markdown`

### Why separate this from relevance?

Because future event layers may be noisy.
A future system might ingest many event types, but only some are even candidates for time-use analysis.

That makes this split useful:
- routing/eligibility: can this kind of event matter?
- relevance: does this specific event matter right now?

---

## 6. `src/events_agents/time_use/relevance.py`

This file classifies eligible events as relevant or not relevant.

### Current strategy
Heuristic-only.

### Signals used
- actual-time hints such as `spent`, `worked`, `woke up`, `slept`, `meeting`
- plan-only hints such as `need to`, `should`, `todo`
- presence of digits as a rough proxy for time expressions

### Output
A `PurposeRelevanceDecision` with:
- `eligible`
- `relevant`
- `confidence`
- `reason`
- classifier metadata

### Why this matters

This keeps irrelevant notes out of the more expensive extraction and reconstruction stages.

### Current limitation

The relevance logic is intentionally simple and will misclassify edge cases. It is acceptable as an MVP seam, not a finished classifier.

---

## 7. `src/events_agents/time_use/extract.py`

This file is the heart of the current MVP.

### What it does
Given a relevant note, it tries to turn freeform text into one or more `TimeUseEvidence` objects.

### Internal helpers

#### `_category_for(text)`
Maps activity wording to one of the top-level taxonomy buckets.

This is deliberately lightweight. The purpose is not ontology elegance; it is to answer weekly time-use questions.

#### `_confidence_for(mode, actuality)`
Assigns a simple confidence label.

#### `_make_evidence(...)`
Builds a `TimeUseEvidence` record with provenance fields populated.

#### `_resolve_hour(...)`
A small heuristic for compact intervals like `6:15 to 6:45 worked` when AM/PM is omitted.

### Patterns currently handled well
- `spent the last 2 hours debugging auth`
- `from 2 to 4 PM I was at the dentist`
- `6:15 to 6:45 worked`
- obvious future-plan notes
- some point-in-time actual observations

### Important design rule

This module tries to extract only what it can justify.
If it cannot confidently recover an interval, it should not invent one.

### Current limitations
- relative-day expressions are not deeply resolved
- sentence splitting is naive
- many real-world note phrasings are still unsupported
- evidence IDs are currently random UUIDs rather than deterministic derivations

---

## 8. `src/events_agents/time_use/reconcile.py`

This file turns extracted evidence into timeline blocks and gaps for a day.

### Current behavior
- keeps only interval-like, non-planned evidence for the target day
- sorts by `observed_start_at`
- converts each into a direct `TimeUseBlock`
- emits explicit day gaps before, between, and after blocks

### Why this matters

This is the point where the system chooses honesty over smoothness.
It preserves unknown time instead of compressing the day into a fake continuous schedule.

### Current limitation

The merge/bridge thresholds are passed in but not richly used yet. The current reconciler is intentionally conservative and simple.

---

## 9. `src/events_agents/time_use/aggregate.py`

This file rolls blocks up into daily and weekly summaries.

### `block_minutes(block)`
Computes duration in minutes from `start_at` and `end_at`.

### `build_daily_rollup(day_local, blocks)`
Sums minutes by category and computes unknown minutes as:

```txt
1440 - known_block_minutes
```

### `build_weekly_rollup(...)`
Adds up category totals across seven days and carries forward the largest day gaps.

### Design note

The arithmetic is intentionally done in code, not delegated to any model.
That aligns with the system requirement that time arithmetic be software, not improvisation.

---

## 10. `src/events_agents/time_use/report.py`

This file renders markdown output.

### What it does
- formats durations like `3h 15m`
- maps category IDs to display labels
- renders sections for coverage, totals, gaps, evidence, caveats, and narrative
- writes the markdown file to disk

### Current limitation

The report currently uses only a small evidence sample and a thin weekly narrative. It is structurally useful but not yet richly analytical.

---

## 11. `src/events_agents/llm/backend.py`

This file is the OpenAI integration seam.

### What it does
- reads `OPENAI_API_KEY` and `OPENAI_MODEL` from the environment
- sends chat-completions requests with JSON-only output requirements
- loads prompt text from `src/events_agents/llm/prompts/`

### Important functions

#### `OpenAIChatBackend.complete_json(...)`
Sends a request to the OpenAI API and parses the model response as JSON.

#### `load_prompt(...)`
Loads prompt text from disk so the classification and extraction modules can keep prompt content separate from Python logic.

#### `default_backend()`
Returns the default OpenAI backend instance.

### Design note

This is intentionally a thin wrapper. The goal is not to hide the API behind a giant abstraction layer, only to isolate request/response handling and prompt loading.

---

## 12. `src/events_agents/time_use/ask.py`

This file implements the thin read-only analyst shell.

### Current behavior
It pattern-matches a few scoped question types and answers from weekly rollup rows and block rows.

Examples:
- `Where did my time go last week?`
- deep-work-total style questions
- unknown-gap prompts

### Important note

This is intentionally not a general assistant. It is a narrow interface over the time-use mart.

---

## 13. `src/events_agents/common/time.py`

This file holds shared time utilities.

### Important helpers
- `parse_iso_datetime(...)`
- `start_of_day(...)`
- `end_of_day(...)`
- `last_complete_week_start(...)`
- `resolve_week_start(...)`
- `week_dates(...)`
- `format_minutes(...)`

### Why this matters

Week boundaries and duration formatting appear in multiple stages. Centralizing them avoids duplicated date logic.

---

## 14. `src/events_agents/index/schema.sql`

This file defines the SQLite schema.

### Read it when you want to understand:
- what data is persisted
- how provenance is retained
- what the reporting and ask layers are reading from

It is the clearest snapshot of the current mart shape.

---

## End-to-end data flow

Here is the current end-to-end flow in one picture:

```txt
journal/**/*.ndjson
  -> iter_canonical_journal_events()
  -> journal_events
  -> classify_relevance()
  -> purpose_relevance
  -> extract_time_use_evidence()
  -> time_use_evidence
  -> reconcile_day()
  -> time_use_blocks + gaps
  -> build_daily_rollup()
  -> time_use_daily_rollups
  -> build_weekly_rollup()
  -> time_use_weekly_rollups
  -> render_weekly_report() / answer_question()
```

## Tests as a second code tour

The tests are also a good map:
- `tests/test_journal_adapter.py`
- `tests/test_relevance.py`
- `tests/test_extract.py`
- `tests/test_extract_more_intervals.py`
- `tests/test_extract_interval_ordering.py`
- `tests/test_reconcile.py`
- `tests/test_aggregate.py`
- `tests/test_end_to_end.py`

They show the intended behavior of each stage in small, focused examples.

## Honest summary

The code currently written is a real working skeleton, not a finished analyst.

Its strongest qualities are:
- clean separation from `eventsCapture`
- canonical-journal-only input
- provenance retention
- explicit unknown time
- a simple but test-covered pipeline

Its weakest areas right now are:
- real-world language extraction coverage
- relative day resolution
- sophisticated reconciliation
- report depth
- ask-shell richness

That is acceptable for an MVP as long as the system remains honest about uncertainty.
