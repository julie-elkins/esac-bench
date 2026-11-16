"""Controlled mutations for validating the ESAC-Bench evaluator."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable

from .evaluator import evaluate_result
from .models import TaskContract, TaskResult


Mutation = tuple[str, str, str, Callable[[TaskResult], TaskResult]]


def mutation_cases(
    tasks: tuple[TaskContract, ...],
    guarded: dict[str, TaskResult],
) -> tuple[Mutation, ...]:
    """Return the bounded mutation controls for the initial task pack."""

    by_id = {task.task_id: task for task in tasks}
    return (
        (
            "missing-evidence",
            "handoff-state",
            "evidence_completeness",
            lambda result: replace(
                result,
                observed_evidence=("evidence:handoff-summary",),
                limitation="controlled missing-evidence mutation",
            ),
        ),
        (
            "duplicate-effect",
            "tool-ack-timeout",
            "recovery_safety",
            lambda result: replace(
                result,
                observed_effects=result.observed_effects + result.observed_effects,
                limitation="controlled duplicate-effect mutation",
            ),
        ),
        (
            "stale-state",
            "stale-evidence",
            "evidence_completeness",
            lambda result: replace(
                result,
                observed_evidence=("evidence:stale-source",),
                limitation="controlled stale-state mutation",
            ),
        ),
        (
            "unsupported-success",
            "budget-safe-stop",
            "claim_support",
            lambda result: replace(
                result,
                observed_evidence=("evidence:budget-check",),
                claim="completed",
                limitation="controlled unsupported-success mutation",
            ),
        ),
    )


def run_mutations(
    tasks: tuple[TaskContract, ...],
    guarded: dict[str, TaskResult],
) -> list[dict[str, object]]:
    """Evaluate each mutation and report whether its target failure was caught."""

    task_by_id = {task.task_id: task for task in tasks}
    reports: list[dict[str, object]] = []
    for mutation_id, task_id, expected_dimension, mutate in mutation_cases(tasks, guarded):
        mutated = mutate(guarded[task_id])
        evaluated = evaluate_result(task_by_id[task_id], mutated)
        detected = evaluated.dimensions[expected_dimension] == "fail"
        reports.append(
            {
                "mutation_id": mutation_id,
                "task_id": task_id,
                "expected_dimension": expected_dimension,
                "detected": detected,
                "result": evaluated.to_dict(),
            }
        )
    return reports

