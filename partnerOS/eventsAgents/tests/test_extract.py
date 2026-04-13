import unittest

from events_agents.time_use.extract import extract_time_use_evidence
from events_agents.time_use.models import CanonicalJournalEvent


class FakeBackend:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict:
        self.calls += 1
        return self.response


class ExtractTests(unittest.TestCase):
    def make_event(self, text: str, captured_at: str = "2026-03-25T14:48:21+05:30") -> CanonicalJournalEvent:
        return CanonicalJournalEvent(
            canonical_event_uid="evt-1",
            journal_path="journal/2026/03/25.ndjson",
            journal_line_no=1,
            journal_bucket_date="2026-03-25",
            event_id="evt-1",
            event_type="note.capture",
            schema_name=None,
            schema_version="1",
            captured_at=captured_at,
            committed_at=captured_at,
            source_client="dropbox-ingress",
            source_transport="dropbox-file-drop",
            content_type="text/plain",
            text_body=text,
            raw_event_json={"content": {"text": text}},
        )

    def test_extract_duration_and_interval_evidence(self):
        event = self.make_event("Spent the last 2 hours debugging auth. From 2 to 4 PM I was at the dentist")
        backend = FakeBackend(
            {
                "evidence": [
                    {
                        "actuality": "retrospective_actual",
                        "observed_day_local": "2026-03-25",
                        "observed_start_at": "2026-03-25T12:48:21+05:30",
                        "observed_end_at": "2026-03-25T14:48:21+05:30",
                        "anchor_time_at": "2026-03-25T14:48:21+05:30",
                        "temporal_mode": "relative_interval",
                        "activity_text": "debugging auth",
                        "category": "deep_work",
                        "subcategory": None,
                        "confidence": "high",
                        "supporting_snippet": "Spent the last 2 hours debugging auth",
                        "derivation_notes": "Duration anchored to captured_at.",
                    },
                    {
                        "actuality": "actual",
                        "observed_day_local": "2026-03-25",
                        "observed_start_at": "2026-03-25T14:00:00+05:30",
                        "observed_end_at": "2026-03-25T16:00:00+05:30",
                        "anchor_time_at": "2026-03-25T14:48:21+05:30",
                        "temporal_mode": "explicit_interval",
                        "activity_text": "at the dentist",
                        "category": "social",
                        "subcategory": None,
                        "confidence": "high",
                        "supporting_snippet": "From 2 to 4 PM I was at the dentist",
                        "derivation_notes": "Explicit interval.",
                    },
                ]
            }
        )

        evidence = extract_time_use_evidence(event, backend=backend)

        self.assertEqual(len(evidence), 2)
        self.assertEqual(evidence[0].actuality, "retrospective_actual")
        self.assertEqual(evidence[0].observed_start_at, "2026-03-25T12:48:21+05:30")
        self.assertEqual(evidence[0].observed_end_at, "2026-03-25T14:48:21+05:30")
        self.assertEqual(evidence[1].observed_start_at, "2026-03-25T14:00:00+05:30")
        self.assertEqual(evidence[1].observed_end_at, "2026-03-25T16:00:00+05:30")
        self.assertEqual(backend.calls, 1)

    def test_extract_planned_note_does_not_become_actual(self):
        event = self.make_event("Need to work on taxes later")
        backend = FakeBackend(
            {
                "evidence": [
                    {
                        "actuality": "planned",
                        "observed_day_local": "2026-03-25",
                        "observed_start_at": None,
                        "observed_end_at": None,
                        "anchor_time_at": "2026-03-25T14:48:21+05:30",
                        "temporal_mode": "vague_reflection",
                        "activity_text": "work on taxes later",
                        "category": "admin",
                        "subcategory": None,
                        "confidence": "low",
                        "supporting_snippet": "Need to work on taxes later",
                        "derivation_notes": "Future plan only.",
                    }
                ]
            }
        )

        evidence = extract_time_use_evidence(event, backend=backend)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].actuality, "planned")
        self.assertIsNone(evidence[0].observed_start_at)
        self.assertEqual(backend.calls, 1)


if __name__ == "__main__":
    unittest.main()
