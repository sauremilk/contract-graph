"""Precision / Recall eval runner for the mapping layer.

This script measures how accurately the drift_contract_graph mapping layer
preserves contract-graph findings as drift Findings.

Metrics (OpenAI Eval-First philosophy):
  Precision = TP / (TP + FP) — how many mapped findings are correct?
  Recall    = TP / (TP + FN) — how many expected findings were captured?

Gating thresholds (from copilot-instructions.md):
  Precision ≥ 90%  (goal: 95%)
  Recall    ≥ 80%  (goal: 90%)
  FP Rate   < 10%

The eval reads ``cases.jsonl`` which contains labelled test cases.
Each case declares what findings are expected for a given input shape.
The eval runner materialises synthetic contract-graph JSON, runs the
mapping, and compares against expectations.

Usage:
    python eval_runner.py              # prints metrics, exits 0 if passing
    python eval_runner.py --baseline   # writes/updates results/baseline.json
    python eval_runner.py --compare    # compares against baseline, fails on regression
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CASES_PATH = Path(__file__).parent / "cases.jsonl"
BASELINE_PATH = Path(__file__).parent / "results" / "baseline.json"

# Gating thresholds
MIN_PRECISION = 0.90
MIN_RECALL = 0.80


def _synthetic_report(case: dict) -> dict:
    """Build a minimal contract-graph JSON report from an eval case."""
    inp = case["input"]
    expected = case["expected_findings"]

    findings = []
    for exp in expected:
        findings.append(
            {
                "finding_id": f"CG-eval{len(findings):06d}",
                "discoverer": "api_type_sync",
                "severity": "high",
                "title": f"Field {exp.get('field_name', '?')} drift ({exp.get('mismatch_kind', '?')})",
                "description": "Synthetic eval finding.",
                "provider_file": inp.get("provider_file", ""),
                "provider_name": inp.get("provider_name", ""),
                "provider_line": 1,
                "consumer_file": inp.get("consumer_file", ""),
                "consumer_name": inp.get("consumer_name", ""),
                "consumer_line": 1,
                "field_name": exp.get("field_name", ""),
                "mismatch_kind": exp.get("mismatch_kind", ""),
                "fix_suggestion": "",
            }
        )
    return {
        "tool": "contract-graph",
        "version": "1.1.1",
        "schema_version": "1.1",
        "findings": findings,
        "summary": {},
    }


def _run_eval() -> dict:
    """Run all cases and return metrics."""
    from drift_contract_graph.mapping import map_findings

    cases = [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    tp = fp = fn = 0

    for case in cases:
        report = _synthetic_report(case)
        mapped = map_findings(report)
        expected = case["expected_findings"]

        # Each expected finding must appear in mapped (field_name + mismatch_kind match).
        expected_keys = {(e["field_name"], e["mismatch_kind"]) for e in expected}
        mapped_keys = {
            (
                f.metadata["contract_graph"]["field_name"],
                f.metadata["contract_graph"]["mismatch_kind"],
            )
            for f in mapped
        }

        case_tp = len(expected_keys & mapped_keys)
        case_fp = len(mapped_keys - expected_keys)
        case_fn = len(expected_keys - mapped_keys)

        tp += case_tp
        fp += case_fp
        fn += case_fn

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    fp_rate = fp / (tp + fp) if (tp + fp) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "fp_rate": round(fp_rate, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "total_cases": len(cases),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true", help="Write results to baseline.json")
    parser.add_argument(
        "--compare", action="store_true", help="Compare to baseline and fail on regression"
    )
    args = parser.parse_args()

    results = _run_eval()

    print(f"Precision : {results['precision']:.1%}  (min {MIN_PRECISION:.0%})")
    print(f"Recall    : {results['recall']:.1%}  (min {MIN_RECALL:.0%})")
    print(f"FP Rate   : {results['fp_rate']:.1%}")
    print(
        f"TP/FP/FN  : {results['tp']}/{results['fp']}/{results['fn']}  ({results['total_cases']} cases)"
    )

    if args.baseline:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nBaseline written to {BASELINE_PATH}")

    if args.compare and BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        regressions = []
        for metric in ("precision", "recall"):
            delta = results[metric] - baseline[metric]
            if delta < -0.02:  # > 2% regression triggers failure
                regressions.append(
                    f"{metric}: {baseline[metric]:.1%} → {results[metric]:.1%} (delta {delta:+.1%})"
                )
        if regressions:
            print("\nREGRESSIONS DETECTED:")
            for r in regressions:
                print(f"  {r}")
            sys.exit(1)

    # Gate check
    failed = []
    if results["precision"] < MIN_PRECISION:
        failed.append(f"Precision {results['precision']:.1%} < {MIN_PRECISION:.0%}")
    if results["recall"] < MIN_RECALL:
        failed.append(f"Recall {results['recall']:.1%} < {MIN_RECALL:.0%}")
    if failed:
        print("\nFAILED GATES:")
        for f in failed:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("\nAll gates passed.")


if __name__ == "__main__":
    main()
