import json
from pathlib import Path
import subprocess
import sys
import unittest

from esac_bench.harbor_receipts import evaluate_harbor_receipt


ROOT = Path(__file__).parents[1]


def passed_receipt() -> dict[str, object]:
    return json.loads(
        (ROOT / "tests/fixtures/harbor-receipt-passed.json").read_text(
            encoding="utf-8"
        )
    )


class HarborReceiptTests(unittest.TestCase):
    def test_clean_pass_requires_execution_benchmark_and_evidence(self):
        result = evaluate_harbor_receipt(passed_receipt())

        self.assertEqual(result.native_outcome, "pass")
        self.assertEqual(result.execution_status, "completed")
        self.assertEqual(result.evidence_status, "complete")
        self.assertEqual(result.trajectory_status, "present")
        self.assertEqual(result.benchmark_score, 1.0)

    def test_harbor_completion_alone_is_not_a_pass(self):
        receipt = passed_receipt()
        receipt["trajectory_digest"] = None

        result = evaluate_harbor_receipt(receipt)

        self.assertEqual(result.native_outcome, "unknown")
        self.assertEqual(result.evidence_status, "incomplete")
        self.assertEqual(result.trajectory_status, "absent")

    def test_invalid_present_trajectory_is_unknown_evidence(self):
        receipt = passed_receipt()
        receipt["trajectory_digest"] = "not-a-digest"

        result = evaluate_harbor_receipt(receipt)

        self.assertEqual(result.native_outcome, "unknown")
        self.assertEqual(result.evidence_status, "incomplete")
        self.assertEqual(result.trajectory_status, "unknown")

    def test_timeout_is_not_observed_benchmark_outcome(self):
        receipt = passed_receipt()
        receipt["status"] = "timed_out"
        receipt["timed_out"] = True
        receipt["benchmark_status"] = "not-run"

        result = evaluate_harbor_receipt(receipt)

        self.assertEqual(result.execution_status, "timed_out")
        self.assertEqual(result.native_outcome, "not_observed")

    def test_clean_benchmark_failure_is_a_failure(self):
        receipt = passed_receipt()
        receipt["benchmark_status"] = "failed"
        receipt["benchmark_score"] = 0.0

        result = evaluate_harbor_receipt(receipt)

        self.assertEqual(result.native_outcome, "fail")

    def test_raw_content_is_refused(self):
        receipt = passed_receipt()
        receipt["trajectory"] = [{"tool": "private"}]

        result = evaluate_harbor_receipt(receipt)

        self.assertEqual(result.error, "forbidden_receipt_content")

    def test_unknown_metadata_is_refused(self):
        receipt = passed_receipt()
        receipt["future_provider_field"] = "not reviewed"

        result = evaluate_harbor_receipt(receipt)

        self.assertEqual(result.error, "unknown_receipt_fields")

    def test_invalid_metadata_types_are_refused(self):
        receipt = passed_receipt()
        receipt["runner_successful_trials"] = "1"

        result = evaluate_harbor_receipt(receipt)

        self.assertEqual(result.error, "trial_counts_invalid")

    def test_cli_evaluates_metadata_only_fixture(self):
        result = subprocess.run(
            [
                sys.executable,
                "tools/evaluate_harbor_receipt.py",
                "--receipt",
                "tests/fixtures/harbor-receipt-passed.json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["native_outcome"], "pass")
        self.assertNotIn("trajectory", payload)
