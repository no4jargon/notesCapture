import unittest

from events_agents.time_use.aggregate import build_daily_rollup
from events_agents.time_use.models import TimeUseBlock


class AggregateTests(unittest.TestCase):
    def test_build_daily_rollup_counts_unknown_minutes(self):
        blocks = [
            TimeUseBlock(
                block_id="b1",
                day_local="2026-03-25",
                start_at="2026-03-25T10:00:00+05:30",
                end_at="2026-03-25T11:30:00+05:30",
                category="deep_work",
                label="debugging",
                confidence="high",
                source_evidence_ids=["e1"],
                derivation_type="direct",
            )
        ]

        rollup = build_daily_rollup("2026-03-25", blocks)

        self.assertEqual(rollup.category_totals["deep_work"], 90)
        self.assertEqual(rollup.unknown_minutes, 1350)
        self.assertEqual(rollup.number_of_blocks, 1)


if __name__ == "__main__":
    unittest.main()
