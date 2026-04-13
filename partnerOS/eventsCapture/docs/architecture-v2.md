# notesCapture v2 architecture

## Purpose

This document describes the target architecture for `notesCapture` as a many-producer, append-only personal capture system.

The main goal is decoupling:
- producers should only capture
- canonical storage should be stable
- views should be generated
- transports should be replaceable

## Core principles

1. **Producers are write-only**
   - producers append captures
   - they do not read prior state

2. **The journal is canonical**
   - not `notes.txt`
   - not transport folders
   - not indexes or agent outputs

3. **Views are generated**
   - `notes.txt` is a materialized view

4. **Transports are adapters**
   - Dropbox, local folders, HTTP, email, and queues are transport choices
   - they are not the producer contract

5. **Agents append, not mutate**
   - agents read journal or views
   - if they write, they append new events

## Mental model

```text
many producers
    -> ingress adapters
    -> commit / normalize / dedupe
    -> canonical append-only journal
    -> materializers / indexes / agents
    -> generated views
```

## Layers

### Producers
Examples:
- Mac quick note popup
- iPhone Shortcut
- Android automation
- browser extension
- webhook sender
- agent-generated observation

### Ingress adapters
Transport-specific staging zones.

Examples:
- `ingress/dropbox/`
- `ingress/local/`
- local HTTP API
- remote HTTPS API

### Committer
Boundary between raw input and canonical truth.

Responsibilities:
- validate payloads
- normalize timestamps
- attach `received_at`
- assign canonical IDs if needed
- dedupe or enforce idempotency
- write canonical events
- route invalid input to rejects

### Canonical journal
Recommended format:

```text
journal/2026/03/13.ndjson
```

One line = one committed event.

### Materializers and indexes
Examples:
- `views/notes.txt`
- daily exports
- SQLite search index
- embeddings index
- task extraction view

### Agents
Agents should read stable views or the journal, then append new events like:
- `agent.summary`
- `agent.reminder`
- `agent.observation`

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

## Canonical event shape

Minimum fields:
- `schema_version`
- `event_id`
- `kind`
- `producer`
- `captured_at`
- `received_at`
- `content`
- `metadata`

Useful additional fields:
- `client_event_id`
- `ingress`
- `blobs`
- `parents`

Example:

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

## Transitional producer contract

Preferred long-term API:

```http
POST /v1/events
Authorization: Bearer <token>
Content-Type: application/json
```

Transitional file-drop contract:
- producers write one raw payload file into a transport-specific ingress folder
- JSON is preferred
- plain text is acceptable during transition

Example:

```text
ingress/dropbox/ios/
```

## Idempotency and time

Producers should eventually send:
- `producer.id`
- `client_event_id`

The committer should use those for dedupe.

Preserve both:
- `captured_at`
- `received_at`

## Security model

### Producers
- write-only when possible
- no direct read access to journal or views

### Committer
- privileged access to journal, rejects, and state

### Readers and agents
- read journal and derived read models
- append new events through the same write boundary

## Materialization

`notes.txt` remains useful, but only as a view.

A materializer should:
- read canonical data
- select note-like events
- sort by `captured_at`
- render a stable timeline

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

1. **formalize contracts**
   - add `capture-event-v1`
   - document `ingress/` as the current producer boundary
   - document `entries/` as current canonical storage

2. **introduce a committer boundary**
   - have the Mac helper append a raw capture request into `ingress/local/`
   - route Mac and mobile through the same commit path

3. **introduce the journal**
   - add `journal/YYYY/MM/DD.ndjson`
   - materialize from `journal/`
   - optionally keep `entries/` as a compatibility export during transition

4. **hide backend details from producers**
   - keep Dropbox only as a transport if needed
   - move producers toward a stable append API

## Near-term invariants

The next code changes should preserve these rules:
1. no producer writes `notes.txt`
2. no producer needs read access to existing notes
3. canonical data is append-only
4. all views are regenerated from canonical data
5. transports are replaceable

## Long-term identity

`notesCapture` should become:
- a personal event ingestion layer
- a durable journal
- a set of generated memory views
- a foundation for future agents
