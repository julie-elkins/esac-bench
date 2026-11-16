import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from esac_bench.adapters import load_calibration_record, load_diagnostic_cases
from esac_bench.live_contract import (
    ADAPTER_CONTRACT_VERSION,
    AdapterRequest,
    AdapterResult,
    digest_identifier,
    validate_request,
    validate_result,
)
from esac_bench.harbor_adapter import build_harbor_dry_run, run_harbor_live
from esac_bench.runner import run_suite
from esac_bench.schema import SCHEMA_VERSION, validate_native_report


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.report = run_suite()

    def test_report_is_metadata_only_and_stable(self):
        self.assertEqual(self.report["data_class"], "synthetic")
        self.assertEqual(self.report["protocol"], "esac-offline-v0")
        self.assertEqual(self.report["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.report["schema_errors"], [])
        encoded = json.dumps(self.report, sort_keys=True)
        self.assertNotIn("prompt", encoded)
        self.assertNotIn("tool_payload", encoded)
        self.assertNotIn("provider_response", encoded)
        self.assertEqual(len(self.report["report_digest"]), 64)

    def test_guarded_control_passes_all_dimensions(self):
        summary = self.report["summaries"]["guarded"]
        for dimension in ("outcome", "recovery_safety", "evidence_completeness", "claim_support"):
            self.assertEqual(summary[dimension], {"pass": 6})

    def test_naive_control_exposes_separate_failures(self):
        summary = self.report["summaries"]["naive"]
        self.assertEqual(summary["outcome"]["pass"], 4)
        self.assertEqual(summary["outcome"]["fail"], 2)
        self.assertEqual(summary["recovery_safety"]["fail"], 2)
        self.assertEqual(summary["evidence_completeness"]["fail"], 4)
        self.assertEqual(summary["claim_support"]["fail"], 4)

    def test_native_results_are_not_legacy_results(self):
        self.assertNotIn("legacy_calibration", self.report)
        self.assertEqual(self.report["benchmark"], "ESAC-Bench")
        self.assertEqual(self.report["task_count"], 6)

    def test_mutation_controls_catch_all_planted_failures(self):
        self.assertEqual(self.report["mutation_suite_status"], "passed")
        self.assertEqual(len(self.report["mutation_results"]), 4)
        self.assertTrue(
            all(item["detected"] for item in self.report["mutation_results"])
        )

    def test_schema_rejects_forbidden_content(self):
        invalid = dict(self.report)
        invalid["provider_response"] = "not allowed"
        self.assertIn("forbidden_content_key", validate_native_report(invalid))

    def test_cross_repository_records_stay_non_native(self):
        root = Path(__file__).parents[1]
        calibration = load_calibration_record(root / "data/legacy-calibration.json")
        diagnostics = load_diagnostic_cases(root / "data/diagnostic-case-studies.json")
        self.assertFalse(calibration["native_esac_score"])
        self.assertEqual(calibration["source_count"], 2)
        self.assertEqual(diagnostics["case_count"], 2)

    def test_live_request_requires_bounds_and_approval(self):
        request = AdapterRequest(
            run_id="run-1",
            adapter_id="adapter-1",
            provider="provider-1",
            model="model-1",
            task_id="task-1",
            execution_mode="live",
            credential_env_var="OPENAI_API_KEY",
            max_runtime_seconds=60,
            max_attempts=1,
            output_cap_bytes=1024,
            spend_ceiling_usd=1,
            stop_condition="stop after one task or any refusal",
            tool_scope=("tool-runner",),
            task_contract_digest=digest_identifier("task"),
            evidence_contract_digest=digest_identifier("evidence"),
            human_approval=False,
        )
        refusal = validate_request(request)
        self.assertIsNotNone(refusal)
        self.assertEqual(refusal.error, "human_approval_required")

    def test_dry_run_does_not_accept_a_credential_name(self):
        request = AdapterRequest(
            run_id="run-1",
            adapter_id="adapter-1",
            provider="provider-1",
            model="model-1",
            task_id="task-1",
            execution_mode="dry_run",
            credential_env_var="OPENAI_API_KEY",
            max_runtime_seconds=60,
            max_attempts=1,
            output_cap_bytes=1024,
            spend_ceiling_usd=1,
            stop_condition="stop after validation",
            tool_scope=("tool-runner",),
            task_contract_digest=digest_identifier("task"),
            evidence_contract_digest=digest_identifier("evidence"),
            human_approval=False,
        )
        refusal = validate_request(request)
        self.assertIsNotNone(refusal)
        self.assertEqual(refusal.error, "invalid_credential_env_var")

    def test_live_result_is_metadata_only(self):
        result = AdapterResult(
            contract_version=ADAPTER_CONTRACT_VERSION,
            run_id="run-1",
            adapter_id="adapter-1",
            provider="provider-1",
            model="model-1",
            task_id="task-1",
            status="completed",
            claim="completed",
            native_outcome="pass",
            evidence_status="complete",
            trajectory_status="present",
            returncode=0,
            elapsed_seconds=1.2,
            observed_cost_usd=0.1,
            receipt_digest=digest_identifier("receipt"),
        )
        self.assertIsNone(validate_result(result))

    def test_harbor_dry_run_builds_shell_free_plan_without_credentials(self):
        request = AdapterRequest(
            run_id="run-1",
            adapter_id="mini-swe-agent",
            provider="anthropic",
            model="claude-opus-4-6",
            task_id="task-1",
            execution_mode="dry_run",
            credential_env_var=None,
            max_runtime_seconds=60,
            max_attempts=1,
            output_cap_bytes=1024,
            spend_ceiling_usd=1,
            stop_condition="stop after plan construction",
            tool_scope=("harbor-runner",),
            task_contract_digest=digest_identifier("task"),
            evidence_contract_digest=digest_identifier("evidence"),
            human_approval=False,
        )
        plan = build_harbor_dry_run(
            request,
            config_path="config/mini-swe-agent-live-2.0.toml",
            receipt_path="runs/esac-dry-run.receipt.json",
        )
        self.assertEqual(plan.command[0], "harbor")
        self.assertFalse(plan.shell)
        self.assertFalse(plan.credential_access)
        self.assertEqual(plan.result.status, "unknown")
        self.assertEqual(plan.result.native_outcome, "not_observed")
        self.assertEqual(plan.result.trajectory_status, "absent")

    def test_harbor_dry_run_rejects_path_traversal(self):
        request = AdapterRequest(
            run_id="run-1",
            adapter_id="mini-swe-agent",
            provider="anthropic",
            model="claude-opus-4-6",
            task_id="task-1",
            execution_mode="dry_run",
            credential_env_var=None,
            max_runtime_seconds=60,
            max_attempts=1,
            output_cap_bytes=1024,
            spend_ceiling_usd=1,
            stop_condition="stop after plan construction",
            tool_scope=("harbor-runner",),
            task_contract_digest=digest_identifier("task"),
            evidence_contract_digest=digest_identifier("evidence"),
            human_approval=False,
        )
        refusal = build_harbor_dry_run(
            request,
            config_path="../secret.toml",
            receipt_path="runs/result.json",
        )
        self.assertEqual(refusal["error"], "invalid_config_path")

    def _live_request(self, *, runtime=2, output_cap=1024):
        return AdapterRequest(
            run_id="live-run-1",
            adapter_id="mini-swe-agent",
            provider="anthropic",
            model="claude-opus-4-6",
            task_id="coding-interruption",
            execution_mode="live",
            credential_env_var="ANTHROPIC_API_KEY",
            max_runtime_seconds=runtime,
            max_attempts=1,
            output_cap_bytes=output_cap,
            spend_ceiling_usd=5,
            stop_condition="stop after one task or any refusal",
            tool_scope=("harbor-runner",),
            task_contract_digest=digest_identifier("task"),
            evidence_contract_digest=digest_identifier("evidence"),
            human_approval=True,
        )

    def _fake_harbor(self, root, body):
        executable = root / "fake-harbor"
        executable.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        return str(executable)

    def test_live_harbor_preserves_raw_receipt_and_writes_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            (root / "config/task.toml").write_text("task = 1\n", encoding="utf-8")
            executable = self._fake_harbor(
                root,
                """receipt=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "--receipt" ]; then shift; receipt="$1"; fi
  shift
done
mkdir -p "$(dirname "$receipt")"
printf '{"raw":"local-only"}\n' > "$receipt"
printf 'bounded output\n'
""",
            )
            request = self._live_request()
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
                result = run_harbor_live(
                    request,
                    config_path="config/task.toml",
                    receipt_path="runs/provider-receipt.json",
                    metadata_receipt_path="runs/esac-receipt.json",
                    output_path="runs/provider-output.log",
                    workspace_root=root,
                    runner_prefix=(executable,),
                )

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.evidence_status, "complete")
            self.assertTrue((root / "runs/provider-receipt.json").exists())
            self.assertIn(
                '"raw":"local-only"',
                (root / "runs/provider-receipt.json").read_text(encoding="utf-8"),
            )
            metadata = json.loads(
                (root / "runs/esac-receipt.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("raw", json.dumps(metadata))

    def test_live_harbor_refuses_missing_credential_before_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            (root / "config/task.toml").write_text("task = 1\n", encoding="utf-8")
            request = self._live_request()
            with patch.dict(os.environ, {}, clear=True):
                result = run_harbor_live(
                    request,
                    config_path="config/task.toml",
                    receipt_path="runs/provider-receipt.json",
                    metadata_receipt_path="runs/esac-receipt.json",
                    output_path="runs/provider-output.log",
                    workspace_root=root,
                    runner_prefix=("/missing/harbor",),
                )

            self.assertEqual(result["error"], "credential_unavailable")
            self.assertFalse((root / "runs").exists())

    def test_live_harbor_refuses_public_output_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            (root / "config/task.toml").write_text("task = 1\n", encoding="utf-8")
            request = self._live_request()
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
                result = run_harbor_live(
                    request,
                    config_path="config/task.toml",
                    receipt_path="README.receipt.json",
                    metadata_receipt_path="runs/esac-receipt.json",
                    output_path="runs/provider-output.log",
                    workspace_root=root,
                    runner_prefix=("/missing/harbor",),
                )

            self.assertEqual(result["error"], "unsafe_output_path")
            self.assertFalse((root / "runs").exists())

    def test_live_harbor_times_out_and_writes_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            (root / "config/task.toml").write_text("task = 1\n", encoding="utf-8")
            executable = self._fake_harbor(root, "sleep 1")
            request = self._live_request(runtime=0.1)
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
                result = run_harbor_live(
                    request,
                    config_path="config/task.toml",
                    receipt_path="runs/provider-receipt.json",
                    metadata_receipt_path="runs/esac-receipt.json",
                    output_path="runs/provider-output.log",
                    workspace_root=root,
                    runner_prefix=(executable,),
                )

            self.assertEqual(result.status, "timed_out")
            self.assertEqual(result.native_outcome, "not_observed")
            self.assertTrue((root / "runs/esac-receipt.json").exists())

    def test_live_harbor_stops_on_output_cap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            (root / "config/task.toml").write_text("task = 1\n", encoding="utf-8")
            executable = self._fake_harbor(root, "head -c 2048 /dev/zero")
            request = self._live_request(output_cap=10)
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
                result = run_harbor_live(
                    request,
                    config_path="config/task.toml",
                    receipt_path="runs/provider-receipt.json",
                    metadata_receipt_path="runs/esac-receipt.json",
                    output_path="runs/provider-output.log",
                    workspace_root=root,
                    runner_prefix=(executable,),
                )

            self.assertEqual(result.status, "failed")
            self.assertIn("output cap", result.limitation)


if __name__ == "__main__":
    unittest.main()

