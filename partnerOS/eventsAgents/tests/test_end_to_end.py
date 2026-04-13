import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from events_agents.cli import main


class EndToEndTests(unittest.TestCase):
    def test_build_and_report_last_complete_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            state_dir = root / "agent-state"
            journal_file = data_dir / "journal" / "2026" / "03" / "25.ndjson"
            journal_file.parent.mkdir(parents=True, exist_ok=True)
            notes = [
                {
                    "schema_version": 1,
                    "event_id": "evt-1",
                    "kind": "note.capture",
                    "captured_at": "2026-03-25T14:48:21+05:30",
                    "received_at": "2026-03-25T14:48:21+05:30",
                    "producer": {"type": "mobile-file-drop", "id": "dropbox-ingress"},
                    "content": {"mime_type": "text/plain", "text": "Spent the last 2 hours debugging auth"},
                    "metadata": {},
                    "blobs": [],
                    "parents": [],
                    "ingress": {"transport": "dropbox-file-drop", "path": "ingress/dropbox/a.txt"},
                },
                {
                    "schema_version": 1,
                    "event_id": "evt-2",
                    "kind": "note.capture",
                    "captured_at": "2026-03-27T16:30:51+05:30",
                    "received_at": "2026-03-27T16:30:51+05:30",
                    "producer": {"type": "mobile-file-drop", "id": "dropbox-ingress"},
                    "content": {"mime_type": "text/plain", "text": "From 1 to 2 PM I was at the dentist"},
                    "metadata": {},
                    "blobs": [],
                    "parents": [],
                    "ingress": {"transport": "dropbox-file-drop", "path": "ingress/dropbox/b.txt"},
                },
            ]
            journal_file.write_text("\n".join(json.dumps(n) for n in notes) + "\n", encoding="utf-8")

            result = main([
                "--state-dir", str(state_dir),
                "time-use",
                "build",
                "--data-dir", str(data_dir),
                "--week", "2026-03-23",
            ])
            self.assertEqual(result, 0)

            report_result = main([
                "--state-dir", str(state_dir),
                "time-use",
                "report",
                "--data-dir", str(data_dir),
                "--week", "2026-03-23",
            ])
            self.assertEqual(report_result, 0)

            report_path = state_dir / "reports" / "time_use" / "weekly" / "2026-W13.md"
            self.assertTrue(report_path.exists())
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("Time Use Report", report_text)
            self.assertIn("Deep work", report_text)
            self.assertIn("[event: evt-1]", report_text)

            with sqlite3.connect(state_dir / "time_use.db") as conn:
                block_count = conn.execute("select count(*) from time_use_blocks").fetchone()[0]
                decision_count = conn.execute("select count(*) from purpose_relevance where relevant = 1").fetchone()[0]
            self.assertEqual(block_count, 2)
            self.assertEqual(decision_count, 2)


if __name__ == "__main__":
    unittest.main()
