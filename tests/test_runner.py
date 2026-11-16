import json
from pathlib import Path
import unittest

from esac_bench.adapters import load_calibration_record, load_diagnostic_cases
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


if __name__ == "__main__":
    unittest.main()

