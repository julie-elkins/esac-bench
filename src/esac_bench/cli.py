"""CLI for the metadata-only offline benchmark."""

from __future__ import annotations

import argparse
import json

from .runner import run_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the offline ESAC-Bench controls.")
    parser.add_argument("--json", action="store_true", help="emit JSON metadata")
    args = parser.parse_args(argv)
    report = run_suite()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print("ESAC-Bench offline v0")
    print(f"Tasks: {report['task_count']} | Profiles: {', '.join(report['profiles'])}")
    for profile, summary in report["summaries"].items():
        print(f"\n{profile}:")
        for dimension, counts in summary.items():
            print(f"  {dimension}: {counts}")
    print(f"\nReport digest: {report['report_digest']}")
    return 0

