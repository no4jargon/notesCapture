# Current journal contract

Observed from live files under `journal/YYYY/MM/DD.ndjson`.

## Shape seen

Each line is one JSON object with fields such as:
- `schema_version`
- `event_id`
- `kind`
- `captured_at`
- `received_at`
- `producer.type`
- `producer.id`
- `content.mime_type`
- `content.text`
- `metadata`
- `blobs`
- `parents`
- `ingress.transport`
- `ingress.path`

## Observed current event type

For the current corpus sampled during implementation, all observed entries were `kind: note.capture` with:
- `content.mime_type: text/plain`
- producer typically `mobile-file-drop` / `dropbox-ingress`
- `captured_at` carrying the canonical bucket time basis

## Important contract note

`journal/YYYY/MM/DD.ndjson` is bucketed by `captured_at`, but note text may describe activity from another day such as "yesterday" or "last night". The analysis layer must not assume bucket date equals observed activity date.
