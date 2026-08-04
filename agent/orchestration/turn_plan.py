"""The single resolved plan for one customer turn.

Before this existed, the sort, navigation and inventory shortcuts each re-parsed
the raw utterance and answered on their own authority. Whichever pattern matched
first won, so a budgeted search ("a phone under 50,000") or a gift recommendation
("something for my girlfriend") could be stolen by the inventory-count shortcut -
which then searched for a product literally named "something" and ignored the
budget entirely.

A ``TurnPlan`` is resolved once, before any shortcut runs, and is immutable.
Shortcuts consume ``plan.operation`` instead of re-interpreting the customer.
They may still optimise execution; they may no longer decide what was meant.

The module is vertical-independent: brand and product-type vocabularies are
supplied by the caller from tenant data, and nothing here knows about any
particular retailer, catalogue or category name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent.retrieval.query_constraints import QueryConstraints, extract_ecommerce_constraints
from agent.retrieval.resolved_context import resolve_turn_context

MAX_REFERENT_IDS = 24


class TurnOperation(str, Enum):
    """What the customer is asking the assistant to DO this turn."""

    SEARCH = "search"
    RECOMMEND = "recommend"
    AGGREGATE = "aggregate"
    COMPARE = "compare"
    NAVIGATE = "navigate"
    SORT = "sort"
    INVENTORY_COUNT = "inventory_count"
    PAGE_QUESTION = "page_question"
    CLARIFY = "clarify"


# Aggregate questions name a superlative over a set rather than a product.
_AGGREGATE_PATTERNS = (
    ("cheapest", r"\b(cheapest|least expensive|lowest priced?|most affordable|budget friendly)\b"),
    ("most_expensive", r"\b(most expensive|dearest|highest priced?|priciest|top end)\b"),
    ("best_rated", r"\b(best[- ]rated|highest[- ]rated|top[- ]rated|best reviewed|best rating)\b"),
)
_COUNT_RE = re.compile(r"\bhow many\b|\bnumber of\b|\bcount of\b|\btotal\b.{0,20}\b(products?|items?)\b", re.IGNORECASE)
_COMPARE_RE = re.compile(r"\bcompare\b|\bversus\b|\bvs\.?\b|\bdifference between\b", re.IGNORECASE)
_SORT_RE = re.compile(
    r"\bsort\b|\border by\b|\b(low|high)(est)? to (low|high)(est)?\b|\bprice (ascending|descending)\b",
    re.IGNORECASE,
)
_NAVIGATE_RE = re.compile(
    r"\b(take me (?:to|there)|go (?:to|there)|open|navigate to|show me the .{0,20}page|visit)\b",
    re.IGNORECASE,
)
# Questions about what the customer can already see on screen.
_PAGE_QUESTION_RE = re.compile(
    r"\b(visible|on (?:the )?screen|on this page|showing|displayed|currently shown|these results)\b",
    re.IGNORECASE,
)
# Referential or corrective turns depend on prior state, so they are never cached.
_STATE_DEPENDENT_RE = re.compile(
    r"\b(these|those|this one|that one|them|the (?:first|second|third|last|other|cheaper))\b"
    r"|^\s*(?:but|no|actually|i said|i meant)\b",
    re.IGNORECASE,
)
_CART_RE = re.compile(r"\b(cart|basket|checkout|buy now|add to bag)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TurnPlan:
    """An immutable, fully resolved description of one turn."""

    turn_id: str
    session_id: str
    site_id: str
    vertical: str
    operation: TurnOperation
    constraints: QueryConstraints
    aggregate: str = ""
    requested_count: int | None = None
    referent_ids: tuple[str, ...] = ()
    page_state: dict[str, Any] | None = None
    navigation_requested: bool = False
    is_followup: bool = False
    is_topic_change: bool = False
    cache_eligible: bool = True
    catalog_version: str = ""
    inherited_fields: tuple[str, ...] = field(default_factory=tuple)
    # Resolved once here so the clarification stage consumes the plan instead of
    # resolving the turn a second time against slightly different context.
    needs_clarification: bool = False
    clarification_question: str = ""

    def hard_constraints(self) -> dict[str, Any]:
        """Pass/fail facts that ranking, actions and text may never override."""
        constraints: dict[str, Any] = {}
        if self.constraints.max_price is not None:
            constraints["max_price"] = self.constraints.max_price
        if self.constraints.min_price is not None:
            constraints["min_price"] = self.constraints.min_price
        if self.constraints.brands:
            constraints["brands"] = tuple(self.constraints.brands)
        if self.constraints.product_types:
            constraints["product_types"] = tuple(self.constraints.product_types)
        if self.constraints.exclusions:
            constraints["exclusions"] = tuple(self.constraints.exclusions)
        return constraints

    def price_constraints(self) -> dict[str, float]:
        return self.constraints.price_constraints()

    def allows_shortcut(self, operation: TurnOperation) -> bool:
        """True when a shortcut for ``operation`` may answer this turn.

        A shortcut runs only when the resolved plan agrees that is what the
        customer asked for, which is what stops an inventory browse from
        answering a budgeted search or a gift recommendation.
        """
        if self.operation == operation:
            return True
        # The catalog shortcut is also a legitimate fast path for a plain brand or
        # type browse ("do you have iPhone?"). It is allowed to optimise execution
        # but never to bypass a constraint it cannot apply, so a budget, a
        # recipient, or an exclusion sends the turn down the full pipeline.
        if operation == TurnOperation.INVENTORY_COUNT and self.operation == TurnOperation.SEARCH:
            return not self.bypasses_constraints_if_shortcut()
        # Tenant route discovery recognises navigational phrasings this module
        # deliberately does not hard-code ("I'm interested in life insurance").
        # The shortcut may still try, and returns nothing when no route matches -
        # but only for turns whose constraints it could not silently drop.
        if operation == TurnOperation.NAVIGATE and self.operation in {
            TurnOperation.SEARCH,
            TurnOperation.RECOMMEND,
        }:
            return not self.bypasses_constraints_if_shortcut()
        return False

    def bypasses_constraints_if_shortcut(self) -> bool:
        """True when a fast catalog path would silently drop a hard constraint."""
        return bool(
            self.constraints.has_price_constraint()
            or self.constraints.recipient
            or self.constraints.occasion
            or self.constraints.exclusions
        )

    def cache_key_component(self) -> str:
        """Stable fingerprint of operation + hard constraints for cache identity."""
        parts = [f"op={self.operation.value}", f"agg={self.aggregate}"]
        for key in sorted(self.hard_constraints()):
            value = self.hard_constraints()[key]
            rendered = ",".join(map(str, value)) if isinstance(value, tuple) else value
            parts.append(f"{key}={rendered}")
        if self.constraints.recipient:
            parts.append(f"recipient={self.constraints.recipient}")
        if self.requested_count:
            parts.append(f"n={self.requested_count}")
        return "|".join(parts)


def _detect_aggregate(text: str) -> str:
    for name, pattern in _AGGREGATE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return ""


def _visible_ids(page_state: dict[str, Any] | None) -> tuple[str, ...]:
    entities = (page_state or {}).get("visible_entities")
    if not isinstance(entities, list):
        return ()
    ids = [
        str(entity.get("id")).strip()
        for entity in entities
        if isinstance(entity, dict) and str(entity.get("id") or "").strip()
    ]
    return tuple(ids[:MAX_REFERENT_IDS])


def _classify(text: str, resolved, aggregate: str) -> TurnOperation:
    """Resolve exactly one operation, in priority order.

    Page-relative questions win first because they must never trigger a catalog
    search; explicit navigation and sort follow; aggregates and comparisons are
    checked before the count pattern so that "cheapest" is not mistaken for an
    inventory question; a recipient or occasion makes the turn a recommendation
    rather than a literal search for the word the customer used.
    """
    if _PAGE_QUESTION_RE.search(text):
        return TurnOperation.PAGE_QUESTION
    if _SORT_RE.search(text):
        return TurnOperation.SORT
    if _COMPARE_RE.search(text):
        return TurnOperation.COMPARE
    if aggregate:
        return TurnOperation.AGGREGATE
    if _NAVIGATE_RE.search(text):
        return TurnOperation.NAVIGATE
    if _COUNT_RE.search(text):
        return TurnOperation.INVENTORY_COUNT

    constraints = resolved.constraints
    if constraints.recipient or constraints.occasion:
        return TurnOperation.RECOMMEND
    if resolved.should_ask_clarification():
        return TurnOperation.CLARIFY
    return TurnOperation.SEARCH


def _is_cache_eligible(operation: TurnOperation, text: str, resolved) -> bool:
    """Only stable, self-contained catalog answers may be replayed.

    Anything that depends on where the customer is, what they were just shown, or
    a correction they just made must be recomputed, because a cached answer would
    describe a different screen than the one in front of them.
    """
    if operation in {
        TurnOperation.PAGE_QUESTION,
        TurnOperation.NAVIGATE,
        TurnOperation.SORT,
        TurnOperation.CLARIFY,
    }:
        return False
    if _STATE_DEPENDENT_RE.search(text) or _CART_RE.search(text):
        return False
    return not resolved.constraints.is_followup


def build_turn_plan(
    utterance: str,
    *,
    site_id: str,
    session_id: str = "",
    turn_id: str = "",
    vertical: str = "ecommerce",
    history: list[dict] | None = None,
    session_summary: str = "",
    page_state: dict[str, Any] | None = None,
    catalog_brands: tuple[str, ...] | list[str] = (),
    catalog_types: tuple[str, ...] | list[str] = (),
    catalog_version: str = "",
) -> TurnPlan:
    """Resolve one turn into an immutable plan. Pure, deterministic, no I/O."""
    text = str(utterance or "")
    resolved = resolve_turn_context(
        text,
        history=list(history or []),
        session_summary=session_summary,
        recent_product_ids=_visible_ids(page_state),
        catalog_brands=catalog_brands,
        catalog_types=catalog_types,
    )
    aggregate = _detect_aggregate(text)
    operation = _classify(text, resolved, aggregate)
    navigation_requested = bool(_NAVIGATE_RE.search(text))

    # A page question answers from the screen, so its referents are whatever the
    # page reported - never a fresh catalog lookup.
    referents = _visible_ids(page_state) if operation == TurnOperation.PAGE_QUESTION else resolved.referenced_product_ids

    return TurnPlan(
        turn_id=turn_id,
        session_id=session_id,
        site_id=site_id,
        vertical=vertical,
        operation=operation,
        constraints=resolved.constraints,
        aggregate=aggregate,
        requested_count=resolved.requested_count,
        referent_ids=tuple(referents),
        page_state=page_state,
        navigation_requested=navigation_requested,
        is_followup=resolved.constraints.is_followup,
        is_topic_change=resolved.is_topic_change,
        cache_eligible=_is_cache_eligible(operation, text, resolved) and not navigation_requested,
        catalog_version=catalog_version,
        inherited_fields=resolved.inherited_fields,
        needs_clarification=resolved.should_ask_clarification(),
        clarification_question=resolved.clarification_question() if resolved.should_ask_clarification() else "",
    )


def empty_constraints(utterance: str = "") -> QueryConstraints:
    """A constraint set for callers that need a plan-shaped value without context."""
    return extract_ecommerce_constraints(utterance)
