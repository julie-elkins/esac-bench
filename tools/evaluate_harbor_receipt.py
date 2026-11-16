"""Evaluate one local metadata-only Harbor receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esac_bench.harbor_receipts import evaluate_harbor_receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a metadata-only Harbor receipt."
    )
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(
            json.dumps(
                {
                    "error": "receipt_read_failed",
                    "message": "The receipt could not be read as JSON.",
                    "guidance": "Provide a readable metadata-only JSON receipt.",
                },
                sort_keys=True,
            )
        )
        return 2
    result = evaluate_harbor_receipt(payload)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 2 if hasattr(result, "error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
