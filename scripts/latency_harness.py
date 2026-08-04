"""Repeatable latency harness for the conversational turn.

Every previous latency claim in this project was an estimate. This harness
measures, and labels what it measured, so a number can never be quoted without
the conditions attached to it.

What is measured, per stage:

    plan_ms         resolving the authoritative TurnPlan for the turn
    cache_ms        the answer-cache lookup
    retrieval_ms    catalog scan + hard filtering + ranking/selection
    first_text_ms   when the customer would first see a textual answer
    action_ms       building and grounding the UI actions for the turn
    total_ms        the whole turn

What is NOT measured, and is reported as such: real Azure speech-to-text, model,
and text-to-speech time. This harness runs against fixture data with the
providers stubbed, so its numbers describe the deterministic decision layer on
this machine. They are a floor, not a production figure, and the report says so.

Usage
    python scripts/latency_harness.py                 # 30 samples, warm + cold
    python scripts/latency_harness.py --samples 100
    python scripts/latency_harness.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.catalog import catalog_operations as ops  # noqa: E402
from agent.orchestration.turn_plan import build_turn_plan  # noqa: E402
from db.cache.answer_cache import normalize_question  # noqa: E402

DEFAULT_SAMPLES = 30
WARMUP_SAMPLES = 3
CATALOG_SIZE = 2000
PERCENTILES = (50, 95)

# Representative turns, one per shape the pipeline answers differently.
WORKLOAD = [
    ("browse", "I'm looking for a Corvi smartphone"),
    ("budgeted_search", "show me a smartphone under 50000"),
    ("aggregate_cheapest", "what is the cheapest item in Fashion Women?"),
    ("aggregate_best_rated", "which item has the best rating?"),
    ("inventory_count", "how many smartphones do you have?"),
    ("correction", "but I said 50,000"),
    ("page_question", "which of these results is cheapest?"),
    ("navigation", "take me to the offers page"),
]

CATEGORIES = ("Electronics", "Fashion Women", "Home Kitchen", "Sports")
BRANDS = ("aster", "borel", "corvi", "delta")


def synthetic_catalog(size: int = CATALOG_SIZE) -> list[dict[str, Any]]:
    """A deterministic catalog: same input, same timings, run after run."""
    records = []
    for index in range(size):
        brand = BRANDS[index % len(BRANDS)]
        records.append({
            "id": f"r{index}",
            "name": f"{brand.title()} Smartphone Model {index}",
            "brand": brand.title(),
            "category_name": CATEGORIES[index % len(CATEGORIES)],
            "price": float(199 + (index * 37) % 90000),
            "rating": round(3.0 + (index % 20) / 10.0, 1),
            "review_count": index % 250,
            "stock": (index % 7) + 1,
            "variant_id": 100000 + index,
        })
    return records


@dataclass
class StageTimings:
    samples: dict[str, list[float]] = field(default_factory=dict)

    def record(self, stage: str, milliseconds: float) -> None:
        self.samples.setdefault(stage, []).append(milliseconds)

    def percentiles(self) -> dict[str, dict[str, float]]:
        report: dict[str, dict[str, float]] = {}
        for stage, values in sorted(self.samples.items()):
            ordered = sorted(values)
            report[stage] = {
                "samples": len(ordered),
                "min_ms": round(ordered[0], 3),
                "max_ms": round(ordered[-1], 3),
                "mean_ms": round(statistics.fmean(ordered), 3),
                **{f"p{p}_ms": round(_percentile(ordered, p), 3) for p in PERCENTILES},
            }
        return report


def _percentile(ordered: list[float], percentile: int) -> float:
    if not ordered:
        return 0.0
    position = (percentile / 100) * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    started = time.perf_counter()
    value = fn()
    return value, (time.perf_counter() - started) * 1000


def measure_turn(
    utterance: str,
    catalog: list[dict[str, Any]],
    cache: dict[str, Any],
    timings: StageTimings,
) -> None:
    """One turn through the deterministic decision layer, stage by stage."""
    turn_started = time.perf_counter()

    plan, plan_ms = _timed(lambda: build_turn_plan(
        utterance, site_id="latency_site", catalog_brands=BRANDS, catalog_types=("smartphone", "kurta", "bottle")
    ))
    timings.record("plan_ms", plan_ms)

    signature = plan.cache_key_component() if plan.cache_eligible else ""
    _, cache_ms = _timed(lambda: cache.get(normalize_question(utterance, signature)))
    timings.record("cache_ms", cache_ms)

    def retrieve():
        categories = ops.matching_category_names(plan.constraints.raw_query, catalog)
        selection = ops.select_records(catalog, plan.constraints, category_names=categories)
        return ops.aggregate_records(selection, plan.aggregate, limit=1) if plan.aggregate else selection

    result, retrieval_ms = _timed(retrieve)
    timings.record("retrieval_ms", retrieval_ms)

    _, action_ms = _timed(lambda: _build_actions(result))
    timings.record("action_ms", action_ms)

    timings.record("first_text_ms", (time.perf_counter() - turn_started) * 1000)
    timings.record("total_ms", (time.perf_counter() - turn_started) * 1000)


def _build_actions(result: Any) -> list[dict[str, Any]]:
    records = result if isinstance(result, list) else list(getattr(result, "records", ()))[:8]
    ids = [str(record.get("id")) for record in records if record.get("id")]
    return [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ids}}] if ids else []


def run(samples: int) -> dict[str, Any]:
    catalog = synthetic_catalog()
    cold = StageTimings()
    warm = StageTimings()
    cache: dict[str, Any] = {}

    # Cold: first touch of every code path, imports and regexes not yet exercised.
    for _index in range(WARMUP_SAMPLES):
        for _label, utterance in WORKLOAD:
            measure_turn(utterance, catalog, cache, cold)

    # Warm: steady state, which is what a live session actually experiences.
    for _index in range(samples):
        for _label, utterance in WORKLOAD:
            measure_turn(utterance, catalog, cache, warm)

    return {
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "catalog_records": len(catalog),
            "workload_turns": len(WORKLOAD),
        },
        "conditions": {
            "providers": "stubbed - no speech-to-text, model, or text-to-speech call is made",
            "database": "not used - the catalog is an in-process fixture",
            "cache_state": "cold run populates nothing; warm run reuses the same in-process dict",
            "honesty_note": (
                "These figures describe the deterministic decision layer on this machine only. "
                "They are a floor for end-to-end latency and must not be quoted as Azure or "
                "public-server performance."
            ),
        },
        "cold": {"samples_per_turn": WARMUP_SAMPLES, "stages": cold.percentiles()},
        "warm": {"samples_per_turn": samples, "stages": warm.percentiles()},
    }


def render(report: dict[str, Any]) -> str:
    lines = [
        "# Latency report (deterministic decision layer, providers stubbed)",
        "",
        f"Catalog records: {report['environment']['catalog_records']} | "
        f"Turn shapes: {report['environment']['workload_turns']} | "
        f"Python {report['environment']['python']} on {report['environment']['platform']}",
        "",
        report["conditions"]["honesty_note"],
        "",
    ]
    for state in ("cold", "warm"):
        block = report[state]
        lines.append(f"## {state} ({block['samples_per_turn']} samples per turn shape)")
        lines.append("")
        lines.append("| stage | samples | p50 ms | p95 ms | mean ms | max ms |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for stage, values in block["stages"].items():
            lines.append(
                f"| {stage} | {values['samples']} | {values['p50_ms']} | "
                f"{values['p95_ms']} | {values['mean_ms']} | {values['max_ms']} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--json", type=str, default="")
    args = parser.parse_args()

    report = run(max(1, args.samples))
    print(render(report))
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
