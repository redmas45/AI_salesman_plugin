"""Deciding whether a turn is understood well enough to act on.

Matching produces confidences, not verdicts, so something has to decide between
acting and asking. Conversational-search work treats this as its own decision:
a system assesses its confidence in an interpretation and either answers or asks
a clarifying question, and when it asks, offering the candidate interpretations
lets the user choose instead of describing the ambiguity again
(Aliannejadi et al., 2019; Keyvan & Huang, ACM Computing Surveys, 2022).

Three outcomes:

* **Act** - one interpretation is clearly best.
* **Choose** - two or more interpretations are close, so the customer is offered
  them by name. This is the case that used to be resolved by guessing, which is
  how a request for one thing was answered with another.
* **Ask** - nothing published is a plausible reading, so the turn gets one open
  question rather than an invented answer.

Never silently substituting a value the customer did not say is required by
rules.md section 14 ("Ask, Never Assume").
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.nlu.frame import SemanticFrame
from agent.nlu.schema import SlotCandidate

DECISION_ACT = "act"
DECISION_CHOOSE = "choose"
DECISION_ASK = "ask"

# A reading below this is a guess, not an interpretation.
CONFIDENCE_FLOOR = 0.7
# Two readings closer together than this are not distinguishable, so the
# customer decides rather than the ranker.
AMBIGUITY_MARGIN = 0.12
# More options than this stops being a question and becomes a list.
MAX_OFFERED_OPTIONS = 4


@dataclass(frozen=True)
class SlotDecision:
    """What to do about one slot, and the options if the customer must choose."""

    slot: str
    decision: str
    value: str = ""
    confidence: float = 0.0
    options: tuple[str, ...] = ()

    @property
    def is_resolved(self) -> bool:
        return self.decision == DECISION_ACT


def decide_slot(slot: str, candidates: tuple[SlotCandidate, ...]) -> SlotDecision:
    """Act on a clear winner, offer close runners-up, otherwise ask."""
    viable = [candidate for candidate in candidates if candidate.confidence >= CONFIDENCE_FLOOR]
    if not viable:
        return SlotDecision(slot=slot, decision=DECISION_ASK)

    best = viable[0]
    contenders = [
        candidate
        for candidate in viable
        if best.confidence - candidate.confidence <= AMBIGUITY_MARGIN
    ]
    if len(contenders) <= 1:
        return SlotDecision(
            slot=slot,
            decision=DECISION_ACT,
            value=best.value,
            confidence=best.confidence,
        )
    return SlotDecision(
        slot=slot,
        decision=DECISION_CHOOSE,
        confidence=best.confidence,
        options=tuple(candidate.value for candidate in contenders[:MAX_OFFERED_OPTIONS]),
    )


def _human_options(options: tuple[str, ...]) -> str:
    if len(options) <= 1:
        return options[0] if options else ""
    return f"{', '.join(options[:-1])} or {options[-1]}"


def clarification_question(frame: SemanticFrame, decisions: tuple[SlotDecision, ...]) -> str:
    """One short question, offering the options whenever there are any.

    Prefers a choice between named alternatives, because picking from a list is
    easier for the customer than restating the request.
    """
    for decision in decisions:
        if decision.decision == DECISION_CHOOSE and decision.options:
            return f"Which {decision.slot} did you mean: {_human_options(decision.options)}?"

    unmatched = frame.content_words
    families = frame.schema.families[:MAX_OFFERED_OPTIONS]
    if unmatched and families:
        named = unmatched[0]
        return (
            f"I could not find {named} in this catalogue. "
            f"Did you mean {_human_options(families)}?"
        )
    if families:
        return f"What are you looking for: {_human_options(families)}?"
    return "Could you tell me what you are looking for?"
