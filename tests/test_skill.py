"""Basic portable skill packaging checks, with no YAML/Markdown dependency."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillPackagingTests(unittest.TestCase):
    def test_frontmatter_and_instruction_budget(self):
        text = (ROOT / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\n"))
        frontmatter, body = text[4:].split("\n---\n", 1)
        name = re.search(r"^name: (.+)$", frontmatter, re.MULTILINE).group(1)
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertEqual(ROOT.name, name)
        self.assertIn("description: >-\n", frontmatter)
        description = " ".join(
            line.strip() for line in frontmatter.split("description: >-\n", 1)[1].splitlines()
        )
        self.assertGreater(len(description), 0)
        self.assertLessEqual(len(description), 1024)
        self.assertLess(len(text.splitlines()), 500)
        self.assertTrue(body.strip())

    def test_local_markdown_links_resolve(self):
        for doc in [ROOT / "SKILL.md", ROOT / "README.md", *ROOT.glob("references/*.md")]:
            for target in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                with self.subTest(doc=doc.name, target=target):
                    self.assertTrue((doc.parent / target.split("#", 1)[0]).is_file())

    def test_markdown_fences_are_balanced(self):
        for doc in [ROOT / "SKILL.md", ROOT / "README.md", *ROOT.glob("references/*.md")]:
            with self.subTest(doc=doc.name):
                fences = sum(line.startswith("```") for line in doc.read_text().splitlines())
                self.assertEqual(fences % 2, 0)


if __name__ == "__main__":
    unittest.main()
