# jj-vcs-skill

A portable [Agent Skill](https://agentskills.io/specification) that teaches coding
agents Jujutsu's model and workflows, rather than substituting command names in
a Git workflow.

## Selection policy

| Current repository | jj available? | Agent should use |
| --- | --- | --- |
| Initialized jj workspace, including colocated `.jj` + `.git` | Yes | **jj** |
| Git-only repository, even if jj is installed | Either | **Git** |
| Colocated jj/Git repository | No | **Git**, with a warning |
| Non-colocated jj workspace | No | Stop: no accessible Git fallback |
| Broken/unreadable jj workspace or invalid config | Yes | Diagnose; don't silently mutate the Git backend |
| No repository | Either | Report this; don't initialize anything automatically |

Detection works from subdirectories, respects nested repository boundaries,
recognizes Git worktree/submodule `.git` files and secondary jj workspaces, and
uses `--ignore-working-copy` so the jj detection probe does not snapshot files.
A Git-only nested repository is not mistaken for its outer jj workspace.

Requests phrased as “git status”, “commit”, “branch”, or “push” activate the same
policy. An explicit instruction to use the Git CLI is respected, with colocation
hazards explained before mutations. The preference never grants permission to
commit, publish, rewrite history, initialize, install tools, or change configuration.

## Install

This repository's root is the skill directory:

```text
jj-vcs-skill/
├── SKILL.md
├── references/
│   ├── workflows.md
│   ├── query-languages.md
│   ├── remotes-and-git.md
│   └── conflicts-and-recovery.md
├── scripts/
│   └── detect-vcs.sh
└── tests/
```

Place **`SKILL.md`, `references/`, and `scripts/` together** in a skill directory
named `jj-vcs-skill` under a discovery location supported by your agent. For
agents supporting the user-level `~/.agents/skills/` convention, run from this
repository:

```sh
mkdir -p "$HOME/.agents/skills/jj-vcs-skill"
cp SKILL.md "$HOME/.agents/skills/jj-vcs-skill/"
cp -R references scripts "$HOME/.agents/skills/jj-vcs-skill/"
```

Alternatively install those same files at
`YOUR_PROJECT/.agents/skills/jj-vcs-skill/` if your agent supports that project
location. Other agents have their own skill discovery paths; consult that
agent's instructions. Do not copy this repository's `.git` or `.jj` metadata.
No network or third-party libraries are needed to use the bundled references
or detector; the detector needs POSIX `sh` plus whichever VCS is available.

A skill is an instruction package, **not a shell interceptor or guaranteed
always-on policy**. Its description requests activation for all version-control
work, including Git-worded requests. The agent host must discover/load it. For
reliable selection, put a short instruction in your agent's persistent rules
(or the project's `AGENTS.md`, where supported):

```markdown
Before any version-control task, load the jj-vcs-skill skill and detect the VCS
for the target repository. Use jj when installed and the repository is already
initialized for jj, including colocated repositories; otherwise use Git if
usable. Never initialize/migrate a repository just to select jj. Do not let an
outer jj workspace override a nested Git-only repository. Diagnose broken jj
workspaces rather than silently falling back to Git writes.
```

Reload skills or start a new agent session as required by your host. Existing
Git-only workflow instructions may conflict: ensure they defer to repository
selection instead of requiring Git writes in every repository.

## What's covered

The main [SKILL.md](SKILL.md) contains the selection rule, core mental model,
default workflow, and safety checks. Detailed material is loaded on demand:

- [Workflows](references/workflows.md): inspect, describe/commit, split selected
  files, amend/squash, rebase stacks, merge, duplicate, revert, workspaces, and
  cautions for advanced automation.
- [Query languages](references/query-languages.md): revsets, filesets, quoting,
  change/commit identities, and machine-readable templates.
- [Remotes and Git](references/remotes-and-git.md): bookmark tracking/conflicts,
  scoped push previews, PRs, colocation, compatibility limits, and setup/signing.
- [Conflicts and recovery](references/conflicts-and-recovery.md): conflict
  resolution, operation history, selective undo, divergence, and stale workspaces.

The skill emphasizes automatically snapshotted working-copy commits, no index,
no active branch, automatic descendant rebasing, and first-class conflicts.
It preserves unrelated user work and treats remote history rewriting as a
separate authorization decision even when jj's push safety checks pass.

## Detector

```sh
sh scripts/detect-vcs.sh                 # Inspect the current directory.
sh scripts/detect-vcs.sh /path/to/repo   # Inspect an explicit directory.
```

- Exit **0**: stdout is exactly `jj` or `git`.
- Exit **1**: stdout is `none`; no usable repository was detected.
- Exit **2**: usage/detection error; read stderr and stop before VCS mutations.

The script probes the filesystem target, not a different repo selected through
inherited `GIT_DIR`/`GIT_WORK_TREE` overrides. It does not change the calling
shell's environment, write configuration, fetch, commit, or initialize repos.
When running later VCS commands, use the same target directory and don't let
ambient repository overrides redirect them elsewhere.

## Verification

```sh
sh -n scripts/detect-vcs.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Tests require only Python's standard library. Stubbed detection and packaging
tests don't need jj/Git; real-repository and workflow tests skip when their
executables are unavailable. Real tests use disposable repositories and a local
bare remote, with isolated configuration, and never publish over the network.
Workflow tests target **jj 0.46.0**; the skill instructs agents to check installed
help for older/newer command syntax.

For additional format validation, the Agent Skills specification recommends the
optional [`skills-ref validate`](https://github.com/agentskills/agentskills/tree/main/skills-ref)
reference tool. No agent-specific tool allowlist is imposed by this skill.

## Sources and maintenance

Based on the [official latest jj documentation](https://docs.jj-vcs.dev/latest/),
especially:

- [Tutorial](https://docs.jj-vcs.dev/latest/tutorial/),
  [Git comparison](https://docs.jj-vcs.dev/latest/git-comparison/), and
  [Git command table](https://docs.jj-vcs.dev/latest/git-command-table/).
- [Working copy](https://docs.jj-vcs.dev/latest/working-copy/),
  [bookmarks](https://docs.jj-vcs.dev/latest/bookmarks/), and
  [conflicts](https://docs.jj-vcs.dev/latest/conflicts/).
- [Revsets](https://docs.jj-vcs.dev/latest/revsets/),
  [filesets](https://docs.jj-vcs.dev/latest/filesets/),
  [templates](https://docs.jj-vcs.dev/latest/templates/), and
  [glossary](https://docs.jj-vcs.dev/latest/glossary/).
- [Operation log](https://docs.jj-vcs.dev/latest/operation-log/),
  [Git compatibility](https://docs.jj-vcs.dev/latest/git-compatibility/), and
  [GitHub/GitLab](https://docs.jj-vcs.dev/latest/github/).
- [Configuration](https://docs.jj-vcs.dev/latest/config/),
  [installation/setup](https://docs.jj-vcs.dev/latest/install-and-setup/), and
  [CLI reference](https://docs.jj-vcs.dev/latest/cli-reference/).

The documentation's `latest` URL moves. Local `jj --version`,
`jj COMMAND --help`, and `jj help -k TOPIC` are the authority for installed
syntax. When updating the skill, review semantic changes as well as renamed
flags, update the references, and rerun both detection and workflow tests.
