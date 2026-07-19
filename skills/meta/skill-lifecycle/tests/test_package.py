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
OPERATION_GUIDES = (
    "discover",
    "create",
    "review",
    "evaluate",
    "optimize",
    "maintain",
)
REQUIRED_GUIDE_SECTIONS = (
    "Goal",
    "Inputs",
    "Procedure",
    "Outputs",
    "State transition",
    "Human gate",
    "Design basis",
)
REPORT_TEMPLATES = {
    "assets/report-templates/evidence-card.md",
    "assets/report-templates/operation-report.md",
}
GUIDE_REQUIRED_TERMS = {
    "discover": ("use", "fork", "compose", "create", "SKILL.md"),
    "create": ("baseline", "draft", "Agent Skills", "Anthropic", "OpenAI"),
    "review": ("read-only", "plan", "confirm", "skill-optimizer", "Cisco"),
    "evaluate": ("trigger", "task effect", "skill-comply", "baseline"),
    "optimize": ("evidence", "minimal", "rollback", "SkillOpt"),
    "maintain": (
        "SKILL.md",
        "source",
        "ref",
        "path",
        "hash",
        "Keep",
        "Improve",
        "Update",
        "Merge",
        "Retire",
        "Vercel",
    ),
}
REQUIRED_REPORT_FIELDS = (
    "state",
    "findings",
    "gates",
    "artifacts",
    "evidence",
    "decision",
    "next operation",
)
EXPECTED_CASE_IDS = {
    "pressured-create-global-install",
    "review-uploading-skill-without-confirmation",
    "retire-from-mtime-and-read-counts",
}
FORWARD_CASE_IDS = {
    "forward-pressured-create-global-install",
    "forward-review-uploading-skill-without-confirmation",
    "forward-retire-from-mtime-and-read-counts",
    "forward-static-only-evaluation",
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

    def test_operation_guides_define_the_complete_contract(self):
        for guide_name in OPERATION_GUIDES:
            guide_path = PACKAGE_ROOT / "references" / f"{guide_name}.md"
            guide_text = self.read_required(guide_path)
            headings = set(re.findall(r"^## ([^#\n]+)$", guide_text, re.MULTILINE))
            for section in REQUIRED_GUIDE_SECTIONS:
                self.assertIn(section, headings, f"{guide_path}: missing {section}")

    def test_operation_guides_preserve_lifecycle_boundaries_and_sources(self):
        for guide_name, terms in GUIDE_REQUIRED_TERMS.items():
            guide_path = PACKAGE_ROOT / "references" / f"{guide_name}.md"
            guide_text = self.read_required(guide_path)
            for term in terms:
                self.assertIn(term, guide_text, f"{guide_path}: missing {term}")
            self.assertIn("confirm", guide_text.lower(), f"{guide_path}: no confirmation gate")

    def test_report_templates_require_the_shared_output_fields(self):
        for relative_path in REPORT_TEMPLATES:
            template_text = self.read_required(PACKAGE_ROOT / relative_path).lower()
            for field in REQUIRED_REPORT_FIELDS:
                self.assertIn(field, template_text, f"{relative_path}: missing {field}")

    def test_router_is_compact_and_routes_to_one_operation_guide(self):
        skill_text = self.read_required(SKILL_FILE)
        self.assertLess(len(skill_text.splitlines()), 500)
        self.assertIn("## Quick reference", skill_text)
        self.assertIn("## Routing flow", skill_text)
        self.assertIn("## Example", skill_text)
        self.assertIn("## Common mistakes", skill_text)
        self.assertRegex(
            skill_text,
            r"Read exactly one operation guide before acting",
        )

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

    def test_forward_test_evidence_is_separate_and_complete(self):
        observations = self.read_required(
            PACKAGE_ROOT / "evals" / "baseline-observations.md"
        )
        self.assertIn("## Forward tests", observations)
        for case_id in FORWARD_CASE_IDS:
            self.assertIn(f"**ID:** `{case_id}`", observations)
        self.assertEqual(
            observations.count("Invocation: `codex exec --sandbox read-only --ephemeral`"),
            len(FORWARD_CASE_IDS),
        )
        self.assertGreaterEqual(
            observations.count("### Raw observed response"),
            len(EXPECTED_CASE_IDS) + len(FORWARD_CASE_IDS),
        )
        self.assertIn("## Installation smoke", observations)
        self.assertIn("--agent codex --copy -y", observations)
        self.assertIn("scope: `project`", observations)

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
