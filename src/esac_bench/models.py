"""Small metadata-only records used by the reference benchmark."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any


DIMENSIONS = (
    "outcome",
    "recovery_safety",
    "evidence_completeness",
    "claim_support",
)


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    task_family: str
    required_evidence: tuple[str, ...]
    outcome_evidence: tuple[str, ...]
    expected_effects: tuple[str, ...]


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    profile: str
    scenario: str
    dimensions: dict[str, str]
    observed_evidence: tuple[str, ...]
    observed_effects: tuple[str, ...]
    claim: str
    limitation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def digest_metadata(value: Any) -> str:
    """Return a stable digest for identifier-only report metadata."""

    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()

