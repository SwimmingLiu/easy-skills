import json
import re
import unittest
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SKILL_FILE = PACKAGE_ROOT / "SKILL.md"
EXPECTED_REFERENCES = {
    "references/discover.md",
    "references/create.md",
    "references/review.md",
    "references/evaluate.md",
    "references/optimize.md",
    "references/maintain.md",
    "references/evidence-schema.md",
}
EXPECTED_CASE_IDS = {
    "pressured-create-global-install",
    "review-uploading-skill-without-confirmation",
    "retire-from-mtime-and-read-counts",
}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)")


def parse_frontmatter(text):
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, re.DOTALL)
    if not match:
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    return yaml.safe_load(match.group(1)), match.end()


class SkillLifecyclePackageTest(unittest.TestCase):
    def read_required(self, path):
        self.assertTrue(path.is_file(), f"package file is missing: {path}")
        return path.read_text(encoding="utf-8")

    def test_folder_and_frontmatter_name_match(self):
        self.assertEqual(PACKAGE_ROOT.name, "skill-lifecycle")
        metadata, _ = parse_frontmatter(self.read_required(SKILL_FILE))
        self.assertEqual(metadata["name"], "skill-lifecycle")

    def test_frontmatter_has_only_name_and_description(self):
        metadata, _ = parse_frontmatter(self.read_required(SKILL_FILE))
        self.assertEqual(set(metadata), {"name", "description"})

    def test_description_is_trigger_oriented_and_bounded(self):
        metadata, _ = parse_frontmatter(self.read_required(SKILL_FILE))
        description = metadata["description"]
        self.assertIsInstance(description, str)
        self.assertTrue(description.startswith("Use when"))
        self.assertLessEqual(len(description), 500)

    def test_direct_reference_links_exist(self):
        skill_text = self.read_required(SKILL_FILE)
        link_targets = {
            target.split("#", 1)[0].split("?", 1)[0]
            for target in MARKDOWN_LINK.findall(skill_text)
        }
        links = {
            target
            for target in link_targets
            if target.startswith("references/") and target.endswith(".md")
        }
        self.assertEqual(links, EXPECTED_REFERENCES)
        for relative_path in links:
            self.assertTrue((PACKAGE_ROOT / relative_path).is_file(), relative_path)

    def test_eval_artifacts_and_ids_are_valid(self):
        observations_path = PACKAGE_ROOT / "evals" / "baseline-observations.md"
        evals_path = PACKAGE_ROOT / "evals" / "evals.json"
        self.read_required(observations_path)
        evals = json.loads(self.read_required(evals_path))

        case_ids = [case["id"] for case in evals["cases"]]
        self.assertEqual(set(case_ids), EXPECTED_CASE_IDS)
        self.assertEqual(len(case_ids), len(set(case_ids)), "duplicate case id")

        assertion_ids = [
            assertion["id"]
            for case in evals["cases"]
            for assertion in case["assertions"]
        ]
        self.assertEqual(
            len(assertion_ids), len(set(assertion_ids)), "duplicate assertion id"
        )

    def test_packaged_evidence_references_resolve_within_skill(self):
        evals_path = PACKAGE_ROOT / "evals" / "evals.json"
        evals = json.loads(self.read_required(evals_path))
        self.assertEqual(
            evals.get("source_provenance"),
            {
                "evidence_path": (
                    "docs/superpowers/evals/skill-lifecycle-baseline.md"
                )
            },
        )
        evidence_paths = [evals["provenance"]["evidence_path"]]
        evidence_paths.extend(case["evidence_ref"]["path"] for case in evals["cases"])

        package_root = PACKAGE_ROOT.resolve()
        for evidence_path in evidence_paths:
            resolved_path = (PACKAGE_ROOT / evidence_path).resolve()
            try:
                resolved_path.relative_to(package_root)
            except ValueError:
                self.fail(f"evidence reference escapes package: {evidence_path}")
            self.assertTrue(resolved_path.is_file(), f"missing evidence: {evidence_path}")

    def test_openai_interface_names_skill_in_default_prompt(self):
        interface_path = PACKAGE_ROOT / "agents" / "openai.yaml"
        interface = yaml.safe_load(self.read_required(interface_path))
        self.assertEqual(interface["interface"]["display_name"], "Skill Lifecycle")
        self.assertIn("$skill-lifecycle", interface["interface"]["default_prompt"])

    def test_package_contains_no_placeholder_tokens(self):
        forbidden_patterns = (
            re.compile(r"\b" + "TO" + r"DO\b", re.IGNORECASE),
            re.compile(r"\b" + "TB" + r"D\b", re.IGNORECASE),
            re.compile(r"\b" + "PLACE" + "HOLDER" + r"\b", re.IGNORECASE),
            re.compile(r"\{\{[^{}]+\}\}"),
            re.compile(r"\bexample_(?:script|reference|asset)\b", re.IGNORECASE),
        )
        text_suffixes = {".md", ".py", ".yaml", ".yml", ".json", ".txt"}
        for path in PACKAGE_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in text_suffixes:
                continue
            content = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertIsNone(pattern.search(content), f"template marker in {path}")


if __name__ == "__main__":
    unittest.main()
