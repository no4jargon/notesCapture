# notesCapture v2 architecture

## Purpose

This document defines the long-term direction for `notesCapture` as a many-producer, one-journal personal capture system.

The goal is to let many independent producers append events into one durable personal event log without requiring those producers to know:

- where canonical data is stored
- how views are generated
- what sync backend is used
- what other data already exists

This is the core decoupling required for a decade-long system.

---

## Core principles

### 1. Producers are write-only
A producer should only be able to emit a new capture.

Examples:
- Mac quick note popup
- iPhone Shortcut
- Android shortcut / Tasker flow
- web form
- browser extension
- watch app
- camera / home sensor event emitter
- agent-generated observation

A producer should not need read access to prior notes or journal state.

### 2. The journal is canonical
The canonical record is an append-only event journal.

Not canonical:
- `notes.txt`
- inbox drop folders
- per-client temporary files
- search indexes
- agent outputs

Canonical:
- committed journal events

### 3. Views are generated
Human-friendly files like `notes.txt` are derived materializations.

This lets the system change storage internals over time without breaking reading workflows.

### 4. Transports are adapters, not the architecture
Dropbox, local folders, HTTP, email, queues, and device-specific workflows are all transport adapters.

They should not define the producer contract.

### 5. Agents read views or journal, and write new events
Agentic systems should not mutate prior state.
They should read canonical data or read models, then append new events.

---

## Mental model

```text
many producers
    -> ingress adapters
    -> commit / normalize / dedupe
    -> canonical append-only journal
    -> materializers / indexes / agents
    -> generated views
```

---

## Layer model

## Layer A: producers
Producers create a payload and submit it.

They only know:
- the capture schema
- how to append
- how to authenticate if needed

They do not know:
- Dropbox paths
- journal file layout
- `notes.txt`
- existing entries
- materialization rules

## Layer B: ingress adapters
Ingress adapters accept append-only writes from producers.

Examples:
- `ingress/dropbox/`
- `ingress/local/`
- local HTTP API
- remote HTTPS API
- email receiver
- webhook receiver

These are transport-specific staging zones.

## Layer C: committer
The committer is the boundary between raw input and canonical truth.

Its job:
- validate payloads
- normalize timestamps
- attach `received_at`
- assign canonical event IDs if needed
- dedupe or enforce idempotency
- write committed events to the journal
- route malformed input to rejects

This is the most important system boundary.

## Layer D: canonical journal
The journal is append-only and immutable.

Recommended format:
- NDJSON by day or month

Example:

```text
journal/2026/03/13.ndjson
```

Each line is one committed canonical event.

Benefits:
- replayable
- grep-able
- easy to back up
- easy to index later
- independent of sync transport

## Layer E: materializers and indexes
These derive useful outputs from the journal.

Examples:
- `views/notes.txt`
- daily markdown exports
- SQLite search index
- embedding index
- people / relationship memory view
- task extraction view
- camera event summary view

## Layer F: agents
Agents should operate on stable read models, not ad hoc folder conventions.

They may read:
- the journal
- materialized views
- indexes
- extracted entity graphs

If they write back, they should append new events such as:
- `agent.summary`
- `agent.reminder`
- `agent.observation`
- `agent.inference`

---

## Target folder layout

```text
data/
├── ingress/
│   ├── dropbox/
│   ├── local/
│   ├── webhook/
│   └── manual/
├── journal/
│   └── 2026/
│       └── 03/
│           └── 13.ndjson
├── blobs/
│   └── sha256/
├── views/
│   ├── notes.txt
│   ├── daily/
│   └── markdown/
├── indexes/
│   ├── search.sqlite3
│   └── embeddings/
├── state/
│   ├── import-checkpoints/
│   └── dedupe/
└── rejects/
    └── 2026/
```

### Directory responsibilities

- `ingress/`: raw append-only submissions, grouped by transport
- `journal/`: canonical committed events
- `blobs/`: photos, audio, screenshots, attachments, large payloads
- `views/`: human-readable generated outputs
- `indexes/`: search and agent-facing read models
- `state/`: importer checkpoints, lockfiles, dedupe state
- `rejects/`: invalid or unparseable submissions

---

## Event model

The system should evolve from “note files” to “capture events”.

### Two levels of representation

#### 1. Raw ingress envelope
What a producer submits.
This can be simple and transport-friendly.

#### 2. Canonical journal event
What the committer writes into the journal.
This is normalized and stable.

Raw and canonical do not need to be identical.

---

## Minimum canonical event fields

- `schema_version`
- `event_id`
- `kind`
- `producer`
- `captured_at`
- `received_at`
- `content`
- `metadata`

Recommended additional fields:
- `client_event_id`
- `ingress`
- `blobs`
- `parents`
- `tags`

---

## Recommended canonical event example

