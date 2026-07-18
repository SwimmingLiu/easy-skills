import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE_ROOT / "scripts" / "update_lifecycle.py"
COMMON = PACKAGE_ROOT / "scripts" / "lifecycle_common.py"


class LifecycleCliTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.state_file = self.root / "lifecycle.json"

    def run_cli(self, *arguments, check=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"CLI failed: {result.stderr}")
        return result

    def init(self):
        self.run_cli("init", "--file", self.state_file, "--skill", "sample-skill")
        return self.read_state()

    def transition(
        self,
        target,
        operation="create",
        evidence=(),
        decision=None,
        gates=(),
        artifacts=(),
        confirm=False,
        check=True,
    ):
        arguments = [
            "transition",
            "--file",
            self.state_file,
            "--to",
            target,
            "--operation",
            operation,
        ]
        for reference in evidence:
            arguments.extend(("--evidence", reference))
        if decision is not None:
            arguments.extend(("--decision", decision))
        for gate in gates:
            arguments.extend(("--gate", gate))
        for artifact in artifacts:
            arguments.extend(("--artifact", artifact))
        if confirm:
            arguments.append("--confirm")
        return self.run_cli(*arguments, check=check)

    def read_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def write_state(self, state):
        self.state_file.write_text(json.dumps(state), encoding="utf-8")

    def assert_invalid_document(self, state, expected_message):
        self.write_state(state)
        result = self.run_cli("show", "--file", self.state_file, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def advance_to_release_ready(self):
        path = (
            ("researched", "discover"),
            ("draft", "create"),
            ("reviewed", "review"),
            ("evaluated", "evaluate"),
            ("release-ready", "review"),
        )
        for state, operation in path:
            self.transition(state, operation, (f"evidence/{state}.json",))

    def test_init_creates_versioned_intake_document(self):
        state = self.init()

        self.assertEqual(state["schema_version"], 1)
        self.assertEqual(state["skill"], "sample-skill")
        self.assertEqual(state["state"], "intake")
        self.assertEqual(state["version"], 1)
        self.assertIsNone(state["resume_state"])
        self.assertEqual(state["runs"], [])
        self.assertEqual(state["gates"], {})
        self.assertEqual(state["artifacts"], [])

    def test_legal_intake_to_researched_requires_discovery_evidence(self):
        self.init()
        self.transition("researched", "discover", ("research/inventory.json",))

        state = self.read_state()
        self.assertEqual(state["state"], "researched")
        self.assertEqual(state["runs"][-1]["operation"], "discover")
        self.assertEqual(
            state["runs"][-1]["evidence_refs"], ["research/inventory.json"]
        )

    def test_illegal_transition_is_rejected_without_changing_file(self):
        self.init()
        before = self.state_file.read_bytes()

        result = self.transition(
            "active", "maintain", ("evidence/release.json",), confirm=True, check=False
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed", result.stderr)
        self.assertEqual(self.state_file.read_bytes(), before)

    def test_maturity_states_require_evidence(self):
        self.init()
        transitions = (
            ("researched", "discover", False),
            ("draft", "create", False),
            ("reviewed", "review", False),
            ("evaluated", "evaluate", False),
            ("release-ready", "review", False),
            ("active", "maintain", True),
            ("retired", "maintain", True),
        )
        for target, operation, confirm in transitions:
            with self.subTest(target=target):
                before = self.state_file.read_bytes()
                result = self.transition(
                    target, operation, confirm=confirm, check=False
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("evidence", result.stderr.lower())
                self.assertEqual(self.state_file.read_bytes(), before)
                self.transition(
                    target,
                    operation,
                    (f"evidence/{target}.json",),
                    confirm=confirm,
                )

    def test_empty_evidence_reference_does_not_satisfy_guard(self):
        self.init()
        before = self.state_file.read_bytes()

        result = self.transition("researched", "discover", ("",), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-empty", result.stderr)
        self.assertEqual(self.state_file.read_bytes(), before)

    def test_active_retired_and_rollback_require_confirmation(self):
        self.init()
        self.advance_to_release_ready()

        active = self.transition(
            "active", "maintain", ("evidence/release.json",), check=False
        )
        self.assertNotEqual(active.returncode, 0)
        self.assertIn("--confirm", active.stderr)
        self.transition(
            "active", "maintain", ("evidence/release.json",), confirm=True
        )

        retired = self.transition(
            "retired", "maintain", ("evidence/retire.json",), check=False
        )
        self.assertNotEqual(retired.returncode, 0)
        self.assertIn("--confirm", retired.stderr)

        rollback = self.run_cli(
            "rollback",
            "--file",
            self.state_file,
            "--to-version",
            "2",
            "--evidence",
            "evidence/regression.json",
            check=False,
        )
        self.assertNotEqual(rollback.returncode, 0)
        self.assertIn("--confirm", rollback.stderr)

    def test_exception_state_resumes_only_to_preserved_state(self):
        self.init()
        self.transition("researched", "discover", ("evidence/research.json",))
        self.transition("needs-input", "review", decision="owner clarification needed")
        paused = self.read_state()
        self.assertEqual(paused["resume_state"], "researched")

        rejected = self.transition(
            "draft", "create", ("evidence/draft.md",), check=False
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("resume", rejected.stderr.lower())
        self.assertEqual(self.read_state(), paused)

        self.transition("researched", "review", decision="clarification received")
        self.assertIsNone(self.read_state()["resume_state"])

        self.transition("blocked", "review", decision="external dependency unavailable")
        self.assertEqual(self.read_state()["resume_state"], "researched")

    def test_every_transition_run_has_auditable_fields(self):
        self.init()
        self.transition(
            "researched",
            "discover",
            ("evidence/research.json",),
            decision="sources are sufficient",
        )

        run = self.read_state()["runs"][-1]
        required = {
            "run_id",
            "timestamp",
            "operation",
            "previous_state",
            "current_state",
            "evidence_refs",
            "decision",
            "version",
        }
        self.assertTrue(required.issubset(run))
        self.assertEqual(run["previous_state"], "intake")
        self.assertEqual(run["current_state"], "researched")
        self.assertEqual(run["version"], 2)

    def test_gates_and_artifacts_are_recorded_and_preserved(self):
        self.init()
        self.transition(
            "researched",
            "discover",
            ("evidence/research.json",),
            gates=("discovery=passed", "owner-review=pending"),
            artifacts=("reports/research.md",),
        )
        self.transition(
            "draft", "create", ("evidence/draft.md",), artifacts=("SKILL.md",)
        )

        state = self.read_state()
        self.assertEqual(
            state["gates"], {"discovery": "passed", "owner-review": "pending"}
        )
        self.assertEqual(state["artifacts"], ["reports/research.md", "SKILL.md"])

    def test_duplicate_artifact_arguments_are_normalized(self):
        self.init()
        self.transition(
            "researched",
            "discover",
            ("evidence/research.json",),
            artifacts=("reports/research.md", "reports/research.md"),
        )

        self.assertEqual(self.read_state()["artifacts"], ["reports/research.md"])

    def test_invalid_artifact_argument_cannot_create_invalid_history(self):
        self.init()
        before = self.state_file.read_bytes()

        result = self.transition(
            "researched",
            "discover",
            ("evidence/research.json",),
            artifacts=("",),
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("artifacts", result.stderr)
        self.assertEqual(self.state_file.read_bytes(), before)

    def test_rollback_restores_prior_lifecycle_snapshot_only(self):
        self.init()
        skill_file = self.root / "SKILL.md"
        skill_file.write_text("user-authored content\n", encoding="utf-8")
        self.transition(
            "researched",
            "discover",
            ("evidence/research.json",),
            gates=("discovery=passed",),
            artifacts=("reports/research.md",),
        )
        self.transition(
            "draft",
            "create",
            ("evidence/draft.md",),
            gates=("draft=passed",),
            artifacts=("SKILL.md",),
        )

        self.run_cli(
            "rollback",
            "--file",
            self.state_file,
            "--to-version",
            "2",
            "--evidence",
            "evidence/regression.json",
            "--confirm",
        )

        state = self.read_state()
        self.assertEqual(state["state"], "researched")
        self.assertEqual(state["gates"], {"discovery": "passed"})
        self.assertEqual(state["artifacts"], ["reports/research.md"])
        self.assertEqual(state["runs"][-1]["operation"], "rollback")
        self.assertEqual(state["runs"][-1]["event"], "rolled-back")
        self.assertEqual(skill_file.read_text(encoding="utf-8"), "user-authored content\n")

    def test_rolled_back_is_event_vocabulary_not_persistent_state(self):
        self.init()
        state = self.read_state()
        state["state"] = "rolled-back"
        self.write_state(state)

        result = self.run_cli("show", "--file", self.state_file, check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("state", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

        scripts_path = str(PACKAGE_ROOT / "scripts")
        sys.path.insert(0, scripts_path)
        self.addCleanup(sys.path.remove, scripts_path)
        spec = importlib.util.spec_from_file_location("update_lifecycle", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertNotIn("rolled-back", module.ALLOWED_TRANSITIONS)

    def test_malformed_top_level_documents_are_rejected_without_traceback(self):
        self.init()
        valid = self.read_state()
        cases = (
            ("schema_version", True, "schema_version"),
            ("schema_version", "1", "schema_version"),
            ("schema_version", 2, "schema_version"),
            ("skill", "", "skill"),
            ("skill", 7, "skill"),
            ("state", "unknown", "state"),
            ("state", 7, "state"),
            ("resume_state", "researched", "resume_state"),
            ("version", True, "version"),
            ("version", 0, "version"),
            ("version", "1", "version"),
            ("runs", {}, "runs"),
            ("gates", [], "gates"),
            ("gates", {"review": 1}, "gates"),
            ("artifacts", {}, "artifacts"),
            ("artifacts", [1], "artifacts"),
        )
        for field, value, expected_message in cases:
            with self.subTest(field=field, value=value):
                malformed = copy.deepcopy(valid)
                malformed[field] = value
                self.write_state(malformed)

                result = self.run_cli("show", "--file", self.state_file, check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_exception_resume_state_invariants_are_validated(self):
        self.init()
        valid = self.read_state()
        cases = (
            ("blocked", None),
            ("needs-input", "rolled-back"),
            ("blocked", "needs-input"),
        )
        for state, resume_state in cases:
            with self.subTest(state=state, resume_state=resume_state):
                malformed = copy.deepcopy(valid)
                malformed["state"] = state
                malformed["resume_state"] = resume_state
                self.write_state(malformed)

                result = self.run_cli("show", "--file", self.state_file, check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("resume_state", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_malformed_runs_and_snapshots_are_rejected_without_traceback(self):
        self.init()
        self.transition("researched", "discover", ("evidence/research.json",))
        valid = self.read_state()
        base_run = valid["runs"][0]
        run_cases = (
            ("run object", "not-an-object", "runs[0]"),
            ("missing run_id", {key: value for key, value in base_run.items() if key != "run_id"}, "run_id"),
            ("run_id type", {**base_run, "run_id": 1}, "run_id"),
            ("timestamp type", {**base_run, "timestamp": 1}, "timestamp"),
            ("operation type", {**base_run, "operation": 1}, "operation"),
            ("previous state", {**base_run, "previous_state": "rolled-back"}, "previous_state"),
            ("current state", {**base_run, "current_state": "rolled-back"}, "current_state"),
            ("evidence list", {**base_run, "evidence_refs": {}}, "evidence_refs"),
            ("evidence item", {**base_run, "evidence_refs": [1]}, "evidence_refs"),
            ("decision type", {**base_run, "decision": 1}, "decision"),
            ("run version bool", {**base_run, "version": True}, "version"),
            ("event value", {**base_run, "event": "other"}, "event"),
            ("snapshot type", {**base_run, "snapshot": []}, "snapshot"),
            (
                "snapshot state",
                {**base_run, "snapshot": {**base_run["snapshot"], "state": "rolled-back"}},
                "snapshot.state",
            ),
            (
                "snapshot resume",
                {**base_run, "snapshot": {**base_run["snapshot"], "resume_state": "draft"}},
                "snapshot.resume_state",
            ),
            (
                "snapshot gates",
                {**base_run, "snapshot": {**base_run["snapshot"], "gates": []}},
                "snapshot.gates",
            ),
            (
                "snapshot artifacts",
                {**base_run, "snapshot": {**base_run["snapshot"], "artifacts": {}}},
                "snapshot.artifacts",
            ),
        )
        for label, run, expected_message in run_cases:
            with self.subTest(case=label):
                malformed = copy.deepcopy(valid)
                malformed["runs"] = [run]
                self.write_state(malformed)

                result = self.run_cli("show", "--file", self.state_file, check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_every_persisted_run_requires_a_snapshot(self):
        self.init()
        self.transition("researched", "discover", ("evidence/research.json",))
        malformed = self.read_state()
        del malformed["runs"][0]["snapshot"]

        self.assert_invalid_document(malformed, "snapshot")

    def test_run_ids_must_be_unique(self):
        self.init()
        self.transition("researched", "discover", ("evidence/research.json",))
        self.transition("draft", "create", ("evidence/draft.md",))
        malformed = self.read_state()
        malformed["runs"][1]["run_id"] = malformed["runs"][0]["run_id"]

        self.assert_invalid_document(malformed, "run_id")

    def test_persisted_artifact_references_must_be_unique(self):
        self.init()
        malformed = self.read_state()
        malformed["artifacts"] = ["report.md", "report.md"]

        self.assert_invalid_document(malformed, "artifacts")

    def test_run_versions_are_contiguous_from_two_and_match_document(self):
        self.init()
        self.transition("researched", "discover", ("evidence/research.json",))
        self.transition("draft", "create", ("evidence/draft.md",))
        valid = self.read_state()
        cases = []

        duplicate = copy.deepcopy(valid)
        duplicate["runs"][1]["version"] = 2
        cases.append(("duplicate", duplicate, "runs[1].version"))

        gap = copy.deepcopy(valid)
        gap["runs"][1]["version"] = 4
        gap["version"] = 4
        cases.append(("gap", gap, "runs[1].version"))

        wrong_start = copy.deepcopy(valid)
        wrong_start["runs"][0]["version"] = 3
        wrong_start["runs"][1]["version"] = 4
        wrong_start["version"] = 4
        cases.append(("wrong start", wrong_start, "runs[0].version"))

        top_mismatch = copy.deepcopy(valid)
        top_mismatch["version"] = 4
        cases.append(("top mismatch", top_mismatch, "document version"))

        no_runs = copy.deepcopy(valid)
        no_runs["runs"] = []
        no_runs["version"] = 2
        cases.append(("empty history", no_runs, "document version"))

        for label, malformed, expected_message in cases:
            with self.subTest(case=label):
                self.assert_invalid_document(malformed, expected_message)

    def test_run_snapshots_match_the_state_history(self):
        self.init()
        self.transition(
            "researched",
            "discover",
            ("evidence/research.json",),
            gates=("discovery=passed",),
            artifacts=("research.md",),
        )
        self.transition("draft", "create", ("evidence/draft.md",))
        valid = self.read_state()

        wrong_current = copy.deepcopy(valid)
        wrong_current["runs"][0]["snapshot"]["state"] = "draft"

        broken_chain = copy.deepcopy(valid)
        broken_chain["runs"][1]["previous_state"] = "intake"

        wrong_final_snapshot = copy.deepcopy(valid)
        wrong_final_snapshot["runs"][1]["snapshot"]["artifacts"] = []

        cases = (
            ("current state", wrong_current, "snapshot.state"),
            ("state chain", broken_chain, "previous_state"),
            ("final snapshot", wrong_final_snapshot, "final snapshot"),
        )
        for label, malformed, expected_message in cases:
            with self.subTest(case=label):
                self.assert_invalid_document(malformed, expected_message)

    def test_empty_history_must_match_exact_initialized_metadata(self):
        self.init()
        valid = self.read_state()
        cases = (
            ("state", {**valid, "state": "researched"}),
            ("gates", {**valid, "gates": {"review": "passed"}}),
            ("artifacts", {**valid, "artifacts": ["report.md"]}),
        )
        for label, malformed in cases:
            with self.subTest(case=label):
                self.assert_invalid_document(malformed, "initialized metadata")

    def test_structurally_linked_illegal_transitions_are_rejected(self):
        self.init()
        self.transition("researched", "discover", ("evidence/research.json",))
        one_run = self.read_state()
        forged_intake_active = copy.deepcopy(one_run)
        forged_intake_active["state"] = "active"
        forged_intake_active["runs"][0]["current_state"] = "active"
        forged_intake_active["runs"][0]["snapshot"]["state"] = "active"

        self.transition("draft", "create", ("evidence/draft.md",))
        two_runs = self.read_state()
        forged_researched_active = copy.deepcopy(two_runs)
        forged_researched_active["state"] = "active"
        forged_researched_active["runs"][1]["current_state"] = "active"
        forged_researched_active["runs"][1]["snapshot"]["state"] = "active"

        for label, malformed in (
            ("intake to active", forged_intake_active),
            ("researched to active", forged_researched_active),
        ):
            with self.subTest(case=label):
                self.assert_invalid_document(malformed, "not allowed")

    def test_legal_exception_resume_history_replays(self):
        self.init()
        self.transition("researched", "discover", ("evidence/research.json",))
        self.transition("needs-input", "review", decision="owner input required")
        self.transition("researched", "review", decision="owner input received")
        self.transition("blocked", "review", decision="dependency unavailable")
        self.transition("researched", "review", decision="dependency restored")

        result = self.run_cli("show", "--file", self.state_file)

        self.assertEqual(json.loads(result.stdout)["state"], "researched")

    def test_rollback_history_names_and_matches_prior_snapshot(self):
        self.init()
        self.transition(
            "researched",
            "discover",
            ("evidence/research.json",),
            gates=("discovery=passed",),
        )
        self.transition("draft", "create", ("evidence/draft.md",))
        self.run_cli(
            "rollback",
            "--file",
            self.state_file,
            "--to-version",
            "2",
            "--evidence",
            "evidence/regression.json",
            "--confirm",
        )

        state = self.read_state()
        self.assertIn("restored_version", state["runs"][-1])
        self.assertEqual(state["runs"][-1]["restored_version"], 2)
        self.run_cli("show", "--file", self.state_file)

        forged = copy.deepcopy(state)
        forged["runs"][-1]["restored_version"] = 1
        self.assert_invalid_document(forged, "restored_version")

    def test_atomic_writer_uses_sibling_temporary_file_and_replace(self):
        spec = importlib.util.spec_from_file_location("lifecycle_common", COMMON)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        destination = self.root / "nested" / "lifecycle.json"
        destination.parent.mkdir()

        real_replace = module.os.replace
        calls = []

        def recording_replace(source, target):
            calls.append((Path(source), Path(target)))
            return real_replace(source, target)

        with mock.patch.object(module.os, "replace", side_effect=recording_replace):
            module.atomic_write_json(destination, {"state": "intake"})

        self.assertEqual(len(calls), 1)
        source, target = calls[0]
        self.assertEqual(source.parent, destination.parent)
        self.assertEqual(target, destination)
        self.assertFalse(source.exists())

    def test_show_prints_deterministic_json(self):
        self.init()

        first = self.run_cli("show", "--file", self.state_file).stdout
        second = self.run_cli("show", "--file", self.state_file).stdout

        self.assertEqual(first, second)
        self.assertEqual(first, json.dumps(self.read_state(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
