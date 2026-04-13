from __future__ import annotations

import json
import uuid

from events_agents.llm.backend import default_backend, load_prompt
from events_agents.time_use.models import CanonicalJournalEvent, PurposeRelevanceDecision
from events_agents.time_use.routing import is_time_use_eligible

RELEVANCE_SYSTEM_PROMPT = load_prompt("relevance_system.txt")


ACTUAL_HINTS = (
    "spent",
    "worked",
    "was at",
    "woke up",
    "slept",
    "gym",
    "meeting",
    "meetings",
    "debugging",
    "worked out",
    "replied to messages",
    "had lunch",
    "had breakfast",
    "ate",
    "read",
    "instagram",
    "youtube",
    "doomscroll",
)
PLAN_ONLY_HINTS = (
    "need to",
    "should ",
    "todo",
    "buy groceries",
    "remind me",
)


def _heuristic_classify(event: CanonicalJournalEvent) -> tuple[bool, float, str]:
    text = (event.text_body or "").strip().lower()
    if text.startswith("need to ") or text.startswith("should ") or text.startswith("todo"):
        return False, 0.9, "plan-only note without evidence of actual time use"
    if any(token in text for token in PLAN_ONLY_HINTS) and not any(token in text for token in ("spent", "was at", "worked until", "woke up", "slept")):
        return False, 0.85, "plan-only note without evidence of actual time use"
    if any(token in text for token in ACTUAL_HINTS) or any(char.isdigit() for char in text):
        return True, 0.9 if any(char.isdigit() for char in text) else 0.8, "contains actual activity or time-spent language"
    return False, 0.6, "no strong evidence of actual time use"


def classify_relevance(event: CanonicalJournalEvent, backend=None) -> PurposeRelevanceDecision:
    eligible = is_time_use_eligible(event)
    relevant = False
    confidence = 0.2
    reason = "ineligible event type or modality"
    decided_by = "heuristic"
    classifier_version = "time_use_relevance_v1"

    if eligible:
        backend = backend or default_backend()
        if backend and getattr(backend, "available", lambda: True)():
            user_prompt = json.dumps(
                {
                    "event_type": event.event_type,
                    "content_type": event.content_type,
                    "captured_at": event.captured_at,
                    "journal_bucket_date": event.journal_bucket_date,
                    "text_body": event.text_body,
                },
                ensure_ascii=False,
                indent=2,
            )
            response = backend.complete_json(system_prompt=RELEVANCE_SYSTEM_PROMPT, user_prompt=user_prompt)
            relevant = bool(response["relevant"])
            confidence = float(response["confidence"])
            reason = str(response["reason"])
            eligible = bool(response.get("eligible", eligible))
            decided_by = backend.__class__.__name__
            classifier_version = f"{classifier_version}+llm"
        else:
            relevant, confidence, reason = _heuristic_classify(event)

    return PurposeRelevanceDecision(
        decision_id=str(uuid.uuid4()),
        purpose_id="time_use",
        canonical_event_uid=event.canonical_event_uid,
        eligible=eligible,
        relevant=relevant,
        confidence=confidence,
        reason=reason,
        decided_by=decided_by,
        classifier_version=classifier_version,
    )
