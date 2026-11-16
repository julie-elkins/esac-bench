"""CI gate for the native ESAC-Bench report contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = list(report.get("schema_errors", []))
    if errors:
        print(json.dumps({"status": "failed", "reason_codes": errors}, sort_keys=True))
        return 1
    if report.get("mutation_suite_status") != "passed":
        print(json.dumps({"status": "failed", "reason": "mutation_suite"}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "passed",
                "schema_version": report.get("schema_version"),
                "task_contract_digest": report.get("task_contract_digest"),
                "report_digest": report.get("report_digest"),
                "mutation_count": len(report.get("mutation_results", [])),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

