"""Dry-run adapter for the Harbor mini-swe-agent execution path.

The adapter has one responsibility: construct a safe Harbor argument vector
and a truthful not-executed result. It does not start Harbor, read credentials,
or contact Anthropic. A future live worker must be a separate implementation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any

from .live_contract import AdapterRequest, AdapterResult, validate_request


@dataclass(frozen=True)
class HarborDryRunPlan:
    """A shell-free command plan and its not-executed metadata result."""

    command: tuple[str, ...]
    shell: bool
    credential_access: bool
    config_path: str
    receipt_path: str
    result: AdapterResult

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["result"] = self.result.to_dict()
        return payload


def _safe_relative_path(value: str, field: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not value.strip():
        raise ValueError(f"invalid_{field}")
    return value


def build_harbor_dry_run(
    request: AdapterRequest,
    *,
    config_path: str,
    receipt_path: str,
) -> HarborDryRunPlan | dict[str, str]:
    """Build a mini-swe-agent Harbor plan without executing it."""

    refusal = validate_request(request)
    if refusal is not None:
        return refusal.to_dict()
    if request.execution_mode != "dry_run":
        return {
            "error": "dry_run_required",
            "message": "The Harbor dry-run adapter cannot execute a live request.",
            "guidance": "Use execution_mode='dry_run' until a separately reviewed live worker exists.",
        }
    if request.adapter_id != "mini-swe-agent":
        return {
            "error": "adapter_id_invalid",
            "message": "This adapter only plans mini-swe-agent runs.",
            "guidance": "Use adapter_id='mini-swe-agent' or select another reviewed adapter.",
        }

    try:
        safe_config = _safe_relative_path(config_path, "config_path")
        safe_receipt = _safe_relative_path(receipt_path, "receipt_path")
    except ValueError as error:
        field = str(error)
        return {
            "error": field,
            "message": "Harbor paths must be bounded relative paths.",
            "guidance": "Remove absolute paths and parent-directory traversal.",
        }

    result = AdapterResult(
        contract_version="esac-live-adapter-v0",
        run_id=request.run_id,
        adapter_id=request.adapter_id,
        provider=request.provider,
        model=request.model,
        task_id=request.task_id,
        status="unknown",
        claim="unknown",
        native_outcome="not_observed",
        evidence_status="unknown",
        trajectory_status="absent",
        returncode=None,
        elapsed_seconds=0.0,
        observed_cost_usd=None,
        receipt_digest=None,
        limitation="dry-run plan only; Harbor and the provider were not called",
    )
    return HarborDryRunPlan(
        command=(
            "harbor",
            "run",
            "--config",
            safe_config,
            "--receipt",
            safe_receipt,
        ),
        shell=False,
        credential_access=False,
        config_path=safe_config,
        receipt_path=safe_receipt,
        result=result,
    )
