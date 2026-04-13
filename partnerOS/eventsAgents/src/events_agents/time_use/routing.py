from __future__ import annotations

from events_agents.time_use.models import CanonicalJournalEvent


ELIGIBLE_EVENT_TYPES = {"note.capture"}
SUPPORTED_MODALITIES = {"text/plain", "text/markdown"}


def is_time_use_eligible(event: CanonicalJournalEvent) -> bool:
    return event.event_type in ELIGIBLE_EVENT_TYPES and event.content_type in SUPPORTED_MODALITIES
