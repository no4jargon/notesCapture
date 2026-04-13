# capture-event-v1

`capture-event-v1` is the first formal producer contract for `notesCapture`.

It is designed for:
- write-only producers
- transport-independent ingestion
- text capture now
- richer media later

This is a producer-facing contract, not necessarily the final on-disk journal format.

## Required fields

### `schema_version`
Integer.

Current value:

```json
1
```

### `kind`
Non-empty string.

Common values:
- `note.capture`
- `link.capture`
- `image.capture`
- `audio.capture`
- `sensor.event`
- `agent.observation`

### `captured_at`
RFC 3339 timestamp set by the producer.

Example:

```json
"2026-03-13T17:24:25+05:30"
```

### `producer`
Object with:
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
Object with:
- `mime_type`

Common content fields:
- `text`
- `url`
- `blob_ref`

## Recommended fields

- `client_event_id` — producer idempotency key
- `metadata` — small structured context
- `blobs` — attached blob descriptors
- `parents` — parent event IDs for derived events

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

## Sensor example

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

## Transport guidance

### Preferred future transport

```http
POST /v1/events
```

### Transitional transport
Write one file per event into a transport-specific ingress folder.

Example:

```text
ingress/dropbox/ios/2026-03-13_17-24-25-iphone.json
```

A producer should not write directly to:
- canonical journal
- `notes.txt`
- materialized views
- search indexes

## Validation rules

A valid payload should satisfy:
- `schema_version == 1`
- `kind` is non-empty
- `captured_at` is valid RFC 3339
- `producer.type` is non-empty
- `producer.id` is non-empty
- `content.mime_type` is non-empty
- payload contains at least one primary content field such as `text`, `url`, or `blob_ref`

## Producer responsibilities

A producer should:
- create the payload
- assign `captured_at`
- provide stable `producer.id`
- provide `client_event_id` when possible
- append once

A producer should not:
- read previous notes
- regenerate `notes.txt`
- inspect canonical journal state
- know what backend is in use

## Committer responsibilities

The committer should:
- validate payloads
- add `received_at`
- assign canonical `event_id`
- normalize structure if needed
- dedupe using `producer.id + client_event_id` when available
- append committed events to the journal
- route invalid payloads to rejects
