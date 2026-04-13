import unittest

from events_agents.time_use.models import CanonicalJournalEvent
from events_agents.time_use.relevance import classify_relevance


class FakeBackend:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict:
        self.calls += 1
        return self.response


def make_event(text: str) -> CanonicalJournalEvent:
    return CanonicalJournalEvent(
        canonical_event_uid="evt",
        journal_path="journal/2026/03/24.ndjson",
        journal_line_no=1,
        journal_bucket_date="2026-03-24",
        event_id="evt",
        event_type="note.capture",
        schema_name=None,
        schema_version="1",
        captured_at="2026-03-24T14:45:00+05:30",
        committed_at="2026-03-24T14:45:05+05:30",
        source_client="dropbox-ingress",
        source_transport="dropbox-file-drop",
        content_type="text/plain",
        text_body=text,
        raw_event_json={"content": {"text": text}},
    )


class RelevanceTests(unittest.TestCase):
    def test_classify_relevance_marks_actual_time_use_note_relevant(self):
        backend = FakeBackend(
            {
                "eligible": True,
                "relevant": True,
                "confidence": 0.91,
                "reason": "The note states actual time spent debugging.",
            }
        )
        decision = classify_relevance(make_event("spent the last 2 hours debugging auth"), backend=backend)
        self.assertTrue(decision.eligible)
        self.assertTrue(decision.relevant)
        self.assertGreaterEqual(decision.confidence, 0.8)
        self.assertEqual(backend.calls, 1)

    def test_classify_relevance_marks_pure_plan_not_relevant(self):
        backend = FakeBackend(
            {
                "eligible": True,
                "relevant": False,
                "confidence": 0.89,
                "reason": "This is a future plan without execution evidence.",
            }
        )
        decision = classify_relevance(make_event("need to work on taxes later and buy groceries"), backend=backend)
        self.assertTrue(decision.eligible)
        self.assertFalse(decision.relevant)
        self.assertEqual(backend.calls, 1)


if __name__ == "__main__":
    unittest.main()
