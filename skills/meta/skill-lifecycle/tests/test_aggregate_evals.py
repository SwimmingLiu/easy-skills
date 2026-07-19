import importlib.util
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
                    {"id": "quality", "passed": True},
                    {"id": "safe", "passed": True, "prohibited_action": True},
                ],
                "duration_ms": 140,
                "total_tokens": 120,
            },
            {
                "case_id": "case-a",
                "variant": "baseline",
                "assertions": [
                    {"id": "quality", "passed": False},
                    {"id": "safe", "passed": True, "prohibited_action": True},
                ],
                "duration_ms": 100,
                "total_tokens": 100,
            },
            {
                "case_id": "case-a",
                "variant": "candidate",
                "assertions": [
                    {"id": "quality", "passed": True},
                    {"id": "safe", "passed": True, "prohibited_action": True},
                ],
                "duration_ms": 120,
                "total_tokens": 90,
            },
            {
                "case_id": "case-b",
                "variant": "baseline",
                "assertions": [
                    {"id": "quality", "passed": False},
                    {"id": "safe", "passed": False, "prohibited_action": True},
                ],
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
            [{"case_id": "x", "variant": "other", "assertions": [{"id": "a", "passed": True}], "duration_ms": 1, "total_tokens": 1}],
            [{"case_id": "x", "variant": "candidate", "assertions": [], "duration_ms": 1, "total_tokens": 1}],
            [{"case_id": "x", "variant": "candidate", "assertions": [{"id": "a", "passed": "yes"}], "duration_ms": 1, "total_tokens": 1}],
            [{"case_id": "x", "variant": "candidate", "assertions": [{"id": "a", "passed": True}], "duration_ms": -1, "total_tokens": 1}],
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

    def test_assertions_have_strict_unique_ids_and_matching_pair_sets(self):
        module = load_module()
        invalid_assertions = (
            [True],
            [{"passed": True}],
            [{"id": "a", "passed": True, "unknown": False}],
            [{"id": "a", "passed": False, "prohibited_actions": True}],
            [{"id": "a", "passed": True}, {"id": "a", "passed": False}],
        )
        for assertions in invalid_assertions:
            records = json.loads(json.dumps(self.records))
            records[0]["assertions"] = assertions
            with self.subTest(assertions=assertions), self.assertRaises(module.ValidationError):
                module.aggregate(records, min_pass_rate_delta=0)

        mismatched = json.loads(json.dumps(self.records))
        mismatched[0]["assertions"][0]["id"] = "different"
        with self.assertRaisesRegex(module.ValidationError, "assertion ids"):
            module.aggregate(mismatched, min_pass_rate_delta=0)

    def test_pair_assertion_definitions_must_match_including_safety_label(self):
        module = load_module()
        for baseline_prohibited, candidate_prohibited in ((True, False), (False, True)):
            records = json.loads(json.dumps(self.records))
            records[3]["assertions"][1]["prohibited_action"] = baseline_prohibited
            records[0]["assertions"][1]["prohibited_action"] = candidate_prohibited
            with self.subTest(
                baseline=baseline_prohibited, candidate=candidate_prohibited
            ), self.assertRaisesRegex(module.ValidationError, "assertion definitions"):
                module.aggregate(records, min_pass_rate_delta=0)

    def test_records_use_field_whitelist_and_json_rejects_duplicate_keys_at_any_depth(self):
        module = load_module()
        records = json.loads(json.dumps(self.records))
        records[0]["unexpected"] = "ignored before hardening"
        with self.assertRaisesRegex(module.ValidationError, "unknown fields"):
            module.aggregate(records, min_pass_rate_delta=0)

        duplicate_documents = (
            '[{"case_id":"a","case_id":"b"}]',
            '[{"case_id":"a","variant":"candidate","assertions":'
            '[{"id":"x","id":"y","passed":true}],"duration_ms":1,'
            '"total_tokens":1}]',
            '{"records":[],"records":[]}',
        )
        for index, document in enumerate(duplicate_documents):
            path = self.root / f"duplicate-{index}.json"
            path.write_text(document, encoding="utf-8")
            result = self.run_cli(
                "--input", path, "--min-pass-rate-delta", "0"
            )
            with self.subTest(index=index, stderr=result.stderr):
                self.assertEqual(result.returncode, 2)
                self.assertIn("duplicate JSON key", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_rejects_markdown_injection_and_enforces_resource_limits(self):
        module = load_module()
        for unsafe in (
            "line\nbreak",
            "cell|break",
            "line\rbreak",
            "[active](link)",
            "space break",
            "`code`",
            "path/segment",
        ):
            records = json.loads(json.dumps(self.records))
            records[0]["case_id"] = unsafe
            records[3]["case_id"] = unsafe
            with self.subTest(case_id=unsafe), self.assertRaises(module.ValidationError):
                module.aggregate(records, min_pass_rate_delta=0)

        too_many_assertions = json.loads(json.dumps(self.records))
        too_many_assertions[0]["assertions"] = [
            {"id": f"a-{index}", "passed": True}
            for index in range(module.MAX_ASSERTIONS_PER_RECORD + 1)
        ]
        with self.assertRaisesRegex(module.ValidationError, "assertions limit"):
            module.aggregate(too_many_assertions, min_pass_rate_delta=0)

        too_many_cases = []
        for index in range(module.MAX_CASES + 1):
            for variant in ("baseline", "candidate"):
                too_many_cases.append(
                    {
                        "case_id": f"case-{index}",
                        "variant": variant,
                        "assertions": [{"id": "a", "passed": True}],
                        "duration_ms": 1,
                        "total_tokens": 1,
                    }
                )
        with self.assertRaisesRegex(module.ValidationError, "case limit"):
            module.aggregate(too_many_cases, min_pass_rate_delta=0)

        long_string = "x" * (module.MAX_STRING_LENGTH + 1)
        too_long = json.loads(json.dumps(self.records))
        too_long[0]["case_id"] = long_string
        too_long[3]["case_id"] = long_string
        with self.assertRaisesRegex(module.ValidationError, "string length limit"):
            module.aggregate(too_long, min_pass_rate_delta=0)

    def test_cli_rejects_oversized_input_output_and_huge_json_numbers(self):
        module = load_module()
        oversized = self.root / "oversized.json"
        oversized.write_bytes(b" " * (module.MAX_INPUT_BYTES + 1))
        result = self.run_cli("--input", oversized, "--min-pass-rate-delta", "0")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

        huge_integer = self.root / "huge.json"
        huge_integer.write_text("[" + "9" * 5000 + "]", encoding="utf-8")
        result = self.run_cli("--input", huge_integer, "--min-pass-rate-delta", "0")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

        input_path = self.write_input()
        with mock.patch.object(module, "MAX_OUTPUT_BYTES", 10):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = module.main(["--input", str(input_path), "--min-pass-rate-delta", "0"])
        self.assertEqual(code, 2)
        self.assertIn("output limit", stderr.getvalue())

        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn(f"input bytes: {module.MAX_INPUT_BYTES}", help_result.stdout)
        self.assertIn(f"cases: {module.MAX_CASES}", help_result.stdout)

    def test_unexpected_exceptions_are_runtime_failures_without_traceback(self):
        module = load_module()
        stderr = io.StringIO()
        with mock.patch.object(module, "_load_records", side_effect=RuntimeError("boom")):
            with contextlib.redirect_stderr(stderr):
                code = module.main(["--input", "unused", "--min-pass-rate-delta", "0"])
        self.assertEqual(code, 3)
        self.assertEqual(stderr.getvalue().strip(), "runtime error: boom")

    def test_raw_value_and_overflow_errors_are_validation_failures(self):
        module = load_module()
        for failure in (ValueError("bad value"), OverflowError("too large")):
            stderr = io.StringIO()
            with mock.patch.object(module, "_load_records", side_effect=failure):
                with contextlib.redirect_stderr(stderr):
                    code = module.main(
                        ["--input", "unused", "--min-pass-rate-delta", "0"]
                    )
            self.assertEqual(code, 2)
            self.assertIn("validation error", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_output_paths_are_distinct_non_symlinks_and_prepare_before_commit(self):
        module = load_module()
        first = self.root / "first.txt"
        first.write_text("old-first", encoding="utf-8")
        second_target = self.root / "target.txt"
        second_target.write_text("old-second", encoding="utf-8")
        second = self.root / "second.txt"
        try:
            second.symlink_to(second_target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")

        with self.assertRaises(module.ValidationError):
            module.write_reports(first, "new", first, "new")
        with self.assertRaises(OSError):
            module.write_reports(first, "new-first", second, "new-second")
        self.assertEqual(first.read_text(encoding="utf-8"), "old-first")
        self.assertEqual(second_target.read_text(encoding="utf-8"), "old-second")

    def test_dual_output_rolls_back_first_when_second_replace_fails(self):
        module = load_module()
        first = self.root / "first.json"
        second = self.root / "second.md"
        first.write_text("old-first", encoding="utf-8")
        second.write_text("old-second", encoding="utf-8")
        real_replace = os.replace
        commit_calls = 0

        def fail_second_commit(source, destination):
            nonlocal commit_calls
            if Path(source).name.endswith(".new"):
                commit_calls += 1
                if commit_calls == 2:
                    raise OSError("injected second replace failure")
            return real_replace(source, destination)

        with mock.patch.object(module.os, "replace", side_effect=fail_second_commit):
            with self.assertRaisesRegex(OSError, "second replace"):
                module.write_reports(first, "new-first", second, "new-second")

        self.assertEqual(first.read_text(encoding="utf-8"), "old-first")
        self.assertEqual(second.read_text(encoding="utf-8"), "old-second")
        self.assertFalse(any(self.root.glob(".*.new")))
        self.assertFalse(any(self.root.glob(".*.backup")))

    def test_committed_outputs_report_uncertain_directory_durability(self):
        module = load_module()
        first = self.root / "first.json"
        second = self.root / "second.md"

        # Use the module's directory-sync helper as the stable injection point.
        with mock.patch.object(module, "_fsync_directory", side_effect=OSError("injected directory sync failure")):
            status = module.write_reports(first, "new-first", second, "new-second")
        self.assertFalse(status["durable"])
        self.assertTrue(status["cleanup_complete"])
        self.assertEqual(first.read_text(encoding="utf-8"), "new-first")
        self.assertEqual(second.read_text(encoding="utf-8"), "new-second")

    def test_output_parent_must_preexist_and_is_not_created_implicitly(self):
        module = load_module()
        missing_parent = self.root / "missing" / "report.json"
        with self.assertRaisesRegex(OSError, "parent directory"):
            module.write_reports(missing_parent, "new")
        self.assertFalse(missing_parent.parent.exists())

    def test_post_commit_cleanup_failure_warns_without_changing_decision_exit(self):
        module = load_module()
        input_path = self.write_input()
        first = self.root / "first.json"
        second = self.root / "second.md"
        first.write_text("old-first", encoding="utf-8")
        second.write_text("old-second", encoding="utf-8")
        real_unlink = os.unlink
        backup_attempts = 0

        def reject_backup_cleanup(path, *args, **kwargs):
            nonlocal backup_attempts
            if str(path).endswith(".backup"):
                backup_attempts += 1
                raise OSError("injected backup cleanup failure")
            return real_unlink(path, *args, **kwargs)

        def run_with_threshold(threshold):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.object(
                module.os, "unlink", side_effect=reject_backup_cleanup
            ):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
                    stderr
                ):
                    code = module.main(
                        [
                            "--input",
                            str(input_path),
                            "--min-pass-rate-delta",
                            threshold,
                            "--json-output",
                            str(first),
                            "--markdown-output",
                            str(second),
                        ]
                    )
            return code, stdout.getvalue(), stderr.getvalue()

        accepted = run_with_threshold("0")
        rejected = run_with_threshold("0.9")
        self.assertEqual(accepted[0], 0)
        self.assertEqual(rejected[0], 1)
        self.assertEqual(backup_attempts, 4)
        self.assertTrue(json.loads(accepted[1])["decision"]["accepted"])
        self.assertFalse(json.loads(rejected[1])["decision"]["accepted"])
        for stderr in (accepted[2], rejected[2]):
            self.assertIn("committed", stderr)
            self.assertIn("cleanup is incomplete", stderr)
        self.assertEqual(first.read_text(encoding="utf-8")[:1], "{")
        self.assertIn("# Evaluation comparison", second.read_text(encoding="utf-8"))

    def test_cli_warns_when_reports_are_committed_but_not_directory_durable(self):
        module = load_module()
        input_path = self.write_input()
        first = self.root / "first.json"
        second = self.root / "second.md"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(
            module,
            "_fsync_directory",
            side_effect=OSError("injected directory sync failure"),
        ):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = module.main(
                    [
                        "--input",
                        str(input_path),
                        "--min-pass-rate-delta",
                        "0",
                        "--json-output",
                        str(first),
                        "--markdown-output",
                        str(second),
                    ]
                )
        self.assertEqual(code, 0)
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())
        self.assertIn("committed but directory durability is uncertain", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
