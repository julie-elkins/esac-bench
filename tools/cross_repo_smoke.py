"""Offline integration smoke for metadata imported from related repositories."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esac_bench.adapters import load_calibration_record, load_diagnostic_cases
from esac_bench.runner import run_suite


def main() -> int:
    calibration = load_calibration_record(ROOT / "data/legacy-calibration.json")
    diagnostics = load_diagnostic_cases(ROOT / "data/diagnostic-case-studies.json")
    report = run_suite()
    if report["schema_errors"] or report["mutation_suite_status"] != "passed":
        print(json.dumps({"status": "failed", "reason": "native_contract"}, sort_keys=True))
        return 1
    if calibration["native_esac_score"]:
        print(json.dumps({"status": "failed", "reason": "calibration_promoted"}, sort_keys=True))
        return 1
    if calibration["source_count"] != 2 or diagnostics["case_count"] != 2:
        print(json.dumps({"status": "failed", "reason": "source_coverage"}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "passed",
                "native_schema_version": report["schema_version"],
                "native_report_digest": report["report_digest"],
                "calibration_source_ids": calibration["source_ids"],
                "diagnostic_case_ids": diagnostics["case_ids"],
                "native_esac_score": calibration["native_esac_score"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

