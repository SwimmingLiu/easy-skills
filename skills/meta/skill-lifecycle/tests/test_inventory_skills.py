import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE_ROOT / "scripts" / "inventory_skills.py"
sys.path.insert(0, str(SCRIPT.parent))
from inventory_skills import parse_frontmatter


class InventorySkillsCliTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

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

    def write_skill(self, relative_directory, name, description="A useful skill."):
        directory = self.root / relative_directory
        directory.mkdir(parents=True, exist_ok=True)
        content = f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n"
        path = directory / "SKILL.md"
        path.write_text(content, encoding="utf-8")
        return path

    def inventory(self, *extra_arguments):
        result = self.run_cli("--root", self.root, *extra_arguments)
        return json.loads(result.stdout)

    def test_discovers_only_exact_regular_skill_files_and_ignores_excluded_dirs(self):
        alpha = self.write_skill("zeta/alpha", "alpha")
        beta = self.write_skill("beta", "beta")
        (self.root / "beta" / "OTHER.md").write_text("---\nname: other\n---\n")
        (self.root / "beta" / "skill.md").write_text("not exact", encoding="utf-8")
        excluded = (
            ".git/one",
            ".worktrees/two",
            "node_modules/three",
            "__pycache__/four",
            ".cache/five",
            ".hidden/six",
        )
        for index, directory in enumerate(excluded):
            self.write_skill(directory, f"excluded-{index}")
        symlink_directory = self.root / "linked-directory"
        symlink_file = self.root / "linked-file" / "SKILL.md"
        try:
            symlink_directory.symlink_to(alpha.parent, target_is_directory=True)
            symlink_file.parent.mkdir()
            symlink_file.symlink_to(beta)
        except (OSError, NotImplementedError):
            pass

        document = self.inventory()

        self.assertEqual(
            [record["path"] for record in document["skills"]],
            ["beta/SKILL.md", "zeta/alpha/SKILL.md"],
        )

    def test_records_frontmatter_hash_and_explicit_metadata(self):
        skill = self.write_skill("sample", "sample-skill", "Does sample work.")

        document = self.inventory(
            "--source",
            "github",
            "--ref",
            "main",
            "--license",
            "MIT",
            "--host",
            "codex",
            "--host",
            "claude",
        )

        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(
            document["skills"],
            [
                {
                    "name": "sample-skill",
                    "path": "sample/SKILL.md",
                    "sha256": hashlib.sha256(skill.read_bytes()).hexdigest(),
                    "source": "github",
                    "ref": "main",
                    "license": "MIT",
                    "hosts": ["codex", "claude"],
                }
            ],
        )

    def test_extracts_name_from_frontmatter_with_nested_extra_fields(self):
        directory = self.root / "nested-skill"
        directory.mkdir()
        skill = directory / "SKILL.md"
        skill.write_text(
            "---\n"
            'name: "nested-skill"\n'
            "description: |\n"
            "  First line.\n"
            "  Second line.\n"
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

        document = self.inventory()

        self.assertEqual(document["skills"][0]["name"], "nested-skill")

    def test_inline_comments_preserve_scalar_types_and_quoted_hashes(self):
        invalid = self.root / "invalid"
        invalid.mkdir()
        (invalid / "SKILL.md").write_text(
            "---\n"
            "name: [invalid] # still a sequence\n"
            "description: text\n"
            "---\n",
            encoding="utf-8",
        )
        missing = self.root / "missing"
        missing.mkdir()
        (missing / "SKILL.md").write_text(
            "---\n"
            "name: # missing\n"
            "description: text\n"
            "---\n",
            encoding="utf-8",
        )
        valid = self.root / "quoted-skill"
        valid.mkdir()
        quoted_content = (
            "---\n"
            'name: "quoted-skill" # package name\n'
            'description: "Keeps # inside and \\"escaped quotes\\"." # note\n'
            "---\n"
        )
        (valid / "SKILL.md").write_text(quoted_content, encoding="utf-8")

        document = self.inventory()
        metadata = parse_frontmatter(quoted_content)
        quoted_hashes = parse_frontmatter(
            "---\n"
            "name: quoted-skill\n"
            "description: '#single and #inside'\n"
            "metadata: \"#double\"\n"
            "---\n"
        )

        self.assertEqual(
            [(item["path"], item["name"]) for item in document["skills"]],
            [
                ("invalid/SKILL.md", None),
                ("missing/SKILL.md", None),
                ("quoted-skill/SKILL.md", "quoted-skill"),
            ],
        )
        self.assertEqual(
            metadata["description"], 'Keeps # inside and "escaped quotes".'
        )
        self.assertEqual(quoted_hashes["description"], "#single and #inside")
        self.assertEqual(quoted_hashes["metadata"], "#double")

    def test_absent_optional_metadata_is_not_omitted(self):
        self.write_skill("sample", "sample")

        record = self.inventory()["skills"][0]

        self.assertIsNone(record["source"])
        self.assertIsNone(record["ref"])
        self.assertIsNone(record["license"])
        self.assertEqual(record["hosts"], [])

    def test_hash_changes_only_when_skill_content_changes(self):
        skill = self.write_skill("sample", "sample")
        before = self.inventory()["skills"][0]["sha256"]
        (self.root / "README.md").write_text("unrelated", encoding="utf-8")
        unchanged = self.inventory()["skills"][0]["sha256"]
        skill.write_text(skill.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
        after = self.inventory()["skills"][0]["sha256"]

        self.assertEqual(before, unchanged)
        self.assertNotEqual(before, after)

    def test_writes_json_or_markdown_to_output(self):
        self.write_skill("sample", "sample")
        json_output = self.root / "reports" / "inventory.json"
        markdown_output = self.root / "reports" / "inventory.md"

        json_result = self.run_cli("--root", self.root, "--output", json_output)
        markdown_result = self.run_cli(
            "--root", self.root, "--format", "markdown", "--output", markdown_output
        )

        self.assertEqual(json_result.stdout, "")
        self.assertEqual(markdown_result.stdout, "")
        self.assertEqual(json.loads(json_output.read_text())["schema_version"], 1)
        markdown = markdown_output.read_text(encoding="utf-8")
        self.assertIn("# Skill Inventory", markdown)
        self.assertIn("sample/SKILL.md", markdown)
        self.assertFalse(any(json_output.parent.glob("*.tmp")))

    def test_invalid_root_is_actionable_runtime_error(self):
        result = self.run_cli("--root", self.root / "missing", check=False)

        self.assertEqual(result.returncode, 2)
        self.assertIn("root", result.stderr.lower())
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
