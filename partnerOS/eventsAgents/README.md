# eventsAgents

`eventsAgents` is a separate, read-only analysis layer for `partnerOS`.

Its job in this MVP is narrow:

> Read canonical journal events from `eventsCapture`, derive a cautious time-use mart from manual `note.capture` events, and answer: **"How did I spend my week?"**

In the current implementation, the two semantic steps are LLM-enabled:
- relevance classification
- evidence extraction

When `OPENAI_API_KEY` is set, those functions call the OpenAI API.
When it is not set, the code falls back to conservative heuristics so tests and offline local development still work.

## What this package does

For the current sprint, the package can:
- import canonical events from `journal/**/*.ndjson`
- index them into local SQLite state under `partnerOS/eventsAgents/state/`
- classify which `note.capture` events are relevant to time-use analysis
- extract structured `TimeUseEvidence` from relevant notes
- reconstruct conservative daily timeline blocks from interval-like evidence
- compute daily and weekly rollups
- generate a weekly markdown report with citations
- answer a few scoped read-only questions from the derived mart

## What this package explicitly does **not** do

- It does **not** modify `partnerOS/eventsCapture/`
- It does **not** treat `notes.txt` or `views/notes.txt` as machine input
- It does **not** read analytical truth from `ingress/`, `rejects/`, or `state/` in the live data dir
- It does **not** write back into the Dropbox-backed live data directory
- It does **not** act autonomously
- It does **not** try to fabricate a complete week from sparse notes

## Canonical input

The only analytical source of truth is:

```txt
<data-dir>/journal/YYYY/MM/DD.ndjson
```

Everything else in `eventsAgents` is derived local state.

## Current package layout

```txt
partnerOS/eventsAgents/
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── docs/
│   ├── code-tour.md
│   ├── current-journal-contract.md
│   ├── time-use-data-model.md
│   └── time-use-mvp.md
├── src/events_agents/
│   ├── cli.py
│   ├── adapters/
│   │   └── journal_fs.py
│   ├── ask/
│   ├── common/
│   │   ├── ids.py
│   │   └── time.py
│   ├── index/
│   │   ├── schema.sql
│   │   ├── search.py
│   │   └── sqlite_store.py
│   ├── llm/
│   │   └── backend.py
│   ├── reports/
│   └── time_use/
│       ├── aggregate.py
│       ├── ask.py
│       ├── extract.py
│       ├── models.py
│       ├── purpose_profile.yaml
│       ├── reconcile.py
│       ├── relevance.py
│       ├── report.py
│       ├── routing.py
│       └── taxonomy.yaml
├── tests/
└── state/
```

## Local environment setup

The repository root contains:
- `.env.local` for local-only secrets
- `.envrc` to export them into the shell

Expected variables:

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
```

If you use `direnv`, run this once from the repo root:

```bash
direnv allow
```

If you do not use `direnv`, load the variables manually:

```bash
source .envrc
```

This makes `OPENAI_API_KEY` available to the time-use CLI anywhere in the repository.

## Quick start

### 1. Import journal events

```bash
PYTHONPATH=partnerOS/eventsAgents/src \
python3 -m events_agents.cli \
  --state-dir partnerOS/eventsAgents/state \
  journal import \
  --data-dir /path/to/data
```

### 2. Inspect basic journal stats

```bash
PYTHONPATH=partnerOS/eventsAgents/src \
python3 -m events_agents.cli \
  --state-dir partnerOS/eventsAgents/state \
  journal stats \
  --data-dir /path/to/data
```

### 3. Build the time-use mart for a week

```bash
PYTHONPATH=partnerOS/eventsAgents/src \
python3 -m events_agents.cli \
  --state-dir partnerOS/eventsAgents/state \
  time-use build \
  --data-dir /path/to/data \
  --week 2026-03-23
```

### 4. Write a weekly markdown report

```bash
PYTHONPATH=partnerOS/eventsAgents/src \
python3 -m events_agents.cli \
  --state-dir partnerOS/eventsAgents/state \
  time-use report \
  --data-dir /path/to/data \
  --week 2026-03-23
```

### 5. Ask a scoped question

```bash
PYTHONPATH=partnerOS/eventsAgents/src \
python3 -m events_agents.cli \
  --state-dir partnerOS/eventsAgents/state \
  time-use ask \
  --data-dir /path/to/data \
  --week 2026-03-23 \
  "Where did my time go last week?"
```

## `--week` behavior

Supported now:
- `--week last-complete`
- `--week YYYY-MM-DD` where the date is the Monday starting the target week

`last-complete` is resolved in `Asia/Kolkata`.

Important practical note: if the most recent completed Monday–Sunday week has no journal coverage, the generated report will honestly show all time as unknown.

## State and outputs

All derived local state is kept under:

```txt
partnerOS/eventsAgents/state/
```

Important files:
- SQLite DB: `partnerOS/eventsAgents/state/time_use.db`
- Weekly reports: `partnerOS/eventsAgents/state/reports/time_use/weekly/`

This directory is gitignored.

## Core pipeline

The current execution path is:

```txt
journal/**/*.ndjson
  -> adapters/journal_fs.py
  -> index/sqlite_store.py
  -> time_use/relevance.py
  -> time_use/extract.py
  -> time_use/reconcile.py
  -> time_use/aggregate.py
  -> time_use/report.py / time_use/ask.py
```

## Current implementation quality level

This is an MVP. It is useful, but intentionally conservative and still incomplete.

### What is reasonably solid
- journal import
- idempotent indexing by canonical event UID
- provenance back to event ID or journal path/line
- simple relevance filtering
- extraction for a few common patterns
- explicit unknown time via uncovered day gaps

### What is still rough
- relevance is heuristic-only right now
- extraction only covers a subset of note patterns
- relative-day resolution like `yesterday`, `last night`, `this morning` is still limited
- reconciliation only turns interval-like evidence into blocks; point summaries are not richly merged yet
- report generation is honest but still thin
- ask mode is intentionally narrow and retrieval-lite

## Read this next

If you want to understand the code in detail, start with:
- `docs/code-tour.md`
- `docs/time-use-mvp.md`
- `docs/time-use-data-model.md`
- `docs/current-journal-contract.md`
