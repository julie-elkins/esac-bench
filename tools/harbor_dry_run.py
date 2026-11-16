"""Run the provider-specific Harbor adapter in dry-run mode."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esac_bench.harbor_adapter import build_harbor_dry_run
from esac_bench.live_contract import AdapterRequest, digest_identifier


def main() -> int:
    request = AdapterRequest(
        run_id="esac-harbor-dry-run-v0",
        adapter_id="mini-swe-agent",
        provider="anthropic",
        model="claude-opus-4-6",
        task_id="coding-interruption",
        execution_mode="dry_run",
        credential_env_var=None,
        max_runtime_seconds=300,
        max_attempts=1,
        output_cap_bytes=1_000_000,
        spend_ceiling_usd=1.0,
        stop_condition="stop after command-plan validation",
        tool_scope=("harbor-runner",),
        task_contract_digest=digest_identifier("coding-interruption"),
        evidence_contract_digest=digest_identifier("esac-offline-v0"),
        human_approval=False,
    )
    plan = build_harbor_dry_run(
        request,
        config_path="config/mini-swe-agent-live-2.0.toml",
        receipt_path="runs/esac-harbor-dry-run-v0.receipt.json",
    )
    print(json.dumps(plan.to_dict() if hasattr(plan, "to_dict") else plan, sort_keys=True))
    return 0 if hasattr(plan, "to_dict") else 1


if __name__ == "__main__":
    raise SystemExit(main())
