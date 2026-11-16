"""Bounded Harbor adapters for the mini-swe-agent execution path.

The dry-run adapter constructs a safe command without executing it. The live
adapter is deliberately narrow: it validates before credential access, runs
one shell-free command, captures raw output only in the ignored local run
workspace, and returns metadata-only evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import PurePosixPath
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from .live_contract import (
    ADAPTER_CONTRACT_VERSION,
    AdapterRequest,
    AdapterRefusal,
    AdapterResult,
    validate_request,
    validate_result,
)


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


def _path_under_root(workspace_root: Path, relative_path: str, field: str) -> Path:
    root = workspace_root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"invalid_{field}") from error
    return candidate


def _is_ignored_run_path(relative_path: str) -> bool:
    return PurePosixPath(relative_path).parts[:1] in (("runs",), ("jobs",))


def _harbor_command(
    *,
    runner_prefix: tuple[str, ...],
    config_path: str,
    receipt_path: str,
) -> tuple[str, ...]:
    return (
        *runner_prefix,
        "--config",
        config_path,
        "--receipt",
        receipt_path,
    )


def _result(
    request: AdapterRequest,
    *,
    status: str,
    claim: str,
    native_outcome: str,
    evidence_status: str,
    trajectory_status: str,
    returncode: int | None,
    elapsed_seconds: float,
    receipt_digest: str | None,
    limitation: str | None,
) -> AdapterResult:
    return AdapterResult(
        contract_version=ADAPTER_CONTRACT_VERSION,
        run_id=request.run_id,
        adapter_id=request.adapter_id,
        provider=request.provider,
        model=request.model,
        task_id=request.task_id,
        status=status,
        claim=claim,
        native_outcome=native_outcome,
        evidence_status=evidence_status,
        trajectory_status=trajectory_status,
        returncode=returncode,
        elapsed_seconds=elapsed_seconds,
        observed_cost_usd=None,
        receipt_digest=receipt_digest,
        limitation=limitation,
    )


def _refusal(error: str, message: str, guidance: str) -> dict[str, str]:
    return AdapterRefusal(error=error, message=message, guidance=guidance).to_dict()


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
        contract_version=ADAPTER_CONTRACT_VERSION,
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
        command=_harbor_command(
            runner_prefix=("harbor", "run"),
            config_path=safe_config,
            receipt_path=safe_receipt,
        ),
        shell=False,
        credential_access=False,
        config_path=safe_config,
        receipt_path=safe_receipt,
        result=result,
    )


def _minimal_child_environment(credential_env_var: str, credential: str) -> dict[str, str]:
    """Forward runtime essentials and exactly one approved credential."""

    allowed_runtime = (
        "HOME",
        "LANG",
        "LC_ALL",
        "LOGNAME",
        "PATH",
        "PWD",
        "SHELL",
        "TERM",
        "TMPDIR",
        "USER",
        "XDG_CONFIG_HOME",
    )
    environment = {
        key: os.environ[key]
        for key in allowed_runtime
        if key in os.environ
    }
    environment[credential_env_var] = credential
    return environment


def _terminate_process(process: subprocess.Popen[bytes]) -> bool:
    """Stop and reap the process group so a timed-out child cannot continue spending."""

    try:
        process_group_id = os.getpgid(process.pid)
    except ProcessLookupError:
        return process.poll() is not None

    # The PID is usually also the process-group ID because the worker starts a
    # new session, but that is an implementation detail of the launcher. Use
    # the observed group ID: assuming PID == PGID left the Harbor child alive
    # in the first live smoke and could allow provider work to continue.
    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        return process.poll() is not None

    try:
        process.wait(timeout=2)
        return True
    except subprocess.TimeoutExpired:
        pass

    try:
        os.killpg(process_group_id, signal.SIGKILL)
    except ProcessLookupError:
        return process.poll() is not None

    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        return False
    return True


def _digest_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_receipt(path: Path, result: AdapterResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_harbor_live(
    request: AdapterRequest,
    *,
    config_path: str,
    receipt_path: str,
    metadata_receipt_path: str,
    output_path: str,
    workspace_root: Path,
    runner_prefix: tuple[str, ...] = ("harbor", "run"),
) -> AdapterResult | dict[str, str]:
    """Run one bounded Harbor command and emit a metadata-only receipt."""

    refusal = validate_request(request)
    if refusal is not None:
        return refusal.to_dict()
    if request.execution_mode != "live":
        return _refusal(
            "live_mode_required",
            "The live Harbor adapter requires a live request.",
            "Use the dry-run adapter for command-plan validation.",
        )
    if request.adapter_id != "mini-swe-agent":
        return _refusal(
            "adapter_id_invalid",
            "This adapter only executes mini-swe-agent runs.",
            "Use adapter_id='mini-swe-agent' or select another reviewed adapter.",
        )
    if request.max_attempts != 1:
        return _refusal(
            "automatic_retry_forbidden",
            "The first live adapter permits exactly one attempt.",
            "Set max_attempts=1; retry policy requires a separate experiment.",
        )
    if not runner_prefix or any(not part.strip() for part in runner_prefix):
        return _refusal(
            "invalid_runner_prefix",
            "The runner prefix is empty.",
            "Provide a fixed non-empty argument vector prefix.",
        )
    if not all(
        _is_ignored_run_path(path)
        for path in (receipt_path, metadata_receipt_path, output_path)
    ):
        return _refusal(
            "unsafe_output_path",
            "Live evidence and raw output must stay under an ignored runs/ or jobs/ directory.",
            "Use separate paths below runs/ or jobs/ so raw provider material cannot enter the public repository.",
        )

    try:
        safe_config = _safe_relative_path(config_path, "config_path")
        safe_receipt = _safe_relative_path(receipt_path, "receipt_path")
        safe_metadata_receipt = _safe_relative_path(
            metadata_receipt_path,
            "metadata_receipt_path",
        )
        safe_output = _safe_relative_path(output_path, "output_path")
        root = workspace_root.resolve()
        config_file = _path_under_root(root, safe_config, "config_path")
        receipt_file = _path_under_root(root, safe_receipt, "receipt_path")
        metadata_receipt_file = _path_under_root(
            root,
            safe_metadata_receipt,
            "metadata_receipt_path",
        )
        output_file = _path_under_root(root, safe_output, "output_path")
    except (OSError, ValueError) as error:
        field = str(error)
        if field not in {
            "invalid_config_path",
            "invalid_receipt_path",
            "invalid_metadata_receipt_path",
            "invalid_output_path",
        }:
            field = "invalid_workspace_path"
        return _refusal(
            field,
            "Harbor paths must be bounded inside the workspace.",
            "Use relative paths without parent-directory traversal or symlinks outside the workspace.",
        )

    if not config_file.is_file():
        return _refusal(
            "config_missing",
            "The Harbor configuration file does not exist.",
            "Provide one checked, public task configuration inside the workspace.",
        )
    if (
        receipt_file.exists()
        or metadata_receipt_file.exists()
        or output_file.exists()
    ):
        return _refusal(
            "output_exists",
            "A requested evidence or raw-output path already exists.",
            "Use a new run identifier and unique output paths; do not overwrite evidence.",
        )
    if len({receipt_file, metadata_receipt_file, output_file}) != 3:
        return _refusal(
            "output_paths_conflict",
            "The raw receipt, metadata receipt, and raw-output paths must be different files.",
            "Use separate paths for provider evidence, ESAC metadata, and process output.",
        )

    credential = os.environ.get(request.credential_env_var or "")
    if not credential:
        return _refusal(
            "credential_unavailable",
            "The approved credential environment variable is not available.",
            f"Set {request.credential_env_var} in the supervised shell, then retry once.",
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    command = _harbor_command(
        runner_prefix=runner_prefix,
        config_path=safe_config,
        receipt_path=safe_receipt,
    )
    environment = _minimal_child_environment(request.credential_env_var, credential)
    started = time.monotonic()
    process: subprocess.Popen[bytes] | None = None
    timed_out = False
    output_exceeded = False
    cleanup_confirmed = True

    try:
        with output_file.open("wb") as output_stream:
            process = subprocess.Popen(
                command,
                cwd=root,
                env=environment,
                stdout=output_stream,
                stderr=subprocess.STDOUT,
                shell=False,
                start_new_session=True,
            )
            while process.poll() is None:
                if time.monotonic() - started >= request.max_runtime_seconds:
                    timed_out = True
                    cleanup_confirmed = _terminate_process(process)
                    break
                if output_file.stat().st_size > request.output_cap_bytes:
                    output_exceeded = True
                    cleanup_confirmed = _terminate_process(process)
                    break
                time.sleep(0.05)
            if process.poll() is None:
                process.wait()
            if output_file.stat().st_size > request.output_cap_bytes:
                output_exceeded = True
    except FileNotFoundError:
        return _refusal(
            "runner_unavailable",
            "The configured runner could not be started.",
            "Install or expose the reviewed runner prefix, then rerun the smoke test.",
        )
    except OSError as error:
        return _refusal(
            "process_start_failed",
            "The Harbor process could not be started.",
            f"Inspect the local runtime before retrying: {error.__class__.__name__}.",
        )

    elapsed = time.monotonic() - started
    receipt_digest = _digest_file(receipt_file)
    evidence_status = "complete" if receipt_digest is not None else "incomplete"
    trajectory_status = "present" if receipt_digest is not None else "absent"
    if timed_out:
        result = _result(
            request,
            status="timed_out",
            claim="unknown",
            native_outcome="not_observed",
            evidence_status=evidence_status,
            trajectory_status=trajectory_status,
            returncode=None,
            elapsed_seconds=elapsed,
            receipt_digest=receipt_digest,
            limitation=(
                "Harbor exceeded the declared runtime bound"
                if cleanup_confirmed
                else "Harbor exceeded the declared runtime bound; process cleanup was not confirmed"
            ),
        )
    elif output_exceeded:
        result = _result(
            request,
            status="failed",
            claim="unknown",
            native_outcome="not_observed",
            evidence_status=evidence_status,
            trajectory_status=trajectory_status,
            returncode=None,
            elapsed_seconds=elapsed,
            receipt_digest=receipt_digest,
            limitation=(
                "Harbor exceeded the declared local output cap"
                if cleanup_confirmed
                else "Harbor exceeded the declared local output cap; process cleanup was not confirmed"
            ),
        )
    else:
        returncode = process.returncode if process is not None else None
        result = _result(
            request,
            status="completed" if returncode == 0 else "failed",
            claim="unknown" if returncode == 0 else "failed",
            native_outcome="unknown",
            evidence_status=evidence_status,
            trajectory_status=trajectory_status,
            returncode=returncode,
            elapsed_seconds=elapsed,
            receipt_digest=receipt_digest,
            limitation=(
                "Harbor completed; native ESAC outcome requires receipt evaluation"
                if returncode == 0
                else "Harbor returned a non-zero exit code"
            ),
        )

    result_refusal = validate_result(result)
    if result_refusal is not None:
        return result_refusal.to_dict()
    _write_receipt(metadata_receipt_file, result)
    return result
