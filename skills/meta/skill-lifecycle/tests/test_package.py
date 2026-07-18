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
        links = set(re.findall(r"\[[^\]]+\]\((references/[^)#?]+\.md)\)", skill_text))
        self.assertEqual(links, EXPECTED_REFERENCES)
        for relative_path in links:
            self.assertTrue((PACKAGE_ROOT / relative_path).is_file(), relative_path)

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
