"""Validation for the public, metadata-only ESAC-Bench report contract."""

from __future__ import annotations

from typing import Any

from .models import DIMENSIONS

SCHEMA_VERSION = "esac-report-v0"
FORBIDDEN_KEYS = frozenset(
    {
        "prompt",
        "tool_payload",
        "tool_arguments",
        "provider_response",
        "trajectory",
        "raw_trace",
        "credential",
    }
)


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def validate_native_report(report: dict[str, Any]) -> list[str]:
    """Return stable reason codes for invalid report metadata."""

    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if report.get("benchmark") != "ESAC-Bench":
        errors.append("benchmark_invalid")
    if report.get("protocol") != "esac-offline-v0":
        errors.append("protocol_invalid")
    if report.get("data_class") != "synthetic":
        errors.append("data_class_invalid")
    if report.get("dimensions") != list(DIMENSIONS):
        errors.append("dimensions_invalid")
    if not isinstance(report.get("results"), list):
        errors.append("results_missing")
    if not isinstance(report.get("mutation_results"), list):
        errors.append("mutation_results_missing")
    recovery_track = report.get("recovery_track")
    if not isinstance(recovery_track, dict):
        errors.append("recovery_track_missing")
    else:
        if recovery_track.get("track_id") != "recovery-v0":
            errors.append("recovery_track_id_invalid")
        if recovery_track.get("case_count") != 7:
            errors.append("recovery_case_count_invalid")
        if recovery_track.get("metrics") != [
            "final_state_restoration",
            "side_effect_integrity",
            "recovery_evidence_completeness",
            "bounded_recovery",
        ]:
            errors.append("recovery_metrics_invalid")
        if not isinstance(recovery_track.get("results"), list):
            errors.append("recovery_results_missing")
    if report.get("mutation_suite_status") not in {"passed", "failed"}:
        errors.append("mutation_status_invalid")
    if "report_digest" not in report:
        errors.append("report_digest_missing")
    if _walk_keys(report) & FORBIDDEN_KEYS:
        errors.append("forbidden_content_key")
    return errors

