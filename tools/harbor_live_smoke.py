"""Run one explicitly approved Harbor smoke through the bounded adapter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esac_bench.harbor_adapter import run_harbor_live
from esac_bench.live_contract import AdapterRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one bounded mini-swe-agent Harbor smoke."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--receipt", required=True, help="Local Harbor receipt under runs/ or jobs/.")
    parser.add_argument(
        "--metadata-receipt",
        required=True,
        help="Metadata-only ESAC receipt under runs/ or jobs/.",
    )
    parser.add_argument(
        "--raw-output",
        required=True,
        help="Local process output under runs/ or jobs/.",
    )
    parser.add_argument("--task-contract-digest", required=True)
    parser.add_argument("--evidence-contract-digest", required=True)
    parser.add_argument("--stop-condition", required=True)
    parser.add_argument("--credential-env-var", default="ANTHROPIC_API_KEY")
    parser.add_argument("--max-runtime-seconds", type=float, default=900)
    parser.add_argument("--output-cap-bytes", type=int, default=1_000_000)
    parser.add_argument("--spend-ceiling-usd", type=float, default=5.0)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument(
        "--runner-prefix",
        nargs="+",
        default=("harbor", "run"),
        help="Shell-free runner prefix, such as: uv run harbor-assurance run.",
    )
    parser.add_argument(
        "--approve-live-run",
        action="store_true",
        help="Required immediately before the supervised provider call.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request = AdapterRequest(
        run_id=args.run_id,
        adapter_id="mini-swe-agent",
        provider="anthropic",
        model=args.model,
        task_id=args.task_id,
        execution_mode="live",
        credential_env_var=args.credential_env_var,
        max_runtime_seconds=args.max_runtime_seconds,
        max_attempts=1,
        output_cap_bytes=args.output_cap_bytes,
        spend_ceiling_usd=args.spend_ceiling_usd,
        stop_condition=args.stop_condition,
        tool_scope=("harbor-runner",),
        task_contract_digest=args.task_contract_digest,
        evidence_contract_digest=args.evidence_contract_digest,
        human_approval=args.approve_live_run,
    )
    result = run_harbor_live(
        request,
        config_path=args.config,
        receipt_path=args.receipt,
        metadata_receipt_path=args.metadata_receipt,
        output_path=args.raw_output,
        workspace_root=args.workspace_root,
        runner_prefix=tuple(args.runner_prefix),
    )
    payload = result.to_dict() if hasattr(result, "to_dict") else result
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not hasattr(result, "to_dict"):
        return 1
    return 0 if result.status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
