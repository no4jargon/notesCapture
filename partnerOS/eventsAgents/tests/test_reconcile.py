import unittest

from events_agents.time_use.models import TimeUseEvidence
from events_agents.time_use.reconcile import reconcile_day


class ReconcileTests(unittest.TestCase):
    def test_reconcile_day_preserves_unknown_gaps(self):
        evidence = [
            TimeUseEvidence(
                evidence_id="e1",
                canonical_event_uid="evt-1",
                source_event_type="note.capture",
                actuality="actual",
                observed_day_local="2026-03-25",
                observed_start_at="2026-03-25T10:00:00+05:30",
                observed_end_at="2026-03-25T11:00:00+05:30",
                anchor_time_at="2026-03-25T11:00:00+05:30",
                temporal_mode="explicit_interval",
                activity_text="debugging auth",
                category="deep_work",
                subcategory=None,
                confidence="high",
                supporting_snippet="debugging auth",
                derivation_notes="",
            ),
            TimeUseEvidence(
                evidence_id="e2",
                canonical_event_uid="evt-2",
                source_event_type="note.capture",
                actuality="actual",
                observed_day_local="2026-03-25",
                observed_start_at="2026-03-25T11:20:00+05:30",
                observed_end_at="2026-03-25T12:00:00+05:30",
                anchor_time_at="2026-03-25T12:00:00+05:30",
                temporal_mode="explicit_interval",
                activity_text="more debugging auth",
                category="deep_work",
                subcategory=None,
                confidence="high",
                supporting_snippet="more debugging auth",
                derivation_notes="",
            ),
        ]

        blocks, gaps = reconcile_day("2026-03-25", evidence, merge_threshold_minutes=15, bridge_threshold_minutes=60)

        self.assertEqual(len(blocks), 2)
        self.assertEqual(gaps[0]["start_at"], "2026-03-25T00:00:00+05:30")
        self.assertEqual(gaps[1]["start_at"], "2026-03-25T11:00:00+05:30")
        self.assertEqual(gaps[1]["end_at"], "2026-03-25T11:20:00+05:30")


if __name__ == "__main__":
    unittest.main()
