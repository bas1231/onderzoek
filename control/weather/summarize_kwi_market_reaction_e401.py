#!/usr/bin/env python3
"""Aggregate E401 reports into a fail-closed evidence-threshold summary.

This script does not estimate profitability and cannot promote a trading
strategy. It only checks whether the preregistered minimum evidence volume,
city diversity and synchronized-capture fraction have been reached without
sample inflation or conflicting duplicate events.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

REACTION_OBSERVED = "REACTION_OBSERVED"
NO_REACTION_OBSERVED_WITHIN_WINDOW = "NO_REACTION_OBSERVED_WITHIN_WINDOW"
UNPROVEN_REACTION = "UNPROVEN_REACTION"
SUPPORTED_SCHEMA = "KAL_WX_MARKET_REACTION_E401_V2"
ECONOMIC_CONCLUSION = "NO_PROVEN_EDGE"


def _event_key(report: dict[str, Any], result: dict[str, Any]) -> tuple[str, str] | None:
    event = result.get("kwi_event")
    if not isinstance(event, dict):
        return None
    city = str(event.get("city") or report.get("city") or "").strip().lower()
    kwi_t = event.get("kwi_t")
    if not city or kwi_t is None:
        return None
    return city, str(kwi_t)


def _canonical_result(result: dict[str, Any]) -> str:
    return json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)


def _nearest_rank(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[rank - 1]


def summarize_reports(
    reports: Iterable[dict[str, Any]],
    *,
    minimum_events: int = 30,
    minimum_cities: int = 2,
    minimum_coverage_fraction: float = 0.95,
) -> dict[str, Any]:
    samples: dict[tuple[str, str], dict[str, Any]] = {}
    fingerprints: dict[tuple[str, str], str] = {}
    conflicted_keys: set[tuple[str, str]] = set()
    rejected_reports: list[dict[str, Any]] = []
    identical_duplicates = 0
    invalid_primary_results = 0

    for index, report in enumerate(reports):
        if not isinstance(report, dict):
            rejected_reports.append({"index": index, "reason": "REPORT_NOT_OBJECT"})
            continue
        if report.get("schema") != SUPPORTED_SCHEMA:
            rejected_reports.append({
                "index": index,
                "schema": report.get("schema"),
                "reason": "UNSUPPORTED_OR_LEGACY_SCHEMA",
            })
            continue
        results = report.get("results")
        declared = report.get("primary_events_total")
        if not isinstance(results, list) or not isinstance(declared, int) or declared != len(results):
            rejected_reports.append({
                "index": index,
                "reason": "PRIMARY_RESULT_COUNT_MISMATCH",
                "declared": declared,
                "actual": len(results) if isinstance(results, list) else None,
            })
            continue

        for result in results:
            if not isinstance(result, dict):
                invalid_primary_results += 1
                continue
            key = _event_key(report, result)
            status = result.get("status")
            if key is None or status not in {
                REACTION_OBSERVED,
                NO_REACTION_OBSERVED_WITHIN_WINDOW,
                UNPROVEN_REACTION,
            }:
                invalid_primary_results += 1
                continue
            if status == REACTION_OBSERVED:
                latency = result.get("latency_ms")
                if not isinstance(latency, (int, float)) or isinstance(latency, bool) or latency < 0:
                    invalid_primary_results += 1
                    continue

            fingerprint = _canonical_result(result)
            if key in conflicted_keys:
                continue
            if key in samples:
                if fingerprints[key] == fingerprint:
                    identical_duplicates += 1
                    continue
                conflicted_keys.add(key)
                samples.pop(key, None)
                fingerprints.pop(key, None)
                continue
            samples[key] = result
            fingerprints[key] = fingerprint

    unique_primary_total = len(samples)
    evaluable = {
        key: result for key, result in samples.items()
        if result.get("status") in {REACTION_OBSERVED, NO_REACTION_OBSERVED_WITHIN_WINDOW}
    }
    unproven = {
        key: result for key, result in samples.items()
        if result.get("status") == UNPROVEN_REACTION
    }
    evaluable_count = len(evaluable)
    coverage_fraction = (evaluable_count / unique_primary_total) if unique_primary_total else 0.0
    evaluable_cities = sorted({key[0] for key in evaluable})

    reaction_latencies = [
        float(result["latency_ms"])
        for result in evaluable.values()
        if result.get("status") == REACTION_OBSERVED
    ]
    reaction_count = len(reaction_latencies)
    no_reaction_count = sum(
        1 for result in evaluable.values()
        if result.get("status") == NO_REACTION_OBSERVED_WITHIN_WINDOW
    )

    dataset_integrity_pass = not conflicted_keys and invalid_primary_results == 0
    event_threshold_pass = unique_primary_total >= minimum_events
    city_threshold_pass = len(evaluable_cities) >= minimum_cities
    coverage_threshold_pass = coverage_fraction >= minimum_coverage_fraction
    minimum_evidence_met = bool(
        dataset_integrity_pass
        and event_threshold_pass
        and city_threshold_pass
        and coverage_threshold_pass
    )

    return {
        "schema": "KAL_WX_MARKET_REACTION_E401_SUMMARY_V1",
        "supported_input_schema": SUPPORTED_SCHEMA,
        "unique_primary_events": unique_primary_total,
        "evaluable_primary_events": evaluable_count,
        "unproven_primary_events": len(unproven),
        "evaluable_cities": evaluable_cities,
        "evaluable_city_count": len(evaluable_cities),
        "valid_synchronized_capture_fraction": coverage_fraction,
        "reaction_observed_count": reaction_count,
        "no_reaction_observed_count": no_reaction_count,
        "reaction_latency_ms": {
            "p50_nearest_rank": _nearest_rank(reaction_latencies, 0.50),
            "p95_nearest_rank": _nearest_rank(reaction_latencies, 0.95),
            "min": min(reaction_latencies) if reaction_latencies else None,
            "max": max(reaction_latencies) if reaction_latencies else None,
        },
        "identical_duplicate_events_deduplicated": identical_duplicates,
        "conflicting_duplicate_event_keys": [list(key) for key in sorted(conflicted_keys)],
        "invalid_primary_results": invalid_primary_results,
        "rejected_reports": rejected_reports,
        "thresholds": {
            "minimum_events": minimum_events,
            "minimum_cities": minimum_cities,
            "minimum_coverage_fraction": minimum_coverage_fraction,
        },
        "checks": {
            "dataset_integrity_pass": dataset_integrity_pass,
            "event_threshold_pass": event_threshold_pass,
            "city_threshold_pass": city_threshold_pass,
            "coverage_threshold_pass": coverage_threshold_pass,
        },
        "minimum_evidence_met": minimum_evidence_met,
        "next_gate": "KAL-WX-ORDER-ARRIVAL-E402" if minimum_evidence_met else None,
        "economic_conclusion": ECONOMIC_CONCLUSION,
        "guards": [
            "minimum_evidence_met is not evidence of profitability or market edge",
            "legacy V1 reports are rejected because they may mix revisions into the primary sample",
            "duplicate city x target-minute events never increase sample size",
            "conflicting duplicates fail dataset integrity",
            "UNPROVEN_REACTION counts against synchronized-capture coverage",
        ],
    }


def _load_report_paths(paths: list[Path], report_dir: Path | None) -> list[dict[str, Any]]:
    files = list(paths)
    if report_dir is not None:
        files.extend(sorted(report_dir.glob("*.json")))
    reports = []
    for path in files:
        reports.append(json.loads(path.read_text(encoding="utf-8")))
    return reports


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, action="append", default=[])
    ap.add_argument("--report-dir", type=Path)
    ap.add_argument("--minimum-events", type=int, default=30)
    ap.add_argument("--minimum-cities", type=int, default=2)
    ap.add_argument("--minimum-coverage-fraction", type=float, default=0.95)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if not args.report and args.report_dir is None:
        raise SystemExit("at least one --report or --report-dir is required")
    reports = _load_report_paths(args.report, args.report_dir)
    summary = summarize_reports(
        reports,
        minimum_events=args.minimum_events,
        minimum_cities=args.minimum_cities,
        minimum_coverage_fraction=args.minimum_coverage_fraction,
    )
    text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
