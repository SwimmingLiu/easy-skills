import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "kb.py"


class KnowledgeBaseSkillTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.vault = Path(self.tempdir.name) / "vault"
        for relative in (
            "00-system",
            "01-inbox",
            "02-sources",
            "03-wiki/concepts",
            "04-projects",
            "08-journal",
        ):
            (self.vault / relative).mkdir(parents=True, exist_ok=True)
        (self.vault / "AGENTS.md").write_text("# Vault\n", encoding="utf-8")
        (self.vault / "02-sources" / "Sources Index.md").write_text(
            "# Sources Index\n", encoding="utf-8"
        )
        (self.vault / "08-journal" / "Knowledge Log.md").write_text(
            "# Knowledge Log\n", encoding="utf-8"
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def run_kb(self, *args, check=True, cwd=None):
        result = subprocess.run(
            ["python3", str(SCRIPT), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if check and result.returncode:
            self.fail(f"kb.py failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    def ingest(self):
        return self.run_kb(
            "ingest",
            "--vault",
            str(self.vault),
            "--title",
            "Durable Context",
            "--text",
            "Durable Markdown gives agents inspectable context.",
            "--source-url",
            "https://example.com/durable-context",
            "--author",
            "Example Author",
            "--published",
            "2026-07-28",
            "--concept",
            "Durable Context",
        )

    def test_locate_walks_up_from_nested_directory(self):
        nested = self.vault / "03-wiki" / "concepts"
        result = self.run_kb("locate", cwd=nested)
        self.assertEqual(Path(result.stdout.strip()).resolve(), self.vault.resolve())

    def test_ingest_is_idempotent_and_preserves_source(self):
        first = json.loads(self.ingest().stdout)
        source_path = self.vault / first["source_path"]
        original = source_path.read_text(encoding="utf-8")
        second = json.loads(self.ingest().stdout)

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["source_path"], second["source_path"])
        self.assertEqual(original, source_path.read_text(encoding="utf-8"))
        self.assertIn('source_url: "https://example.com/durable-context"', original)
        self.assertIn("Durable Markdown gives agents", original)

        index = (self.vault / "02-sources" / "Sources Index.md").read_text(encoding="utf-8")
        log = (self.vault / "08-journal" / "Knowledge Log.md").read_text(encoding="utf-8")
        self.assertEqual(index.count(first["source_link"]), 1)
        self.assertEqual(log.count(first["source_link"]), 1)

    def test_ingest_creates_traceable_concept_and_search_result(self):
        created = json.loads(self.ingest().stdout)
        concept = self.vault / created["concept_paths"][0]
        concept_text = concept.read_text(encoding="utf-8")
        self.assertIn(created["source_link"], concept_text)
        self.assertIn("confidence: medium", concept_text)

        search = json.loads(
            self.run_kb("search", "--vault", str(self.vault), "durable context").stdout
        )
        self.assertGreaterEqual(search["count"], 1)
        self.assertTrue(any(created["source_link"] in item["source_links"] for item in search["results"]))

    def test_check_reports_unresolved_links_and_recovers(self):
        self.ingest()
        healthy = json.loads(self.run_kb("check", "--vault", str(self.vault)).stdout)
        self.assertTrue(healthy["healthy"])

        broken = self.vault / "03-wiki" / "concepts" / "Broken.md"
        broken.write_text(
            "---\ntype: concept\nstatus: active\ncreated: 2026-07-29\nupdated: 2026-07-29\n---\n\n[[Missing Note]]\n",
            encoding="utf-8",
        )
        result = self.run_kb("check", "--vault", str(self.vault), check=False)
        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["healthy"])
        self.assertTrue(any("Missing Note" in issue for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
