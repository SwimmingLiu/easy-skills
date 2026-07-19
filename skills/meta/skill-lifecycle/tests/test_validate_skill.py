import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE_ROOT / "scripts" / "validate_skill.py"


class ValidateSkillCliTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def run_cli(self, skill_directory, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(skill_directory), *map(str, arguments)],
            check=False,
            capture_output=True,
            text=True,
        )

    def create_skill(self, name="clean-skill", body="# Clean\n", directory_name=None):
        directory = self.root / (directory_name or name)
        directory.mkdir(parents=True, exist_ok=True)
        content = f"---\nname: {name}\ndescription: Performs a bounded task.\n---\n{body}"
        (directory / "SKILL.md").write_text(content, encoding="utf-8")
        return directory

    def validate(self, skill_directory, *arguments):
        result = self.run_cli(skill_directory, *arguments)
        if result.stdout:
            return result, json.loads(result.stdout)
        return result, None

    def codes(self, document):
        return [finding["code"] for finding in document["findings"]]

    def test_malformed_frontmatter_is_a_blocking_finding(self):
        malformed_documents = {
            "missing delimiter": "---\nname: malformed\ndescription: text\n",
            "not mapping": "---\n- name: malformed\n- description: text\n---\n",
            "missing name": "---\ndescription: text\n---\n",
            "non-string description": "---\nname: malformed\ndescription:\n---\n",
            "sequence description": (
                "---\nname: malformed\ndescription: [not, text]\n---\n"
            ),
            "mapping description": (
                "---\nname: malformed\ndescription: {text: invalid}\n---\n"
            ),
            "sequence name": (
                "---\nname: [malformed]\ndescription: text\n---\n"
            ),
            "mapping name": (
                "---\nname: {value: malformed}\ndescription: text\n---\n"
            ),
        }
        for label, content in malformed_documents.items():
            with self.subTest(label=label):
                directory = self.root / label.replace(" ", "-")
                directory.mkdir()
                (directory / "SKILL.md").write_text(content, encoding="utf-8")

                result, document = self.validate(directory)

                self.assertEqual(result.returncode, 1)
                self.assertTrue(
                    {"FRONTMATTER_INVALID", "REQUIRED_FIELD"}
                    & set(self.codes(document))
                )

    def test_name_format_and_directory_name_must_match(self):
        directory = self.create_skill("Bad_Name", directory_name="different-name")

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 1)
        self.assertIn("INVALID_NAME", self.codes(document))
        self.assertIn("NAME_DIRECTORY_MISMATCH", self.codes(document))

    def test_accepts_nested_extra_frontmatter_and_block_description(self):
        directory = self.root / "nested-skill"
        directory.mkdir()
        (directory / "SKILL.md").write_text(
            "---\n"
            "name: 'nested-skill'\n"
            "description: >\n"
            "  Performs a bounded task with\n"
            "  a folded description.\n"
            "allowed-tools:\n"
            "  - Read\n"
            "  - Write\n"
            "metadata:\n"
            "  trigger: nested data\n"
            "  labels:\n"
            "    - one\n"
            "    - two\n"
            "---\n"
            "# Nested\n",
            encoding="utf-8",
        )

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(document["findings"], [])

    def test_finds_broken_and_escaping_links_but_ignores_external_anchor_and_images(self):
        directory = self.create_skill(
            body=(
                "[missing](references/missing.md)\n"
                "[escape](../outside.md)\n"
                "[web](https://example.com/source)\n"
                "[mail](mailto:owner@example.com)\n"
                "[section](#clean)\n"
                "![optional](images/missing.png)\n"
            )
        )

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            sorted(code for code in self.codes(document) if "LINK" in code),
            ["BROKEN_LOCAL_LINK", "LINK_PATH_ESCAPE"],
        )

    def test_resolves_links_relative_to_each_markdown_file_and_rejects_symlink_escape(self):
        directory = self.create_skill(body="[guide](references/guide.md)\n")
        references = directory / "references"
        references.mkdir()
        (references / "guide.md").write_text("[skill](../SKILL.md)\n", encoding="utf-8")
        outside = self.root / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        try:
            (references / "linked.md").symlink_to(outside)
        except (OSError, NotImplementedError):
            pass
        else:
            (references / "guide.md").write_text(
                "[skill](../SKILL.md)\n[escape](linked.md)\n", encoding="utf-8"
            )

        result, document = self.validate(directory)

        expected = "LINK_PATH_ESCAPE" if (references / "linked.md").is_symlink() else None
        if expected:
            self.assertEqual(result.returncode, 1)
            self.assertIn(expected, self.codes(document))
        else:
            self.assertEqual(result.returncode, 0)

    def test_validates_reference_style_links_and_ignores_image_references(self):
        directory = self.create_skill(
            body=(
                "[missing guide][missing]\n"
                "[escape][]\n"
                "[web][web-source]\n"
                "[mail][owner]\n"
                "[section][local-section]\n"
                "![optional][image-only]\n\n"
                "[missing]: references/missing.md\n"
                "[escape]: ../outside.md\n"
                "[web-source]: https://example.com/source\n"
                "[owner]: mailto:owner@example.com\n"
                "[local-section]: #clean\n"
                "[image-only]: images/missing.png\n"
            )
        )

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 1)
        link_findings = [
            item for item in document["findings"]
            if item["code"] in {"BROKEN_LOCAL_LINK", "LINK_PATH_ESCAPE"}
        ]
        self.assertEqual(
            [(item["code"], item["line"]) for item in link_findings],
            [("BROKEN_LOCAL_LINK", 12), ("LINK_PATH_ESCAPE", 13)],
        )

    def test_finds_placeholders_except_in_baseline_observations(self):
        marker = "TO" + "DO"
        directory = self.create_skill(body="[notes](references/notes.md)\n")
        references = directory / "references"
        references.mkdir()
        (references / "notes.md").write_text(f"Finish: {marker}\n", encoding="utf-8")
        evals = directory / "evals"
        evals.mkdir()
        (evals / "baseline-observations.md").write_text(
            f"Observed literal marker: {marker}\n", encoding="utf-8"
        )

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 1)
        placeholders = [
            finding for finding in document["findings"]
            if finding["code"] == "PLACEHOLDER_TOKEN"
        ]
        self.assertEqual(len(placeholders), 1)
        self.assertEqual(placeholders[0]["path"], "references/notes.md")

    def test_undisclosed_risky_commands_are_high_severity(self):
        risks = {
            "destructive-rm": "```bash\nrm -rf /tmp/release\n```\n",
            "destructive-rm-sudo": "```bash\nsudo rm -rf /tmp/release\n```\n",
            "destructive-rm-long-flags": (
                "```bash\nrm --recursive --force /tmp/release\n```\n"
            ),
            "curl-upload": "```bash\ncurl -X POST -d @report.json https://example.com\n```\n",
            "git-push": "```bash\ngit push origin main\n```\n",
            "global-install": "```bash\nnpm install --global some-tool\n```\n",
            "credential-read": "```bash\ncat ~/.ssh/id_rsa\n```\n",
            "credential-read-home-variable": (
                "```bash\ncat $HOME/.ssh/id_ed25519\n```\n"
            ),
            "tilde-shell-fence": "~~~sh\ngit push origin main\n~~~\n",
            "attributed-shell-fence": (
                "```bash {.release}\ngit push origin main\n```\n"
            ),
        }
        for name, body in risks.items():
            with self.subTest(name=name):
                directory = self.create_skill(name=name, body=body)

                result, document = self.validate(directory)

                self.assertEqual(result.returncode, 1)
                risk_findings = [
                    finding for finding in document["findings"]
                    if finding["code"].startswith("RISK_")
                ]
                self.assertEqual(len(risk_findings), 1)
                self.assertEqual(risk_findings[0]["severity"], "High")

    def test_python_subprocess_list_command_is_high_severity(self):
        directory = self.create_skill(name="python-risk")
        scripts = directory / "scripts"
        scripts.mkdir()
        (scripts / "release.py").write_text(
            "import subprocess\n"
            "subprocess.run(['git', 'push', 'origin', 'main'], check=True)\n",
            encoding="utf-8",
        )

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 1)
        risks = [item for item in document["findings"] if item["code"] == "RISK_GIT_PUSH"]
        self.assertEqual(len(risks), 1)
        self.assertEqual(risks[0]["path"], "scripts/release.py")
        self.assertEqual(risks[0]["line"], 2)

    def test_clear_permission_disclosure_downgrades_but_retains_risk(self):
        directory = self.create_skill(
            name="disclosed-risk",
            body=(
                "Ask the user for explicit permission before running the command.\n\n"
                "```bash\ngit push origin main\n```\n"
            ),
        )

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 0)
        risks = [finding for finding in document["findings"] if finding["code"] == "RISK_GIT_PUSH"]
        self.assertEqual(len(risks), 1)
        self.assertEqual(risks[0]["severity"], "Medium")
        self.assertEqual(document["status"], "pass")

    def test_disclosure_is_scoped_to_the_file_containing_the_command(self):
        directory = self.create_skill(
            name="scoped-disclosure",
            body=(
                "Ask the user for explicit permission before running commands.\n"
                "[safe](references/safe.md)\n"
                "[unsafe](references/unsafe.md)\n"
            ),
        )
        references = directory / "references"
        references.mkdir()
        (references / "safe.md").write_text(
            "Ask the user for explicit confirmation before running this command.\n\n"
            "```bash\ngit push origin safe\n```\n",
            encoding="utf-8",
        )
        (references / "unsafe.md").write_text(
            "```bash\ngit push origin unsafe\n```\n",
            encoding="utf-8",
        )

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 1)
        risks = {
            item["path"]: item["severity"]
            for item in document["findings"]
            if item["code"] == "RISK_GIT_PUSH"
        }
        self.assertEqual(
            risks,
            {"references/safe.md": "Medium", "references/unsafe.md": "High"},
        )

    def test_prose_source_urls_do_not_count_as_network_commands(self):
        directory = self.create_skill(
            body="Sources: https://curl.se/docs/ and https://git-scm.com/docs/git-push\n"
        )

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 0)
        self.assertFalse(any(code.startswith("RISK_") for code in self.codes(document)))

    def test_inert_python_command_text_is_not_risky_behavior(self):
        directory = self.create_skill()
        scripts = directory / "scripts"
        scripts.mkdir()
        (scripts / "patterns.py").write_text(
            'UPLOAD_PATTERN = r"curl -X POST -d @report.json https://example.com"\n',
            encoding="utf-8",
        )

        result, document = self.validate(directory)

        self.assertEqual(result.returncode, 0)
        self.assertFalse(any(code.startswith("RISK_") for code in self.codes(document)))

    def test_clean_package_has_deterministic_success_document(self):
        directory = self.create_skill(body="[guide](references/guide.md)\n")
        references = directory / "references"
        references.mkdir()
        (references / "guide.md").write_text("# Guide\n", encoding="utf-8")

        first, first_document = self.validate(directory)
        second, second_document = self.validate(directory)

        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(first_document, second_document)
        self.assertEqual(first_document["schema_version"], 1)
        self.assertEqual(first_document["skill_path"], str(directory.resolve()))
        self.assertEqual(first_document["status"], "pass")
        self.assertEqual(
            first_document["counts"],
            {"Blocker": 0, "High": 0, "Medium": 0, "Low": 0},
        )
        self.assertEqual(first_document["findings"], [])

    def test_output_file_markdown_and_invalid_invocation_exit_codes(self):
        directory = self.create_skill()
        output = self.root / "reports" / "validation.md"

        result = self.run_cli(directory, "--format", "markdown", "--output", output)
        missing = self.run_cli(self.root / "missing")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("# Skill Validation", output.read_text(encoding="utf-8"))
        self.assertEqual(missing.returncode, 2)
        self.assertIn("skill directory", missing.stderr.lower())
        self.assertNotIn("Traceback", missing.stderr)


if __name__ == "__main__":
    unittest.main()
