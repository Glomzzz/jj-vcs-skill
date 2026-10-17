"""Exercise documented recipes in disposable repos, never the user's repo."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_detection import GIT, JJ, isolated_env


@unittest.skipUnless(JJ and GIT, "real jj and Git are required")
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.env = isolated_env(self.base)
        self.repo = self.base / "repo"
        self.command(JJ, "git", "init", "--no-colocate", self.repo, cwd=self.base)

    def command(self, *args, cwd=None):
        result = subprocess.run(
            list(map(str, args)), cwd=cwd or self.repo, env=self.env,
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def jj(self, *args):
        return self.command(JJ, "--no-pager", "--color", "never", *args)

    def value(self, rev, template):
        return self.jj("log", "--no-graph", "-r", rev, "-T", template)

    def write(self, name, content):
        (self.repo / name).write_text(content)

    def test_snapshot_describe_commit_and_bookmark_semantics(self):
        change = self.value("@", "change_id")
        old_hash = self.value("@", "commit_id")
        self.write("task.txt", "task\n")
        self.jj("status")
        self.assertEqual(change, self.value("@", "change_id"))
        self.assertNotEqual(old_hash, self.value("@", "commit_id"))
        self.jj("describe", "-m", "Task")
        self.assertEqual(change, self.value("@", "change_id"))
        self.jj("bookmark", "create", "task", "-r", "@")
        self.jj("commit", "-m", "Task")
        self.assertEqual(change, self.value("@-", "change_id"))
        self.assertEqual("true", self.value("@", "empty"))
        self.assertEqual(change, self.value("task", "change_id"))
        self.write("second.txt", "second\n")
        self.jj("commit", "-m", "Second")
        self.assertEqual(change, self.value("task", "change_id"))
        self.assertNotEqual(change, self.value("@-", "change_id"))

    def test_split_keeps_unrelated_delta_in_working_copy(self):
        self.write("owned.txt", "agent's task\n")
        self.write("unrelated.txt", "user's other work\n")
        self.jj("split", "-m", "Task only", "owned.txt")
        self.assertEqual("owned.txt", self.jj("file", "list", "-r", "@-"))
        self.assertEqual("A unrelated.txt", self.jj("diff", "--summary"))
        self.assertEqual("user's other work\n", (self.repo / "unrelated.txt").read_text())

    def test_squash_rebases_descendant_and_moves_bookmark(self):
        self.write("task.txt", "first\n")
        self.jj("commit", "-m", "First")
        target = self.value("@-", "change_id")
        self.jj("bookmark", "create", "task", "-r", target)
        self.write("child.txt", "child\n")
        self.jj("commit", "-m", "Child")
        descendant = self.value("@-", "change_id")
        old_hash = self.value(descendant, "commit_id")
        self.jj("new", target)
        self.write("task.txt", "fixed\n")
        self.jj("squash", "--into", target, "--use-destination-message")
        self.assertEqual(target, self.value("task", "change_id"))
        self.assertNotEqual(old_hash, self.value(descendant, "commit_id"))
        self.assertEqual("fixed", self.jj("file", "show", "-r", descendant, "task.txt"))

    def test_conflicted_rebase_and_reviewable_resolution(self):
        self.write("file.txt", "base\n")
        self.jj("commit", "-m", "Base")
        base = self.value("@-", "change_id")
        self.jj("new", base, "-m", "Left")
        self.write("file.txt", "left\n")
        left = self.value("@", "change_id")
        self.jj("new", base, "-m", "Right")
        self.write("file.txt", "right\n")
        right = self.value("@", "change_id")
        self.jj("rebase", "-s", right, "-o", left)
        self.assertEqual("true", self.value(right, "conflict"))
        self.jj("new", right)
        self.write("file.txt", "resolved\n")
        self.jj("status")
        self.assertEqual("false", self.value("@", "conflict"))
        self.jj("squash", "--into", right, "--use-destination-message")
        self.assertEqual("", self.value(f"conflicts() & ::{right}", "commit_id"))
        self.assertEqual("resolved", self.jj("file", "show", "-r", right, "file.txt"))

    def test_revision_rebase_leaves_descendants_behind(self):
        ids = []
        for name in ("base", "a", "b", "c"):
            self.write(name + ".txt", name + "\n")
            self.jj("commit", "-m", name)
            ids.append(self.value("@-", "change_id"))
        base, a, b, c = ids
        self.jj("rebase", "-r", b, "-o", base)
        self.assertEqual(base, self.value(b + "-", "change_id"))
        self.assertEqual(a, self.value(c + "-", "change_id"))

    def test_duplicate_and_inverse_commit(self):
        self.write("bad.txt", "mistake\n")
        self.jj("commit", "-m", "Mistake")
        original = self.value("@-", "change_id")
        self.jj("duplicate", original, "-o", "root()")
        duplicate = self.value(f'all() ~ ::@', "change_id")
        self.assertTrue(duplicate)
        self.assertNotEqual(original, duplicate)
        self.assertEqual("mistake", self.jj("file", "show", "-r", duplicate, "bad.txt"))
        self.jj("revert", "-r", original, "--before", "@")
        self.assertEqual("", self.jj("file", "list", "-r", "@-"))
        self.assertEqual("mistake", self.jj("file", "show", "-r", original, "bad.txt"))

    def test_literal_filesets_and_json_template(self):
        self.write("Foo(1).txt", "literal\n")
        self.write("other.txt", "other\n")
        self.jj("describe", "-m", 'Quoted "description"\n\nBody')
        diff = self.jj("diff", "--git", 'file:"Foo(1).txt"')
        self.assertIn("literal", diff)
        self.assertNotIn("other.txt", diff)
        output = self.value(
            "@", 'json({"change_id" => change_id, "commit_id" => commit_id, "description" => description}) ++ "\n"'
        )
        decoded = json.loads(output)
        self.assertIn('Quoted "description"', decoded["description"])
        self.assertEqual(self.value("@", "change_id"), decoded["change_id"])

    def test_scoped_push_and_dry_run_to_local_remote(self):
        remote = self.base / "remote.git"
        self.command(GIT, "init", "--bare", remote, cwd=self.base)
        self.jj("git", "remote", "add", "origin", str(remote))
        self.write("task.txt", "ready\n")
        self.jj("commit", "-m", "Ready")
        self.jj("bookmark", "create", "task", "-r", "@-")
        tip_hash = self.value("task", "commit_id")
        self.jj("git", "push", "--remote", "origin", "--bookmark", "task", "--dry-run")
        self.assertEqual("", self.command(GIT, "--git-dir", remote, "for-each-ref"))
        self.jj("git", "push", "--remote", "origin", "--bookmark", "task")
        self.assertEqual(
            tip_hash,
            self.command(GIT, "--git-dir", remote, "rev-parse", "refs/heads/task"),
        )


if __name__ == "__main__":
    unittest.main()
