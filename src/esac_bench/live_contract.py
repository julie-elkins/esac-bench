"""Design-time contract for bounded live-agent adapters.

The contract keeps the adapter boundary narrow:

1. validate a bounded request before any provider call;
2. run one provider-specific worker behind that request;
3. return metadata-only evidence or a structured refusal;
4. leave raw trajectories in the local run workspace.

This module does not execute a provider. It is the contract that a later
adapter must satisfy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import re
from typing import Any


ADAPTER_CONTRACT_VERSION = "esac-live-adapter-v0"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_CREDENTIAL_ENV_VARS = frozenset({"ANTHROPIC_API_KEY", "OPENAI_API_KEY"})
_EXECUTION_MODES = frozenset({"dry_run", "live"})
_STATUSES = frozenset({"completed", "failed", "refused", "timed_out", "unknown"})
_CLAIMS = frozenset({"completed", "failed", "unknown"})
_NATIVE_OUTCOMES = frozenset({"pass", "fail", "unknown", "not_observed"})
_EVIDENCE_STATUSES = frozenset({"complete", "incomplete", "unknown"})
_TRAJECTORY_STATUSES = frozenset({"present", "absent", "unknown"})


@dataclass(frozen=True)
class AdapterRefusal:
    """A refusal is a result, not an exception or a passing observation."""

    error: str
    message: str
    guidance: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class AdapterRequest:
    """The bounded, provider-neutral input to one adapter execution."""

    run_id: str
    adapter_id: str
    provider: str
    model: str
    task_id: str
    execution_mode: str
    credential_env_var: str | None
    max_runtime_seconds: float
    max_attempts: int
    output_cap_bytes: int
    spend_ceiling_usd: float
    stop_condition: str
    tool_scope: tuple[str, ...]
    task_contract_digest: str
    evidence_contract_digest: str
    human_approval: bool


@dataclass(frozen=True)
class AdapterResult:
    """Metadata-only result returned by a future live adapter."""

    contract_version: str
    run_id: str
    adapter_id: str
    provider: str
    model: str
    task_id: str
    status: str
    claim: str
    native_outcome: str
    evidence_status: str
    trajectory_status: str
    returncode: int | None
    elapsed_seconds: float
    observed_cost_usd: float | None
    receipt_digest: str | None
    limitation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_identifier(value: str) -> bool:
    return bool(_IDENTIFIER_PATTERN.fullmatch(value))


def _is_digest(value: str) -> bool:
    return bool(_DIGEST_PATTERN.fullmatch(value))


def _invalid(field: str, guidance: str) -> AdapterRefusal:
    return AdapterRefusal(
        error=f"invalid_{field}",
        message=f"Adapter request field '{field}' is invalid.",
        guidance=guidance,
    )


def validate_request(request: AdapterRequest) -> AdapterRefusal | None:
    """Validate the request before any provider credential is read."""

    for field in (
        "run_id",
        "adapter_id",
        "provider",
        "model",
        "task_id",
    ):
        if not _is_identifier(getattr(request, field)):
            return _invalid(field, "Use a lowercase identifier with bounded length.")

    if request.execution_mode not in _EXECUTION_MODES:
        return _invalid("execution_mode", "Choose 'dry_run' or 'live'.")
    if request.execution_mode == "live" and not request.human_approval:
        return AdapterRefusal(
            error="human_approval_required",
            message="Live execution is not approved.",
            guidance="Record explicit human approval before starting a paid run.",
        )
    if request.credential_env_var not in _CREDENTIAL_ENV_VARS and (
        request.execution_mode == "live"
    ):
        return _invalid(
            "credential_env_var",
            "Name an allow-listed credential environment variable, never its value.",
        )
    if request.execution_mode == "dry_run" and request.credential_env_var is not None:
        return _invalid(
            "credential_env_var",
            "Leave credential_env_var empty for a dry run.",
        )
    if not math.isfinite(request.max_runtime_seconds) or request.max_runtime_seconds <= 0:
        return _invalid("max_runtime_seconds", "Provide a finite positive runtime bound.")
    if request.max_attempts < 1:
        return _invalid("max_attempts", "Provide an attempt limit of at least one.")
    if request.output_cap_bytes < 1:
        return _invalid("output_cap_bytes", "Provide a positive local output cap.")
    if not math.isfinite(request.spend_ceiling_usd) or request.spend_ceiling_usd <= 0:
        return _invalid("spend_ceiling_usd", "Provide a positive preflight ceiling.")
    if not request.stop_condition.strip():
        return _invalid("stop_condition", "State what ends the run.")
    if not request.tool_scope or any(not _is_identifier(tool) for tool in request.tool_scope):
        return _invalid("tool_scope", "Declare one or more bounded tool identifiers.")
    if not _is_digest(request.task_contract_digest):
        return _invalid("task_contract_digest", "Use a lowercase SHA-256 digest.")
    if not _is_digest(request.evidence_contract_digest):
        return _invalid("evidence_contract_digest", "Use a lowercase SHA-256 digest.")
    return None


def validate_result(result: AdapterResult) -> AdapterRefusal | None:
    """Validate a metadata-only result returned by a future adapter."""

    if result.contract_version != ADAPTER_CONTRACT_VERSION:
        return _invalid("contract_version", "Use the declared adapter contract version.")
    if result.status not in _STATUSES:
        return _invalid("status", "Use a declared terminal adapter status.")
    if result.claim not in _CLAIMS:
        return _invalid("claim", "Use completed, failed, or unknown.")
    if result.native_outcome not in _NATIVE_OUTCOMES:
        return _invalid("native_outcome", "Use a declared benchmark outcome.")
    if result.evidence_status not in _EVIDENCE_STATUSES:
        return _invalid("evidence_status", "Use a declared evidence status.")
    if result.trajectory_status not in _TRAJECTORY_STATUSES:
        return _invalid("trajectory_status", "Use a declared trajectory status.")
    if not math.isfinite(result.elapsed_seconds) or result.elapsed_seconds < 0:
        return _invalid("elapsed_seconds", "Use a finite non-negative duration.")
    if result.observed_cost_usd is not None and (
        not math.isfinite(result.observed_cost_usd) or result.observed_cost_usd < 0
    ):
        return _invalid("observed_cost_usd", "Use a finite non-negative observed cost.")
    if result.receipt_digest is not None and not _is_digest(result.receipt_digest):
        return _invalid("receipt_digest", "Use a lowercase SHA-256 digest.")
    return None


def digest_identifier(value: str) -> str:
    """Create a stable digest for a public identifier or contract fixture."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
