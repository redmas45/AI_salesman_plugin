"""Cached and uncached turns must be semantically the same answer.

Slice 10 gave the cache a constraint-aware key, and the TurnPlan work decided
which turns may be replayed at all - but nothing proved that a replayed answer
still says the same thing, names the same records, and drives the same actions.
A cache that quietly serves a different answer is worse than no cache, because
the difference only appears for the second customer to ask.

These tests run the real pipeline twice against an in-memory cache that mirrors
the production key (tenant, session, catalog version, and the constraint
signature via the real `normalize_question`), and compare the two answers field
by field.
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.cache.answer_cache import normalize_question  # noqa: E402

SITE_A = "ecommerce_site"
SITE_B = "other_site"
SESSION_A = "session-a"
SESSION_B = "session-b"

CATALOG = [
    {"id": "1", "name": "Aster Kurta", "brand": "Aster", "category_name": "Fashion Women",
     "price": 499.0, "rating": 4.2, "review_count": 18, "stock": 5},
    {"id": "2", "name": "Corvi Smartphone X1", "brand": "Corvi", "category_name": "Electronics",
     "price": 42999.0, "rating": 4.4, "review_count": 120, "stock": 2},
]

ANSWER_TEXT = "The Corvi Smartphone X1 is a strong pick at ₹42,999."
ANSWER_ACTIONS = [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["2"]}}]

# Fields that must survive a cache round trip unchanged. `latency_ms` and the
# retrieval evidence legitimately differ - one answer was computed, the other
# replayed - so they are compared separately and loosely.
EQUIVALENT_FIELDS = ("response_text", "ui_actions", "answer_scope", "intent")


class InMemoryAnswerCache:
    """A cache double keyed exactly as the production table is keyed."""

    def __init__(self) -> None:
        self.rows: dict[tuple, dict] = {}
        self.data_version = 1
        self.lookups: list[tuple] = []

    def _key(self, site_id: str, session_id: str, question: str, signature: str) -> tuple:
        return (site_id, session_id, normalize_question(question, signature), self.data_version)

    def lookup(self, site_id, question, session_id="", constraint_signature=""):
        key = self._key(site_id, session_id, question, constraint_signature)
        self.lookups.append(key)
        row = self.rows.get(key)
        return dict(row) if row else None

    def store(self, site_id, *, session_id="", question="", answer_text="", answer_scope="",
              cache_type="", source_ids=(), source_urls=(), ui_actions=(), confidence=0.0,
              constraint_signature=""):
        key = self._key(site_id, session_id, question, constraint_signature)
        self.rows[key] = {
            "answer_text": answer_text,
            "answer_scope": answer_scope,
            "ui_actions": [dict(action) for action in ui_actions or []],
            "confidence": confidence,
            "source_ids": list(source_ids or []),
            "source_urls": list(source_urls or []),
            "data_version": self.data_version,
            "match_type": "exact",
            "match_score": 1.0,
        }
        return dict(self.rows[key])

    def bump_data_version(self) -> None:
        self.data_version += 1


@pytest.fixture
def cached_pipeline(monkeypatch):
    from agent import orchestrator
    from agent.runtime_helpers.retrieval_runtime import RetrievalContext

    cache = InMemoryAnswerCache()
    llm_calls: list[str] = []

    def fake_llm(site_id, transcript, products, **kwargs):
        llm_calls.append(transcript)
        return {
            "response_text": ANSWER_TEXT,
            "intent": "product_search",
            "confidence": 0.9,
            "answer_scope": "product_search",
            "ui_actions": [dict(action) for action in ANSWER_ACTIONS],
        }

    # This suite is about cache identity and equivalence, so every other
    # database-backed collaborator is supplied as a fixture rather than skipped.
    # Failing the connection immediately keeps the run fast and deterministic:
    # without it every optional lookup waits out a full connect timeout.
    def no_database(*_args, **_kwargs):
        raise psycopg.OperationalError("database intentionally unavailable in this suite")

    monkeypatch.setattr(psycopg, "connect", no_database)
    monkeypatch.setattr("db.core.database._get_connection", no_database)
    monkeypatch.setattr(
        "agent.retrieval.catalog_vocabulary.catalog_brand_vocabulary",
        lambda site_id: ("aster", "corvi"),
    )
    monkeypatch.setattr(
        "agent.action_helpers.capabilities.admin_db._client_row",
        lambda site_id: {"vertical_key": "ecommerce", "vertical_config_json": "{}"},
    )
    monkeypatch.setattr(
        "agent.guardrail_helpers.guardrails.product_exists",
        lambda site_id, product_id: str(product_id) in {p["id"] for p in CATALOG},
    )
    monkeypatch.setattr(orchestrator, "_add_variant_ids_to_cart_actions", lambda site_id, actions: actions)
    monkeypatch.setattr(orchestrator, "_persist_preference_actions", lambda site_id, actions: None)
    monkeypatch.setattr(orchestrator, "_cart_context_for_site", lambda site_id, ecommerce: "")
    monkeypatch.setattr(
        orchestrator,
        "_apply_capability_filter_result",
        lambda site_id, actions: {"actions": list(actions), "removed": [], "status": "applied"},
    )
    monkeypatch.setattr(orchestrator, "lookup_answer_cache", cache.lookup)
    monkeypatch.setattr(orchestrator, "store_answer_cache", cache.store)
    monkeypatch.setattr(orchestrator, "get_all_products", lambda site_id, limit=1000: [dict(p) for p in CATALOG])
    monkeypatch.setattr(orchestrator, "get_catalog_records", lambda site_id, **kw: [dict(p) for p in CATALOG])
    monkeypatch.setattr(orchestrator, "_is_ecommerce_site", lambda site_id: True)
    monkeypatch.setattr(
        orchestrator,
        "_retrieve_context",
        lambda site_id, transcript, history, price_constraints=None: RetrievalContext(
            profile={}, price_constraints={}, products=[dict(p) for p in CATALOG]
        ),
    )
    monkeypatch.setattr(orchestrator.llm, "generate_response", fake_llm)
    return orchestrator, cache, llm_calls


def _run(orchestrator, text, *, site_id=SITE_A, session_id=SESSION_A):
    return orchestrator.run(
        site_id=site_id,
        text_input=text,
        skip_tts=True,
        session_id=session_id,
    )


def _material(result: dict) -> dict:
    return {field: result.get(field) for field in EQUIVALENT_FIELDS}


def _product_ids(result: dict) -> list[str]:
    ids: list[str] = []
    for action in result.get("ui_actions") or []:
        ids.extend(str(pid) for pid in (action.get("params") or {}).get("product_ids") or [])
    return ids


# --- Equivalence ------------------------------------------------------------


def test_replayed_answer_is_identical_to_the_computed_one(cached_pipeline):
    orchestrator, _cache, llm_calls = cached_pipeline
    question = "recommend me a good smartphone"

    uncached = _run(orchestrator, question)
    cached = _run(orchestrator, question)

    assert len(llm_calls) == 1, "the second identical turn must be served from the cache"
    assert cached["retrieval"]["cache_hit"] is True
    assert _material(cached) == _material(uncached)
    replayed_ids = _product_ids(cached)
    assert replayed_ids == _product_ids(uncached)
    assert replayed_ids, "the replayed answer must still name records"
    assert set(replayed_ids) <= {record["id"] for record in CATALOG}, (
        "a replayed answer may only name records that exist in this tenant's catalog"
    )


def test_cached_answer_keeps_the_same_actioned_record_ids(cached_pipeline):
    orchestrator, _cache, _llm = cached_pipeline
    question = "show me a phone"

    first = _run(orchestrator, question)
    second = _run(orchestrator, question)

    assert _product_ids(second) == _product_ids(first)
    assert [a["action"] for a in second["ui_actions"]] == [a["action"] for a in first["ui_actions"]]


# --- Isolation --------------------------------------------------------------


def test_another_tenant_never_reads_this_tenants_cached_answer(cached_pipeline):
    orchestrator, _cache, llm_calls = cached_pipeline
    question = "recommend me a good smartphone"

    _run(orchestrator, question, site_id=SITE_A)
    _run(orchestrator, question, site_id=SITE_B)

    assert len(llm_calls) == 2, "a cached answer must not cross a tenant boundary"


def test_another_session_never_reads_this_sessions_cached_answer(cached_pipeline):
    orchestrator, _cache, llm_calls = cached_pipeline
    question = "recommend me a good smartphone"

    _run(orchestrator, question, session_id=SESSION_A)
    _run(orchestrator, question, session_id=SESSION_B)

    assert len(llm_calls) == 2, "the cache is session scoped"


def test_a_catalog_change_invalidates_every_cached_answer(cached_pipeline):
    orchestrator, cache, llm_calls = cached_pipeline
    question = "recommend me a good smartphone"

    _run(orchestrator, question)
    _run(orchestrator, question)
    assert len(llm_calls) == 1

    cache.bump_data_version()
    _run(orchestrator, question)

    assert len(llm_calls) == 2, "a new catalog version must not be answered from the old one"


def test_a_different_budget_is_a_different_cache_identity(cached_pipeline):
    orchestrator, _cache, llm_calls = cached_pipeline

    _run(orchestrator, "show me a smartphone under 20000")
    _run(orchestrator, "show me a smartphone under 50000")

    assert len(llm_calls) == 2, "the budget is part of the answer, so it is part of the key"


# --- Turns that must never be replayed --------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "which of these is cheapest?",
        "take me to the offers page",
        "sort them by price",
        "but I said 50,000",
        "add that one to my cart",
    ],
)
def test_state_dependent_turns_neither_read_nor_write_the_cache(cached_pipeline, question):
    orchestrator, cache, _llm = cached_pipeline

    result = _run(orchestrator, question)

    assert cache.lookups == [], f"{question!r} depends on current state and must not read the cache"
    assert cache.rows == {}, f"{question!r} must not be stored for replay"
    assert result.get("response_text")