```json
{
  "schema_version": 1,
  "event_id": "01JPNX8E5A1Y5YDZ3A4R5S6T7U",
  "kind": "note.capture",
  "captured_at": "2026-03-13T17:24:25+05:30",
  "received_at": "2026-03-13T17:24:28+05:30",
  "producer": {
    "type": "ios-shortcut",
    "id": "anuj-iphone",
    "version": "1.0"
  },
  "client_event_id": "2026-03-13_17-24-25-iphone",
  "ingress": {
    "transport": "dropbox-file-drop",
    "path": "ingress/dropbox/ios/2026-03-13_17-24-25-iphone.json"
  },
  "content": {
    "mime_type": "text/plain",
    "text": "Quick note from iPhone"
  },
  "metadata": {
    "tags": [],
    "timezone": "Asia/Kolkata"
  },
  "blobs": [],
  "parents": []
}
```

---

## Event kinds

The architecture should not be limited to text notes.

Initial event kinds:
- `note.capture`
- `note.imported`
- `link.capture`
- `image.capture`
- `audio.capture`
- `sensor.event`
- `agent.observation`
- `agent.summary`
- `agent.reminder`
- `task.inferred`

`notes.txt` should mostly materialize from `note.capture` and selected note-like event kinds.

---

## Producer contract

A producer must be able to do exactly one thing reliably:
append a new capture event request.

### Preferred long-term API

```http
POST /v1/events
Authorization: Bearer <token>
Content-Type: application/json
```

Body:

```json
{
  "schema_version": 1,
  "kind": "note.capture",
  "captured_at": "2026-03-13T17:24:25+05:30",
  "client_event_id": "iphone-2026-03-13_17-24-25",
  "content": {
    "mime_type": "text/plain",
    "text": "Quick note from iPhone"
  },
  "metadata": {
    "tags": []
  }
}
```

### Transitional file-drop contract

Until a real API exists, file-drop producers should write one raw payload file into a transport-specific ingress folder.

Example:

```text
ingress/dropbox/ios/
```

The payload should be JSON if possible.
Plain text is allowed only as a legacy transitional mode.

---

## Idempotency and dedupe

This matters once devices retry or sync is flaky.

Every producer should eventually send:
- `producer.id`
- `client_event_id`

The committer should use those to prevent duplicate committed events.

Canonical `event_id` should be assigned by the committer or deterministically derived.

---

## Time model

Preserve both:
- `captured_at`: when the producer created the event
- `received_at`: when the committer accepted it

This is required for:
- offline devices
- delayed sync
- backfills
- sensors with buffering
- future analytics

---

## Security model

### Producers
- ideally write-only
- scoped tokens or write-only transport paths
- no direct read access to journal or views

### Committer
- privileged access to journal, rejects, and state

### Readers / agents
- read access to journal and derived read models
- write only through append APIs if they emit new events

---

## Materialization model

`notes.txt` remains valuable, but only as a view.

The materializer should:
- read the journal
- select note-like event kinds
- sort by `captured_at`
- render a stable human-readable timeline

Other future materializers may generate:
- daily review files
- conversation memory views
- people summaries
- location timelines
- event dashboards

---

## Migration from current architecture

Current system:
- Mac helper writes plain text capture files into `ingress/local/`
- phone writes plain text capture files into `ingress/dropbox/`
- importer converts ingress files into entries
- `notes.txt` is generated from `entries/`

Target system:
- all producers write raw capture requests into `ingress/`
- committer writes canonical events into `journal/`
- materializers build `views/notes.txt`

### Migration phases

#### Phase 1: formalize the contracts
- add a documented `capture-event-v1` schema
- document `ingress/` as the current producer boundary
- document `entries/` as current canonical storage, not final target

#### Phase 2: make Mac capture symmetrical
- stop writing directly to canonical entries from the Mac helper
- have the Mac helper append a raw capture request into `ingress/local/`
- let the same committer path handle Mac and iPhone captures

#### Phase 3: introduce journal
- add `journal/YYYY/MM/DD.ndjson`
- have the committer write journal events there
- materialize `notes.txt` from `journal/`, not `entries/`
- keep `entries/` as a compatibility export during transition if desired

#### Phase 4: move clients off Dropbox knowledge
- keep Dropbox only as a file transport if needed
- move mobile clients toward a stable append API
- make producers submit to a stable endpoint, not a backend-specific path

#### Phase 5: add blobs and richer event kinds
- photo/audio/screenshot/link capture
- agent observations and reminders
- sensor and home automation events

---

## Near-term implementation guidance

The next code changes should aim for these invariants:

1. no producer writes `notes.txt`
2. no producer needs read access to existing notes
3. canonical data is append-only
4. all views are regenerated from canonical data
5. all transports are replaceable

### Concretely
- keep the current system working
- introduce `docs/capture-event-v1.md`
- add a future `ingress/` abstraction in code and docs
- gradually route Mac and mobile capture through the same append-only commit path

---

## Long-term identity of notesCapture

`notesCapture` should be thought of as:

- a personal event ingestion layer
- a durable journal
- a set of generated memory views
- a foundation for future agents

Not just as a single notes file or a quick-note app.
