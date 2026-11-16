"""Offline suite runner with separate assurance dimensions."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .evaluator import evaluate_result
from .models import DIMENSIONS, digest_metadata
from .mutations import run_mutations
from .schema import SCHEMA_VERSION, validate_native_report
from .tasks import TASKS, reference_result


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, dict[str, int]] = {}
    for dimension in DIMENSIONS:
        counts[dimension] = dict(
            Counter(result["dimensions"][dimension] for result in results)
        )
    return counts


def run_suite() -> dict[str, Any]:
    """Run deterministic guarded and naive controls without provider calls."""

    reference_results = [
        evaluate_result(task, reference_result(task, profile))
        for profile in ("guarded", "naive")
        for task in TASKS
    ]
    results = [result.to_dict() for result in reference_results]
    guarded = {
        result.task_id: result
        for result in reference_results
        if result.profile == "guarded"
    }
    mutation_results = run_mutations(TASKS, guarded)
    report: dict[str, Any] = {
        "benchmark": "ESAC-Bench",
        "schema_version": SCHEMA_VERSION,
        "protocol": "esac-offline-v0",
        "data_class": "synthetic",
        "task_count": len(TASKS),
        "task_contract_ids": [task.task_id for task in TASKS],
        "task_contract_digest": digest_metadata(
            [
                {
                    "task_id": task.task_id,
                    "task_family": task.task_family,
                    "required_evidence": task.required_evidence,
                    "outcome_evidence": task.outcome_evidence,
                    "expected_effects": task.expected_effects,
                }
                for task in TASKS
            ]
        ),
        "profiles": ["guarded", "naive"],
        "dimensions": list(DIMENSIONS),
        "results": results,
        "mutation_results": mutation_results,
        "mutation_suite_status": (
            "passed"
            if all(item["detected"] for item in mutation_results)
            else "failed"
        ),
        "summaries": {
            profile: _summarize(
                [result for result in results if result["profile"] == profile]
            )
            for profile in ("guarded", "naive")
        },
        "limitations": [
            "Reference profiles are evaluator controls, not model scores.",
            "No provider API or live environment was used.",
            "No composite score is reported.",
        ],
    }
    report["report_digest"] = digest_metadata(
        {key: value for key, value in report.items() if key != "report_digest"}
    )
    report["schema_errors"] = validate_native_report(report)
    if report["schema_errors"]:
        raise ValueError("native_report_invalid")
    return report

