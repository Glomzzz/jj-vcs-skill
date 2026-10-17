---
name: jj-vcs-skill
description: >-
  Use for all repository version-control tasks: status, diff, history, commits,
  branches/bookmarks, merge, rebase, undo, fetch, push, and pull requests, including
  requests phrased as Git commands. Detect the current repository first; prefer
  Jujutsu (jj) only when jj is installed and that repository is already initialized
  for jj, otherwise use Git. Explain jj's working-copy commits, change IDs,
  revsets, automatic rebasing, conflicts, bookmarks, and safe Git interoperability.
---

# Jujutsu-first version control

## 1. Select the VCS before doing version-control work

**Use jj if and only if the `jj` executable is available and the target repository
is already a working jj workspace. Otherwise use Git if it is a Git repository.**
A colocated repository has both `.jj` and `.git`: **choose jj**, not Git.
The user saying “git diff”, “commit”, or “branch” normally describes an intent;
fulfill it with jj when selected. Honor an explicit request to use the Git CLI,
but first explain any colocation hazards relevant to a mutating command.

Run the bundled detector from the directory being worked on:

```sh
sh /absolute/path/to/this/skill/scripts/detect-vcs.sh
# Or inspect a different target directory:
sh /absolute/path/to/this/skill/scripts/detect-vcs.sh /path/to/repository
```

Resolve the script path relative to **this installed skill**, not the project.
It prints `jj` or `git` with exit 0; `none` with exit 1; or a diagnostic with
exit 2 if detection is blocked. Do not treat exit 2 as permission to use Git.

If scripts cannot run, perform the equivalent checks yourself:

1. Starting at the target directory, find the nearest ancestor containing `.jj`
   or `.git` (a Git marker may be a file). This is the repository boundary.
2. If that boundary has `.jj` and `jj` is available, load its recorded state with
   `jj --ignore-working-copy --at-op=@ -R "$root" log --no-graph -r @ -T commit_id`.
   Select jj on success. `jj root` alone doesn't validate the repository data.
3. Otherwise, if the boundary has `.git`, verify Git there with
   `git -C "$root" rev-parse --git-dir`. Select Git on success. Don't let Git
   discover a different outer repository. With no marker, Git can still identify
   a bare repository at the target. Otherwise report no usable VCS.
4. A present but unreadable/broken jj workspace or invalid configuration is an
   error to diagnose, not grounds for silently mutating the backing Git repo.

Do not rely on `test -d .jj`: it misses subdirectories and doesn't validate
linked workspaces. Keep subsequent commands scoped to the detected target;
inherited `GIT_DIR`/`GIT_WORK_TREE` must not redirect Git into another repository.
Do not rely on `jj root` alone: inside a nested Git-only repo it can find an
**outer** jj workspace. Re-detect after changing repositories/workspaces, including
submodules. If jj is missing, Git fallback is usable only where Git can actually
open the repo; do not reach into `.jj/repo/store` to manufacture a fallback.

**Never install jj, run `jj git init`, migrate/colocate a repo, or initialize Git
merely to satisfy this preference.** Initialization/cloning requires the user's
intent. If Git is selected, use normal safe Git workflows: inspect status and
staged/unstaged diffs, stage only task-owned changes, and never use destructive
reset/clean or force-push without authorization. The jj recipes below do not
apply to a Git-only repository.

## 2. Understand jj before translating Git habits

- **`@` is the working-copy commit**, not Git's `HEAD`. Most commands snapshot
  filesystem edits into a new version of `@` before running. Even `status`,
  `diff`, and `log` can record an operation. This is not a remote publish.
- **No index/staging area.** New non-ignored files are normally tracked
  automatically; edits and deletions are snapshotted too. `.gitignore` is used,
  not `.jjignore`. `snapshot.auto-track`, size limits, and sparse settings can
  change what is included. Inspect status; don't assume every new file was added.
