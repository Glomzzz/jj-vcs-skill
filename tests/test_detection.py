"""Dependency-free detector tests; real-repository cases skip without jj/Git."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DETECTOR = ROOT / "scripts" / "detect-vcs.sh"
SHELL = shutil.which("sh")
JJ = shutil.which("jj")
GIT = shutil.which("git")


def isolated_env(home):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("JJ_", "GIT_"))
    }
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / "config"),
        JJ_CONFIG="",
        JJ_USER="Skill Test",
        JJ_EMAIL="skill-test@example.invalid",
        JJ_EDITOR="false",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_TERMINAL_PROMPT="0",
    )
    return env


@unittest.skipUnless(SHELL, "POSIX sh is required")
class StubDetectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.cwd = self.base / "project with spaces"
        self.cwd.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.env = isolated_env(self.base)
        self.env["PATH"] = str(self.bin)
        self.env["PROBE_LOG"] = str(self.base / "probes")

    def tool(self, name, success=True):
        script = self.bin / name
        script.write_text(
            f"#!{SHELL}\n"
            f"printf '%s\\n' '{name}' \"$@\" >> \"$PROBE_LOG\"\n"
            f"exit {0 if success else 1}\n"
        )
        script.chmod(0o755)

    def marker(self, name, parent=None):
        (parent or self.cwd).joinpath(name).mkdir()

    def detect(self, cwd=None, args=()):
        return subprocess.run(
            [SHELL, str(DETECTOR), *map(str, args)],
            cwd=cwd or self.cwd,
            env=self.env,
            text=True,
            capture_output=True,
            timeout=10,
        )

    def assert_selection(self, expected, **kwargs):
        result = self.detect(**kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected + "\n")
        return result

    def test_jj_wins_in_colocated_repository(self):
        self.marker(".jj")
        self.marker(".git")
        self.tool("jj")
        self.tool("git")
        self.assert_selection("jj")
        probes = Path(self.env["PROBE_LOG"]).read_text().splitlines()
        self.assertIn("--ignore-working-copy", probes)
        self.assertIn("--at-op=@", probes)
        self.assertIn("log", probes)
        self.assertIn("-R", probes)
        self.assertIn(str(self.cwd), probes)
        self.assertNotIn("git", probes)

    def test_git_when_jj_not_initialized(self):
        self.marker(".git")
        self.tool("jj")
        self.tool("git")
        self.assert_selection("git")
        self.assertNotIn("jj\n", Path(self.env["PROBE_LOG"]).read_text())

    def test_git_when_jj_not_installed(self):
        self.marker(".jj")
        self.marker(".git")
        self.tool("git")
        result = self.assert_selection("git")
        self.assertIn("jj is unavailable", result.stderr)

    def test_non_colocated_jj(self):
        self.marker(".jj")
        self.tool("jj")
        self.assert_selection("jj")

    def test_subdirectory(self):
        self.marker(".jj")
        self.tool("jj")
        nested = self.cwd / "src" / "nested"
        nested.mkdir(parents=True)
        self.assert_selection("jj", cwd=nested)

    def test_nested_git_stops_outer_jj_discovery(self):
        self.marker(".jj")
        self.tool("jj")
        self.tool("git")
        nested = self.cwd / "vendor"
        nested.mkdir()
        self.marker(".git", nested)
        self.assert_selection("git", cwd=nested)
        self.assertNotIn("jj\n", Path(self.env["PROBE_LOG"]).read_text())

    def test_git_marker_can_be_a_file(self):
        (self.cwd / ".git").write_text("gitdir: /elsewhere\n")
        self.tool("git")
        self.assert_selection("git")

    def test_broken_jj_is_not_silent_git_fallback(self):
        self.marker(".jj")
        self.marker(".git")
        self.tool("jj", success=False)
        self.tool("git")
        result = self.detect()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("refusing silent Git fallback", result.stderr)
        self.assertNotIn("git", Path(self.env["PROBE_LOG"]).read_text().splitlines())

    def test_broken_symlink_is_not_ignored(self):
        (self.cwd / ".jj").symlink_to(self.base / "missing")
        self.tool("jj", success=False)
        self.assertEqual(self.detect().returncode, 2)

    def test_missing_jj_does_not_escape_into_outer_git(self):
        self.marker(".git")
        self.tool("git")
        nested = self.cwd / "inner"
        nested.mkdir()
        self.marker(".jj", nested)
        result = self.detect(cwd=nested)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertFalse(Path(self.env["PROBE_LOG"]).exists())

    def test_no_tools_or_repository(self):
        result = self.detect()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "none\n")

    def test_installed_jj_is_not_enough(self):
        self.tool("jj")
        result = self.detect()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "none\n")
        self.assertFalse(Path(self.env["PROBE_LOG"]).exists())

    def test_explicit_directory(self):
        self.marker(".jj")
        self.tool("jj")
        self.assert_selection("jj", cwd=self.base, args=(self.cwd,))

    def test_invalid_directory(self):
        self.assertEqual(self.detect(args=("missing",)).returncode, 2)

    def test_excess_arguments(self):
        result = self.detect(args=("one", "two"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)

    def test_git_environment_overrides_are_removed(self):
        self.marker(".git")
        script = self.bin / "git"
        script.write_text(
            f"#!{SHELL}\n"
            '[ "${GIT_DIR+x}${GIT_WORK_TREE+x}${GIT_COMMON_DIR+x}${GIT_INDEX_FILE+x}" = "" ]\n'
        )
        script.chmod(0o755)
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
            self.env[name] = "/unrelated"
        self.assert_selection("git")


@unittest.skipUnless(SHELL and JJ and GIT, "real jj, Git, and sh are required")
class RealRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.env = isolated_env(self.base)

    def run_command(self, *args, cwd=None):
        result = subprocess.run(
            list(map(str, args)),
            cwd=cwd or self.base,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def init_jj(self, path, colocated=True):
        self.run_command(
            JJ, "git", "init", "--colocate" if colocated else "--no-colocate", path
        )
        return path

    def detect(self, path, expected="jj"):
        self.assertEqual(self.run_command(SHELL, DETECTOR, path), expected)

    def test_colocated_root_subdir_and_symlink(self):
        repo = self.init_jj(self.base / "repo with spaces")
        nested = repo / "src"
        nested.mkdir()
        link = self.base / "linked-src"
        link.symlink_to(nested, target_is_directory=True)
        for path in (repo, nested, link):
            with self.subTest(path=path):
                self.detect(path)

    def test_non_colocated(self):
        self.detect(self.init_jj(self.base / "repo", colocated=False))

    def test_secondary_workspace(self):
        repo = self.init_jj(self.base / "repo")
        workspace = self.base / "secondary"
        self.run_command(JJ, "workspace", "add", workspace, cwd=repo)
        self.detect(workspace)

    def test_git_only_does_not_get_initialized(self):
        repo = self.base / "git-only"
        self.run_command(GIT, "init", repo)
        self.detect(repo, "git")
        self.assertFalse((repo / ".jj").exists())

    def test_nested_git_only_repository(self):
        outer = self.init_jj(self.base / "outer")
        inner = outer / "nested"
        self.run_command(GIT, "init", inner)
        self.detect(inner, "git")

    def test_nested_jj_repository(self):
        outer = self.base / "outer"
        self.run_command(GIT, "init", outer)
        self.detect(self.init_jj(outer / "nested"))

    def test_git_worktree_file_marker(self):
        repo = self.base / "git-only"
        self.run_command(GIT, "init", repo)
        self.run_command(
            GIT, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "--allow-empty", "-m", "Initial", cwd=repo,
        )
        worktree = self.base / "worktree"
        self.run_command(GIT, "worktree", "add", "-b", "task", worktree, cwd=repo)
        self.assertTrue((worktree / ".git").is_file())
        self.detect(worktree, "git")

    def test_bare_git(self):
        repo = self.base / "bare.git"
        self.run_command(GIT, "init", "--bare", repo)
        self.detect(repo, "git")

    def test_detection_does_not_snapshot_or_record_operation(self):
        repo = self.init_jj(self.base / "repo")
        args = (JJ, "--ignore-working-copy", "op", "log", "--no-graph", "--limit", "1", "-T", "id")
        before = self.run_command(*args, cwd=repo)
        (repo / "unsnapshotted.txt").write_text("Do not snapshot during detection.\n")
        self.detect(repo)
        self.assertEqual(before, self.run_command(*args, cwd=repo))
        self.assertNotIn(
            "unsnapshotted.txt",
            self.run_command(JJ, "--ignore-working-copy", "file", "list", cwd=repo),
        )

    def test_invalid_jj_config_blocks_git_fallback(self):
        repo = self.init_jj(self.base / "repo")
        config = self.base / "invalid.toml"
        config.write_text("[invalid TOML\n")
        self.env["JJ_CONFIG"] = str(config)
        result = subprocess.run(
            [SHELL, str(DETECTOR), str(repo)], env=self.env,
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("refusing silent Git fallback", result.stderr)

    def test_broken_jj_blocks_even_with_usable_git(self):
        repo = self.base / "repo"
        self.run_command(GIT, "init", repo)
        (repo / ".jj").mkdir()
        result = subprocess.run(
            [SHELL, str(DETECTOR), str(repo)], env=self.env,
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
