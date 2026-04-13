import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from events_agents.adapters.journal_fs import iter_canonical_journal_events
from events_agents.index.sqlite_store import SQLiteStore


class JournalAdapterTests(unittest.TestCase):
    def test_iter_canonical_journal_events_normalizes_note_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            journal_file = data_dir / "journal" / "2026" / "03" / "24.ndjson"
            journal_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": 1,
                "event_id": "evt-1",
                "kind": "note.capture",
                "captured_at": "2026-03-24T14:45:00+05:30",
                "received_at": "2026-03-24T14:45:05+05:30",
                "producer": {"type": "mobile-file-drop", "id": "dropbox-ingress"},
                "content": {"mime_type": "text/plain", "text": "worked for 2 hours"},
                "metadata": {},
                "blobs": [],
                "parents": [],
                "ingress": {"transport": "dropbox-file-drop", "path": "ingress/dropbox/a.txt"},
            }
            journal_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            events = list(iter_canonical_journal_events(data_dir))

            self.assertEqual(len(events), 1)
            event = events[0]
            self.assertEqual(event.event_type, "note.capture")
            self.assertEqual(event.event_id, "evt-1")
            self.assertEqual(event.text_body, "worked for 2 hours")
            self.assertEqual(event.content_type, "text/plain")
            self.assertEqual(event.journal_bucket_date, "2026-03-24")
            self.assertTrue(event.canonical_event_uid)
            self.assertEqual(event.journal_line_no, 1)

    def test_import_journal_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            state_dir = root / "state"
            journal_file = data_dir / "journal" / "2026" / "03" / "24.ndjson"
            journal_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": 1,
                "event_id": "evt-1",
                "kind": "note.capture",
                "captured_at": "2026-03-24T14:45:00+05:30",
                "received_at": "2026-03-24T14:45:05+05:30",
                "producer": {"type": "mobile-file-drop", "id": "dropbox-ingress"},
                "content": {"mime_type": "text/plain", "text": "worked for 2 hours"},
                "metadata": {},
                "blobs": [],
                "parents": [],
                "ingress": {"transport": "dropbox-file-drop", "path": "ingress/dropbox/a.txt"},
            }
            journal_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            store = SQLiteStore(state_dir / "time_use.db")
            first = store.import_journal(data_dir)
            second = store.import_journal(data_dir)

            self.assertEqual(first["imported"], 1)
            self.assertEqual(second["imported"], 0)
            with sqlite3.connect(state_dir / "time_use.db") as conn:
                count = conn.execute("select count(*) from journal_events").fetchone()[0]
            self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
