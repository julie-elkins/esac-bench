"""Evaluate metadata-only Harbor receipts without importing raw agent content.

The evaluator has four deliberate rules:

1. accept only the declared Harbor receipt schema and metadata keys;
2. require clean execution before interpreting benchmark status;
3. require validated trajectory metadata before supporting a native outcome;
4. return a structured refusal instead of raising on unsafe or ambiguous input.

It does not read provider logs, prompts, tool arguments, or trajectories.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from typing import Any


EVALUATOR_VERSION = "esac-harbor-receipt-eval-v0"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "prompt",
        "tool_payload",
        "tool_arguments",
        "provider_response",
        "trajectory",
        "raw_trace",
        "credential",
        "events",
        "steps",
    }
)
_ALLOWED_KEYS = frozenset(
    {
        "agent",
        "agent_event_count",
        "agent_last_event_type",
        "agent_last_item_type",
        "agent_last_status",
        "agent_log_digest",
        "agent_revision",
        "agent_terminal_event_type",
        "agent_tool_call_count",
        "agent_trace_status",
        "assurance_source",
        "assurance_status",
        "atif_scan_status",
        "atif_schema_version",
        "atif_step_count",
        "atif_tool_call_count",
        "attempts",
        "benchmark",
        "benchmark_failure_kind",
        "benchmark_failure_phase",
        "benchmark_revision",
        "benchmark_score",
        "benchmark_status",
        "command_digest",
        "elapsed_seconds",
        "estimated_cost_usd",
        "failure_breakdown",
        "failure_kind",
        "failure_phase",
        "harness",
        "harness_revision",
        "max_total_cost_usd",
        "model",
        "observed_cost_usd",
        "output_capped",
        "provider",
        "returncode",
        "run_id",
        "runner_completed_trials",
        "runner_errored_trials",
        "runner_result_status",
        "runner_successful_trials",
        "runner_total_trials",
        "schema_version",
        "status",
        "stop_condition",
        "task_count",
        "timed_out",
        "trajectory_digest",
        "trajectory_store",
    }
)
_REQUIRED_KEYS = frozenset(
    {
        "benchmark_status",
        "output_capped",
        "returncode",
        "runner_completed_trials",
        "runner_errored_trials",
        "runner_result_status",
        "runner_successful_trials",
        "runner_total_trials",
        "schema_version",
        "status",
        "task_count",
        "timed_out",
        "trajectory_digest",
    }
)


@dataclass(frozen=True)
class ReceiptEvaluationRefusal:
    """A receipt that cannot be safely interpreted."""

    error: str
    message: str
    guidance: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class HarborReceiptEvaluation:
    """A metadata-only native outcome derived from one Harbor receipt."""

    evaluator_version: str
    source_schema_version: str
    run_id: str | None
    task_count: int | None
    execution_status: str
    benchmark_status: str
    native_outcome: str
    evidence_status: str
    trajectory_status: str
    benchmark_score: float | None
    observed_cost_usd: float | None
    limitation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, child in value.items():
            keys.add(str(key))
            keys.update(_walk_keys(child))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys.update(_walk_keys(child))
        return keys
    return set()


def _refusal(error: str, message: str, guidance: str) -> ReceiptEvaluationRefusal:
    return ReceiptEvaluationRefusal(error, message, guidance)


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and bool(_DIGEST_PATTERN.fullmatch(value))


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _validated_evidence(receipt: dict[str, Any]) -> tuple[str, str]:
    trajectory_digest = receipt.get("trajectory_digest")
    trajectory_present = _is_digest(trajectory_digest)
    atif_checked = (
        receipt.get("assurance_source") == "atif"
        and receipt.get("assurance_status") == "metadata-checked"
        and receipt.get("atif_scan_status") == "passed"
        and isinstance(receipt.get("atif_schema_version"), str)
        and receipt["atif_schema_version"].startswith("ATIF-")
    )
    if trajectory_present and atif_checked:
        return "complete", "present"
    if trajectory_digest is None:
        return "incomplete", "absent"
    return "incomplete", "unknown"


def _execution_status(receipt: dict[str, Any]) -> str:
    if receipt.get("status") == "refused":
        return "refused"
    if receipt.get("status") == "timed_out" or receipt.get("timed_out") is True:
        return "timed_out"
    if (
        receipt.get("status") == "completed"
        and receipt.get("returncode") == 0
        and receipt.get("runner_result_status") == "completed"
        and receipt.get("runner_total_trials")
        == receipt.get("runner_completed_trials")
        and receipt.get("runner_errored_trials") == 0
        and receipt.get("runner_successful_trials")
        == receipt.get("runner_completed_trials")
        and receipt.get("output_capped") is False
    ):
        return "completed"
    if receipt.get("status") == "failed" or receipt.get("returncode") not in (None, 0):
        return "failed"
    return "unknown"


def _benchmark_score(receipt: dict[str, Any]) -> float | None:
    value = receipt.get("benchmark_score")
    return float(value) if _finite_number(value) else None


def _observed_cost(receipt: dict[str, Any]) -> float | None:
    value = receipt.get("observed_cost_usd")
    return float(value) if _finite_number(value) and value >= 0 else None


def evaluate_harbor_receipt(
    receipt: dict[str, Any],
) -> HarborReceiptEvaluation | ReceiptEvaluationRefusal:
    """Safely normalize one metadata-only Harbor receipt."""

    if not isinstance(receipt, dict):
        return _refusal(
            "receipt_not_object",
            "The Harbor receipt must be a JSON object.",
            "Provide the metadata-only receipt object.",
        )
    forbidden = _walk_keys(receipt) & _FORBIDDEN_KEYS
    if forbidden:
        return _refusal(
            "forbidden_receipt_content",
            "The Harbor receipt contains raw or provider-private content.",
            "Provide metadata-only fields and remove raw content.",
        )
    unknown = set(receipt) - _ALLOWED_KEYS
    if unknown:
        return _refusal(
            "unknown_receipt_fields",
            "The Harbor receipt contains fields outside the reviewed metadata contract.",
            "Review the receipt schema before adding new fields.",
        )
    if receipt.get("schema_version") != "receipt-v1":
        return _refusal(
            "receipt_schema_unsupported",
            "The Harbor receipt schema is not supported.",
            "Provide a receipt-v1 metadata-only Harbor receipt.",
        )
    missing = sorted(_REQUIRED_KEYS - set(receipt))
    if missing:
        return _refusal(
            "receipt_fields_missing",
            "The Harbor receipt is missing required metadata.",
            f"Provide the required fields: {', '.join(missing)}.",
        )
    if not isinstance(receipt["task_count"], int) or receipt["task_count"] < 1:
        return _refusal(
            "task_count_invalid",
            "The Harbor receipt task count is invalid.",
            "Use a positive integer task count.",
        )
    if not isinstance(receipt["runner_result_status"], str):
        return _refusal(
            "runner_status_invalid",
            "The Harbor runner status is invalid.",
            "Provide the runner's metadata status as a string.",
        )
    if not isinstance(receipt["status"], str):
        return _refusal(
            "status_invalid",
            "The Harbor receipt status is invalid.",
            "Provide the adapter status as a string.",
        )
    if not isinstance(receipt["benchmark_status"], str):
        return _refusal(
            "benchmark_status_invalid",
            "The Harbor benchmark status is invalid.",
            "Provide the benchmark status as a string.",
        )
    if not isinstance(receipt["timed_out"], bool) or not isinstance(
        receipt["output_capped"], bool
    ):
        return _refusal(
            "execution_flags_invalid",
            "The Harbor execution flags are invalid.",
            "Provide boolean timed_out and output_capped metadata.",
        )
    counter_fields = (
        "runner_completed_trials",
        "runner_errored_trials",
        "runner_successful_trials",
        "runner_total_trials",
    )
    if any(
        not isinstance(receipt[field], int) or isinstance(receipt[field], bool)
        for field in counter_fields
    ):
        return _refusal(
            "trial_counts_invalid",
            "The Harbor trial counts are invalid.",
            "Provide non-negative integer trial counts.",
        )
    if receipt["returncode"] not in (None, 0) and not isinstance(receipt["returncode"], int):
        return _refusal(
            "returncode_invalid",
            "The Harbor return code is invalid.",
            "Provide an integer return code or null.",
        )
    evidence_status, trajectory_status = _validated_evidence(receipt)
    execution_status = _execution_status(receipt)
    benchmark_status = receipt["benchmark_status"]
    if execution_status == "completed" and benchmark_status == "passed":
        native_outcome = "pass" if evidence_status == "complete" else "unknown"
        limitation = (
            None
            if native_outcome == "pass"
            else "Benchmark passed, but required evidence metadata was incomplete."
        )
    elif execution_status == "completed" and benchmark_status == "failed":
        native_outcome = "fail" if evidence_status == "complete" else "unknown"
        limitation = (
            None
            if native_outcome == "fail"
            else "Benchmark failed, but required evidence metadata was incomplete."
        )
    else:
        native_outcome = "not_observed"
        limitation = "No clean benchmark outcome was observed."
    return HarborReceiptEvaluation(
        evaluator_version=EVALUATOR_VERSION,
        source_schema_version=receipt["schema_version"],
        run_id=receipt.get("run_id"),
        task_count=receipt["task_count"],
        execution_status=execution_status,
        benchmark_status=benchmark_status,
        native_outcome=native_outcome,
        evidence_status=evidence_status,
        trajectory_status=trajectory_status,
        benchmark_score=_benchmark_score(receipt),
        observed_cost_usd=_observed_cost(receipt),
        limitation=limitation,
    )


def receipt_digest(receipt: dict[str, Any]) -> str:
    """Digest metadata for local audit without retaining receipt contents."""

    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
