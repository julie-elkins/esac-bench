"""Offline adapters for public metadata from related repositories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_calibration_record(path: str | Path) -> dict[str, Any]:
    """Load a public calibration record without turning it into native results."""

    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != "legacy_calibration":
        raise ValueError("calibration_record_type_invalid")
    if record.get("native_esac_score") is not False:
        raise ValueError("calibration_record_cannot_be_native_score")
    if record.get("data_class") != "public_metadata_only":
        raise ValueError("calibration_data_class_invalid")
    return {
        "source_type": "legacy_calibration",
        "native_esac_score": False,
        "source_count": len(record.get("sources", [])),
        "source_ids": [
            source["source_id"]
            for source in record.get("sources", [])
            if isinstance(source, dict) and "source_id" in source
        ],
    }


def load_diagnostic_cases(path: str | Path) -> dict[str, Any]:
    """Load public diagnostic metadata and return an identifier-only index."""

    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("diagnostic_records_invalid")
    return {
        "source_type": "diagnostic_case_study",
        "case_count": len(records),
        "case_ids": [
            record["case_id"]
            for record in records
            if isinstance(record, dict) and "case_id" in record
        ],
    }

