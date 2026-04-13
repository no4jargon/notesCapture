import unittest

from events_agents.time_use.extract import extract_time_use_evidence
from events_agents.time_use.models import CanonicalJournalEvent


class ExtractMoreIntervalsTests(unittest.TestCase):
    def test_extract_compact_explicit_interval_without_from_keyword(self):
        event = CanonicalJournalEvent(
            canonical_event_uid="evt-1",
            journal_path="journal/2026/03/25.ndjson",
            journal_line_no=1,
            journal_bucket_date="2026-03-25",
            event_id="evt-1",
            event_type="note.capture",
            schema_name=None,
            schema_version="1",
            captured_at="2026-03-25T20:48:20+05:30",
            committed_at="2026-03-25T20:48:20+05:30",
            source_client="dropbox-ingress",
            source_transport="dropbox-file-drop",
            content_type="text/plain",
            text_body="6:15 to 6:45 worked",
            raw_event_json={"content": {"text": "6:15 to 6:45 worked"}},
        )

        evidence = extract_time_use_evidence(event)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].observed_start_at, "2026-03-25T18:15:00+05:30")
        self.assertEqual(evidence[0].observed_end_at, "2026-03-25T18:45:00+05:30")
        self.assertEqual(evidence[0].actuality, "actual")


if __name__ == "__main__":
    unittest.main()
