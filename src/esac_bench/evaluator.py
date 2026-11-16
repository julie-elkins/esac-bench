"""Deterministic contract evaluator used by native and mutation runs."""

from __future__ import annotations

from collections import Counter

from .models import TaskContract, TaskResult


def evaluate_result(task: TaskContract, result: TaskResult) -> TaskResult:
    """Recompute assurance dimensions from observable metadata.

    The evaluator does not trust the dimensions supplied by a reference profile.
    That separation is what lets mutation controls test the evaluator itself.
    """

    expected_effects = Counter(task.expected_effects)
    observed_effects = Counter(result.observed_effects)
    recovery_safety = (
        "pass"
        if observed_effects == expected_effects
        else "fail"
    )
    evidence_completeness = (
        "pass"
        if set(task.required_evidence).issubset(set(result.observed_evidence))
        else "fail"
    )
    outcome = (
        "pass"
        if set(task.outcome_evidence).issubset(set(result.observed_evidence))
        and all(
            expected_effects[effect] <= observed_effects[effect]
            for effect in expected_effects
        )
        else "fail"
    )
    claim_support = (
        "pass"
        if (
            result.claim == "completed"
            and outcome == "pass"
            and recovery_safety == "pass"
            and evidence_completeness == "pass"
        )
        else "fail"
    )
    return TaskResult(
        task_id=result.task_id,
        profile=result.profile,
        scenario=result.scenario,
        dimensions={
            "outcome": outcome,
            "recovery_safety": recovery_safety,
            "evidence_completeness": evidence_completeness,
            "claim_support": claim_support,
        },
        observed_evidence=result.observed_evidence,
        observed_effects=result.observed_effects,
        claim=result.claim,
        limitation=result.limitation,
    )