- **Change ID versus commit ID.** A rewrite normally preserves the change ID but
  creates a new commit hash. Prefer unambiguous change IDs for ongoing work;
  use commit hashes for an exact historical version or divergent changes.
- **`jj describe -m ...` describes the existing change.** It does not stage files
  or start a successor. `jj new` starts a new empty child; `jj commit -m ...`
  describes the current change and starts a new child in one command.
- **`jj new REV` starts a child of REV; `jj edit REV` edits REV itself.** Prefer
  `new` for inspecting published history or working on top of somebody else's work.
  Old work remains in the graph: a Git-style stash is usually unnecessary.
- **Bookmarks are movable names**, mapped to Git branches on remotes. There is
  no active/current bookmark. Creating a child does not advance a bookmark;
  rewriting its target normally moves it along automatically.
- **Rewriting an ancestor automatically rebases descendants.** This includes
  descendants on other stacks and can affect other workspaces. Inspect scope
  before a rewrite; do not assume only the working-copy commit will change.
- **Conflicts are first-class data in commits.** A rebase/merge may succeed while
  leaving conflicts. There is no `jj rebase --continue`, Git staging step, or
  pending merge to commit. Inspect the affected graph, not just the exit code.
- **Two histories exist.** `jj log` shows commits; `jj op log` shows changes to
  repository state. `jj evolog` shows how a change evolved. Local undo does not
  undo a remote push or restore ignored/never-snapshotted files.
- **`root()` is virtual.** `trunk()` is a configurable revset alias for the main
  line, not a guaranteed bookmark named `main`. Verify its resolution.

## 3. Start with inspection, not history changes

After selecting jj:

```sh
jj --version
jj --no-pager --color never status
jj --no-pager --color never log -r 'ancestors(@, 10)'
jj --no-pager --color never diff --git
jj bookmark list --all
jj git remote list
```

Inspect local instructions and identify pre-existing edits, the intended base,
any conflicts, and the user's desired outcome. For especially sensitive
inspection, `--ignore-working-copy` avoids snapshotting/updating the working copy,
but shows the **last recorded state**, not unsnapshotted edits on disk.

For commands below, `REV`, `BASE`, `TIP`, `SOURCE`, `DEST`, `NAME`, and `REMOTE`
are placeholders: resolve them from the repository; do not type them literally.
Do not assume `main`, `origin`, or `@-` is the intended target. `@-` selects all
parents, so it is not necessarily one commit at a merge.

Check `jj COMMAND --help` on the installed version before using an unfamiliar
flag. The online `latest` docs can be newer than the executable. Prefer explicit
revisions, filesets, remotes, and noninteractive messages over user-specific
aliases or editor prompts. Use `--no-pager --color never` for readable tool output.

## 4. Default task workflow

### Make a change without absorbing unrelated work

If `@` is already the intended task change, continue there. If it contains
unrelated work, record its change ID and inspect the graph before making a
separate child/sibling or asking how to handle overlapping edits. A new child
inherits its parent's content; it does not magically remove unrelated work from
the ancestry of a future push.

When the user wants a separate change from a verified base:

```sh
jj new BASE
# Edit files and run the project's tests/lint/format checks explicitly.
jj diff --git
jj status
```

Don't run `jj new` automatically at every session start: it changes the workspace.
Don't “clean” or rewrite the user's existing changes for convenience.

### Finish/commit only when requested

After reviewing all content of `@` and verifying it belongs to the task:

```sh
jj commit -m "fix(scope): explain the change"
# The completed change is now @-; @ is a fresh empty child.
jj show @-
jj status
```

Alternatively, `jj describe -m "..."` leaves the completed change at `@`;
run `jj new` only if a fresh working-copy commit is desired. Follow project
message conventions; Conventional Commits are not mandatory everywhere.
If only selected files/hunks belong to the task, read
[workflows](references/workflows.md) before committing. There is no staging area
that implicitly excludes the user's other edits.

### Amend a mutable change

