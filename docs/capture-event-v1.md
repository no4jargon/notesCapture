# capture-event-v1

This document defines the first formal capture contract for `notesCapture` producers.

It is designed to support:
- text notes now
- richer media later
- write-only producers
- transport-independent ingestion

This is a producer-facing contract, not necessarily the exact on-disk canonical journal format.

## Design goals

- easy to emit from simple clients
- stable across transports
- append-only
- no read dependency on prior state
- future-proof enough for agents and non-text events

## Required fields

### `schema_version`
Integer.

Current value:

```json
1
```

### `kind`
String describing the event type.

Initial recommended values:
- `note.capture`
- `link.capture`
- `image.capture`
- `audio.capture`
- `sensor.event`
- `agent.observation`

### `captured_at`
RFC 3339 timestamp recorded by the producer.

Example:

```json
"2026-03-13T17:24:25+05:30"
```

### `producer`
Object identifying the producer.

Required nested fields:
- `type`
- `id`

Example:

```json
{
  "type": "ios-shortcut",
  "id": "anuj-iphone"
}
```

### `content`
Object describing the payload.

Required nested fields:
- `mime_type`

Common fields by mime type:
- `text` for `text/plain`
- `url` for captured links
- `blob_ref` for larger media stored separately

---

## Recommended fields

### `client_event_id`
Producer-generated idempotency key.

Examples:
- iPhone shortcut filename stem
- browser extension UUID
- watch app UUID

### `metadata`
Free-form object for small structured context.

Examples:
- tags
- app name
- source page title
- location hint
- timezone
- device battery state
- camera zone

### `blobs`
Array of attached blob descriptors for future media capture.

### `parents`
Array of parent event IDs for derived or agent-generated events.

---

## Minimal text note example

```json
{
  "schema_version": 1,
  "kind": "note.capture",
  "captured_at": "2026-03-13T17:24:25+05:30",
  "producer": {
    "type": "mac-hotkey",
    "id": "anuj-mba"
  },
  "client_event_id": "01JPNX8E5A1Y5YDZ3A4R5S6T7U",
  "content": {
    "mime_type": "text/plain",
    "text": "Quick note from Mac"
  },
  "metadata": {
    "tags": []
  }
}
```

## Link capture example

```json
{
  "schema_version": 1,
  "kind": "link.capture",
  "captured_at": "2026-03-13T18:05:00+05:30",
  "producer": {
    "type": "chrome-extension",
    "id": "anuj-chrome"
  },
  "client_event_id": "chrome-5e9f5b88",
  "content": {
    "mime_type": "text/uri-list",
    "url": "https://example.com/article",
    "text": "Interesting article about memory systems"
  },
  "metadata": {
    "page_title": "Memory Systems",
    "tags": ["reading"]
  }
}
```

## Camera / sensor example

```json
{
  "schema_version": 1,
  "kind": "sensor.event",
  "captured_at": "2026-03-13T19:10:04+05:30",
  "producer": {
    "type": "home-camera-agent",
    "id": "living-room-cam-01"
  },
  "client_event_id": "cam01-1741873204",
  "content": {
    "mime_type": "application/json",
    "text": "Motion detected near front door"
  },
  "metadata": {
    "zone": "front-door",
    "confidence": 0.94,
    "tags": ["motion"]
  }
}
```

---

## Transport guidance

## Preferred future transport
Use an authenticated append API:

```http
POST /v1/events
```

## Transitional transport
Use file-drop ingress by writing one JSON file per event into a transport-specific ingress folder.

Example:

```text
ingress/dropbox/ios/2026-03-13_17-24-25-iphone.json
```

A producer should not write directly to:
- canonical journal
- `notes.txt`
- materialized views
- search indexes

---

## Validation rules

A valid `capture-event-v1` payload should satisfy:
- `schema_version == 1`
- `kind` is a non-empty string
- `captured_at` is parseable RFC 3339
- `producer.type` is non-empty
- `producer.id` is non-empty
- `content.mime_type` is non-empty
- payload contains at least one primary content field like `text`, `url`, or `blob_ref`

---

## Producer responsibilities

A producer should:
- create the event payload
- assign `captured_at`
- provide a stable `producer.id`
- provide `client_event_id` if possible
- append the payload once

A producer should not:
- read previous notes
- regenerate `notes.txt`
- inspect canonical journal state
- know what backend is being used

---

## Committer responsibilities

The committer will:
- validate the capture payload
- add `received_at`
- assign canonical `event_id`
- normalize structure if needed
- dedupe using `producer.id + client_event_id` when available
- append committed event to the journal
- route invalid payloads to rejects

That separation keeps capture clients simple and durable.
