import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[2]
SCRIPTS = PACKAGE_ROOT / "scripts"


class WorkflowIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.skill_root = self.root / "skills" / "example-skill"
        self.skill_root.mkdir(parents=True)
        self.skill_file = self.skill_root / "SKILL.md"
        self.skill_file.write_text(
            """---
name: example-skill
description: Use when a user needs a deterministic example response.
---

# Example Skill

Read [the procedure](references/procedure.md), then return the result.
""",
            encoding="utf-8",
        )
        references = self.skill_root / "references"
        references.mkdir()
        (references / "procedure.md").write_text(
            "# Procedure\n\nReturn the requested deterministic result.\n",
            encoding="utf-8",
        )

    def run_cli(self, script, *arguments, expected=0):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / script), *map(str, arguments)],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            expected,
            f"{script} returned {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def transition(self, lifecycle_file, target, operation, evidence, *extra):
        self.run_cli(
            "update_lifecycle.py",
            "transition",
            "--file",
            lifecycle_file,
            "--to",
            target,
            "--operation",
            operation,
            "--evidence",
            evidence,
            *extra,
        )

    def test_complete_evidence_backed_workflow_rejects_candidate_and_rolls_back(self):
        inventory_file = self.root / "artifacts" / "inventory.json"
        self.run_cli(
            "inventory_skills.py",
            "--root",
            self.root / "skills",
            "--output",
            inventory_file,
            "--source",
            "https://github.com/example/skills",
            "--ref",
            "0123456789abcdef",
            "--license",
            "MIT",
            "--host",
            "codex",
        )
        inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
        self.assertEqual(len(inventory["skills"]), 1)
        record = inventory["skills"][0]
        self.assertEqual(record["source"], "https://github.com/example/skills")
        self.assertEqual(record["ref"], "0123456789abcdef")
        self.assertEqual(record["path"], "example-skill/SKILL.md")
        self.assertEqual(
            record["sha256"], hashlib.sha256(self.skill_file.read_bytes()).hexdigest()
        )

        validation_result = self.run_cli("validate_skill.py", self.skill_root)
        validation = json.loads(validation_result.stdout)
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["findings"], [])
        validation_file = self.root / "artifacts" / "validation.json"
        validation_file.write_text(validation_result.stdout, encoding="utf-8")

        baseline_file = self.root / "artifacts" / "baseline.json"
        baseline_file.write_text(
            json.dumps({"case_id": "workflow-case", "variant": "baseline"}),
            encoding="utf-8",
        )
        release_check = self.root / "artifacts" / "release-check.md"
        release_check.write_text(
            "# Release check\n\nLicense, compatibility, safety, and rollback verified.\n",
            encoding="utf-8",
        )

        lifecycle_file = self.root / "artifacts" / "lifecycle.json"
        self.run_cli(
            "update_lifecycle.py",
            "init",
            "--file",
            lifecycle_file,
            "--skill",
            "example-skill",
        )
        transitions = (
            ("researched", "discover", inventory_file),
            ("draft", "create", self.skill_file),
            ("reviewed", "review", validation_file),
            ("evaluated", "evaluate", baseline_file),
            ("release-ready", "maintain", release_check),
        )
        for target, operation, evidence in transitions:
            self.assertTrue(evidence.exists(), f"missing transition evidence: {evidence}")
            self.transition(lifecycle_file, target, operation, evidence)

        eval_input = self.root / "artifacts" / "eval-input.json"
        eval_input.write_text(
            json.dumps(
                [
                    {
                        "case_id": "workflow-case",
                        "variant": "baseline",
                        "assertions": [
                            {"id": "quality", "passed": True},
                            {"id": "safe", "passed": True, "prohibited_action": True},
                        ],
                        "duration_ms": 100,
                        "total_tokens": 100,
                    },
                    {
                        "case_id": "workflow-case",
                        "variant": "candidate",
                        "assertions": [
                            {"id": "quality", "passed": False},
                            {"id": "safe", "passed": False, "prohibited_action": True},
                        ],
                        "duration_ms": 120,
                        "total_tokens": 110,
                    },
                ]
            ),
            encoding="utf-8",
        )
        evaluation_json = self.root / "artifacts" / "evaluation.json"
        evaluation_markdown = self.root / "artifacts" / "evaluation.md"
        rejected = self.run_cli(
            "aggregate_evals.py",
            "--input",
            eval_input,
            "--min-pass-rate-delta",
            "0",
            "--json-output",
            evaluation_json,
            "--markdown-output",
            evaluation_markdown,
            expected=1,
        )
        report = json.loads(rejected.stdout)
        self.assertFalse(report["decision"]["accepted"])
        self.assertEqual(report["decision"]["candidate_prohibited_action_failures"], 1)
        self.assertIn("Decision: **rejected**", evaluation_markdown.read_text(encoding="utf-8"))

        self.transition(
            lifecycle_file,
            "changes-required",
            "optimize",
            evaluation_json,
            "--decision",
            "Reject candidate after regression gate; restore release-ready snapshot.",
            "--gate",
            "candidate=rejected",
            "--artifact",
            evaluation_markdown,
        )
        before_rollback = json.loads(
            self.run_cli("update_lifecycle.py", "show", "--file", lifecycle_file).stdout
        )
        self.assertEqual(before_rollback["state"], "changes-required")
        failed_run = before_rollback["runs"][-1]
        self.assertEqual(failed_run["evidence_refs"], [str(evaluation_json)])
        self.assertIn("Reject candidate", failed_run["decision"])

        rollback_evidence = self.root / "artifacts" / "rollback-decision.md"
        rollback_evidence.write_text(
            "# Rollback decision\n\nCandidate rejected by predeclared regression gates.\n",
            encoding="utf-8",
        )
        self.run_cli(
            "update_lifecycle.py",
            "rollback",
            "--file",
            lifecycle_file,
            "--to-version",
            "6",
            "--evidence",
            rollback_evidence,
            "--confirm",
        )
        restored = json.loads(
            self.run_cli("update_lifecycle.py", "show", "--file", lifecycle_file).stdout
        )
        self.assertEqual(restored["state"], "release-ready")
        self.assertEqual(restored["gates"], {})
        self.assertEqual(restored["artifacts"], [])
        self.assertEqual(restored["runs"][-1]["event"], "rolled-back")
        self.assertEqual(restored["runs"][-1]["restored_version"], 6)
        self.assertEqual(restored["runs"][-1]["evidence_refs"], [str(rollback_evidence)])
        self.assertIn(failed_run, restored["runs"])

    def test_readme_documents_meta_skill_installation(self):
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("### Meta Skills", readme)
        self.assertIn("skills/meta/skill-lifecycle/SKILL.md", readme)
        self.assertIn(
            "npx skills add ./skills/meta/skill-lifecycle -g -y",
            readme,
        )
        self.assertIn(
            "npx skills add https://github.com/SwimmingLiu/easy-skills@skills/meta/skill-lifecycle -g -y",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
