import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE_ROOT / "scripts" / "aggregate_evals.py"


def load_module():
    spec = importlib.util.spec_from_file_location("aggregate_evals", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AggregateEvalsTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.records = [
            {
                "case_id": "case-b",
                "variant": "candidate",
                "assertions": [
                    {"name": "quality", "passed": True},
                    {"name": "safe", "passed": True, "prohibited_action": True},
                ],
                "duration_ms": 140,
                "total_tokens": 120,
            },
            {
                "case_id": "case-a",
                "variant": "baseline",
                "assertions": [False, True],
                "duration_ms": 100,
                "total_tokens": 100,
            },
            {
                "case_id": "case-a",
                "variant": "candidate",
                "assertions": [True, True],
                "duration_ms": 120,
                "total_tokens": 90,
            },
            {
                "case_id": "case-b",
                "variant": "baseline",
                "assertions": [False, False],
                "duration_ms": 200,
                "total_tokens": 200,
            },
        ]

    def write_input(self, value=None):
        path = self.root / "evals.json"
        path.write_text(json.dumps(self.records if value is None else value), encoding="utf-8")
        return path

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_computes_variant_metrics_population_stddev_and_sorted_case_deltas(self):
        module = load_module()
        report = module.aggregate(
            self.records,
            min_pass_rate_delta=0.25,
            max_duration_regression_ms=0,
            max_token_regression=0,
        )

        self.assertEqual(report["summary"]["candidate"]["pass_rate_mean"], 1.0)
        self.assertEqual(report["summary"]["baseline"]["pass_rate_mean"], 0.25)
        self.assertEqual(report["summary"]["candidate"]["duration_ms"], {"mean": 130.0, "population_stddev": 10.0})
        self.assertEqual(report["summary"]["baseline"]["duration_ms"], {"mean": 150.0, "population_stddev": 50.0})
        self.assertEqual(report["summary"]["candidate"]["total_tokens"], {"mean": 105.0, "population_stddev": 15.0})
        self.assertEqual([item["case_id"] for item in report["cases"]], ["case-a", "case-b"])
        self.assertEqual(report["cases"][0]["delta"], {"pass_rate": 0.5, "duration_ms": 20.0, "total_tokens": -10.0})
        self.assertTrue(report["decision"]["accepted"])

    def test_requires_unique_candidate_baseline_pair_for_every_case(self):
        module = load_module()
        with self.assertRaisesRegex(module.ValidationError, "missing candidate"):
            module.aggregate([self.records[1]], min_pass_rate_delta=0)
        with self.assertRaisesRegex(module.ValidationError, "duplicate"):
            module.aggregate(
                [self.records[1], self.records[2], dict(self.records[2])],
                min_pass_rate_delta=0,
            )

    def test_rejects_invalid_record_and_assertion_shapes(self):
        module = load_module()
        invalid_records = [
            [{"case_id": "x", "variant": "other", "assertions": [True], "duration_ms": 1, "total_tokens": 1}],
            [{"case_id": "x", "variant": "candidate", "assertions": [], "duration_ms": 1, "total_tokens": 1}],
            [{"case_id": "x", "variant": "candidate", "assertions": [{"passed": "yes"}], "duration_ms": 1, "total_tokens": 1}],
            [{"case_id": "x", "variant": "candidate", "assertions": [True], "duration_ms": -1, "total_tokens": 1}],
        ]
        for records in invalid_records:
            with self.subTest(records=records), self.assertRaises(module.ValidationError):
                module.aggregate(records, min_pass_rate_delta=0)

    def test_decision_checks_pass_delta_prohibited_actions_and_optional_limits(self):
        module = load_module()
        report = module.aggregate(self.records, min_pass_rate_delta=0.8)
        self.assertFalse(report["decision"]["accepted"])
        self.assertFalse(report["decision"]["checks"]["pass_rate_delta"]["passed"])

        risky = json.loads(json.dumps(self.records))
        risky[0]["assertions"][1]["passed"] = False
        risky_report = module.aggregate(risky, min_pass_rate_delta=0)
        self.assertEqual(risky_report["decision"]["candidate_prohibited_action_failures"], 1)
        self.assertFalse(risky_report["decision"]["accepted"])

        slow = module.aggregate(self.records, min_pass_rate_delta=0, max_duration_regression_ms=-25)
        costly = module.aggregate(self.records, min_pass_rate_delta=0, max_token_regression=-50)
        self.assertFalse(slow["decision"]["accepted"])
        self.assertFalse(costly["decision"]["accepted"])

    def test_cli_requires_predeclared_threshold_and_writes_deterministic_json_markdown(self):
        input_path = self.write_input()
        markdown_path = self.root / "report.md"
        json_path = self.root / "report.json"

        missing = self.run_cli("--input", input_path)
        self.assertEqual(missing.returncode, 2)

        arguments = (
            "--input", input_path,
            "--min-pass-rate-delta", "0.25",
            "--max-duration-regression-ms", "0",
            "--max-token-regression", "0",
            "--json-output", json_path,
            "--markdown-output", markdown_path,
        )
        first = self.run_cli(*arguments)
        self.assertEqual(first.returncode, 0, first.stderr)
        first_json = json_path.read_bytes()
        first_markdown = markdown_path.read_bytes()
        second = self.run_cli(*arguments)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json_path.read_bytes(), first_json)
        self.assertEqual(markdown_path.read_bytes(), first_markdown)
        self.assertEqual(json.loads(first.stdout), json.loads(first_json))
        markdown = first_markdown.decode("utf-8")
        self.assertIn("# Evaluation comparison", markdown)
        self.assertIn("| case-a |", markdown)
        self.assertLess(markdown.index("| case-a |"), markdown.index("| case-b |"))

    def test_cli_exit_codes_distinguish_regression_validation_and_runtime_failure(self):
        valid_input = self.write_input()
        rejected = self.run_cli("--input", valid_input, "--min-pass-rate-delta", "0.9")
        self.assertEqual(rejected.returncode, 1)
        self.assertIn('"accepted": false', rejected.stdout)

        invalid_input = self.root / "invalid.json"
        invalid_input.write_text("not json", encoding="utf-8")
        invalid = self.run_cli("--input", invalid_input, "--min-pass-rate-delta", "0")
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("validation error", invalid.stderr.lower())

        missing = self.run_cli("--input", self.root / "absent.json", "--min-pass-rate-delta", "0")
        self.assertEqual(missing.returncode, 3)
        self.assertIn("runtime error", missing.stderr.lower())


if __name__ == "__main__":
    unittest.main()
