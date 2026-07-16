"""Regression tests for hybrid-retrieval SQL parameter ordering."""

from __future__ import annotations

from typing import Any

from agent.retrieval import generic_rag, product_rag


class _Cursor:
    def fetchall(self) -> list[dict[str, Any]]:
        return []


class _Connection:
    def __init__(self) -> None:
        self.params: list[Any] = []

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def execute(self, _query: str, params: list[Any]) -> _Cursor:
        self.params = params
        return _Cursor()


def test_product_fts_places_price_parameters_after_both_tsqueries(monkeypatch) -> None:
    connection = _Connection()
    monkeypatch.setattr(product_rag, "get_db", lambda _site_id: connection)

    product_rag._lexical_product_search(
        "iphone",
        "site_1",
        " AND p.price <= %s",
        [80000.0],
        30,
    )

    assert connection.params == ["iphone:*", "iphone:*", 80000.0, 30]


def test_knowledge_fts_places_entity_filter_after_both_tsqueries(monkeypatch) -> None:
    connection = _Connection()
    monkeypatch.setattr(generic_rag, "get_db", lambda _site_id: connection)

    generic_rag._fts_knowledge_search("health plan", "site_1", ["plans"], 12)

    assert connection.params == [
        "health:* | plan:*",
        "health:* | plan:*",
        ["plans"],
        12,
    ]


def test_knowledge_fuzzy_places_entity_filter_after_threshold(monkeypatch) -> None:
    connection = _Connection()
    monkeypatch.setattr(generic_rag, "get_db", lambda _site_id: connection)

    generic_rag._fuzzy_knowledge_search("health plan", "site_1", ["plans"], 12)

    assert connection.params == ["health plan", "health plan", 0.15, ["plans"], "health plan", 12]