For message-only changes: `jj describe REV -m "..."`.
For content, either `jj edit REV` and edit files, or make a fixup child with
`jj new REV`, review its diff, then `jj squash --into REV -m "..."`.
The latter makes the fixup independently reviewable. Read the workflow reference
for message preservation and partial squashes. Never squash blindly into `@-`.

### Update from a remote

Fetching and integrating are separate decisions:

```sh
jj git fetch --remote REMOTE
jj log -r 'trunk() | ancestors(@, 10)'
# Only if rebasing the inspected, task-owned stack is wanted:
jj rebase -s SOURCE -o BASE
jj status
jj log -r 'SOURCE::'
```

Use `-s` for a change and its descendants, `-r` for relocating selected changes
while leaving descendants behind, and `-b` for a branch relative to the destination.
These are not interchangeable. See [workflows](references/workflows.md).
Older releases may spell `-o/--onto` as `-d/--destination`; consult local help.

### Publish only when authorized

Read [remotes and Git interoperability](references/remotes-and-git.md) first.
Determine the last intended described, conflict-free revision; do not point a
bookmark at the empty working-copy child by habit.

```sh
jj bookmark create NAME -r TIP       # Only if NAME doesn't exist.
# If it exists, inspect it, then: jj bookmark move NAME --to TIP
jj git push --remote REMOTE --bookmark NAME --dry-run
# After checking the preview and authorization:
jj git push --remote REMOTE --bookmark NAME
```

Tracking/new-bookmark requirements vary by version. Follow local help, not an
invented `--force` flag. A normal jj push can rewrite remote history; its safety
checks do not replace permission to rewrite shared commits. A dry run is not
permission to publish and may still snapshot/update local state.

## 5. Safety rules and completion checks

- Don't commit, push, create PRs, change bookmarks, rewrite history, or change
  persistent configuration just because this skill is active. Do only the
  version-control operations needed and authorized for the task.
- Inspect the exact revset before a destructive/broad command with
  `jj log -r 'EXPRESSION'`. Respect immutable commits and ownership; do not bypass
  immutability via `--ignore-immutable` or configuration changes by default.
- `jj restore`, `abandon`, `squash`, `rebase`, `undo`, and operation restoration
  can replace content or change other commits. Preserve unrelated work and
  explain/confirm destructive scope first. An operation log is not a full backup.
- Keep credentials/secrets and build artifacts outside the working copy or
  properly ignored **before** a snapshot. Removing a secret from the current
  tree does not erase earlier snapshots; report exposure and rotate credentials.
- Do not assume Git hooks, `.gitattributes`, LFS filters, or submodule operations
  run under jj. Run required checks explicitly; consult the compatibility guide
  before handling these features.
- Prefer jj for status, diffs, history, commits, bookmarks, fetch, push, and
  workspaces in a jj repo. Don't mix in Git writes or “repair” detached HEAD.
  If a required feature has no jj equivalent, explain and obtain approval for a
  narrowly scoped Git operation; see the interoperability reference.
- After mutations, inspect `jj status`, the affected graph and diffs, and
  bookmark positions. Check conflicts in the entire intended publish stack,
  not only `@`. Report tests, change IDs, remaining work, and whether anything
  was committed/pushed. An empty `@` means no delta from its parents, not “there
  is no unpublished work.”

## 6. Load detailed references as needed

| Task | Read |
| --- | --- |
| Commit selection, stacks, squash/split, merge, copy/revert, workspaces | [workflows](references/workflows.md) |
| Revision/path selection, quoting, history queries, machine-readable output | [revsets, filesets, templates](references/query-languages.md) |
| Fetch/push, bookmark tracking/conflicts, PRs, colocation, setup/signing | [remotes and Git interoperability](references/remotes-and-git.md) |
| File conflicts, undo/recovery, divergence, stale workspaces | [conflicts and recovery](references/conflicts-and-recovery.md) |

Primary source: [official jj documentation](https://docs.jj-vcs.dev/latest/).
Use `jj help`, `jj COMMAND --help`, and `jj help -k TOPIC` for version-matched help.
