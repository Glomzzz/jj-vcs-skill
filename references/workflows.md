# jj workflow recipes

Use after the VCS selection and safety checks in `SKILL.md`. All uppercase
revision/name tokens below are placeholders. Inspect the graph before choosing
them. These commands describe possible operations, not automatic permission to
perform them. Check local `--help` when flags differ.

## Review before and after every meaningful operation

```sh
jj status
jj diff --git                         # @ relative to merged parents
jj diff -r REV --git                  # The delta introduced by REV
jj diff --from BASE --to TIP --git    # Difference between two trees
jj show REV
jj log -r 'ancestors(@, 10)'
jj file list
jj file show -r REV path/to/file
jj file annotate path/to/file
```

`jj diff -r REV` is not “the working copy compared to REV.” Use `--from`/`--to`
for that. A merge's delta is relative to the automatically merged parent trees,
so an empty merge can still connect important history.

## New work, switching tasks, and finishing work

```sh
jj new BASE -m "Implement the requested behavior"
# Edit files, run checks, inspect status and diff.
jj describe -m "feat(component): explain the result"
jj new
```

Describing and creating a child can instead be done with
`jj commit -m "feat(component): explain the result"`. This finishes the whole
current delta unless paths/options explicitly select less. Unlike Git's usual
commit, it includes already-tracked edits, deletions, and automatically tracked
new files, not just staged files.

To pause a change, record its change ID, then `jj new BASE` to work elsewhere.
To resume amending it, `jj edit SAVED_CHANGE`; to build on it, `jj new SAVED_CHANGE`.
A nonempty previous working copy remains visible. An empty, undescribed working
copy may be discarded automatically when leaving it; do not use one as a durable
named checkpoint.

## Select only task-owned files; split mixed work

For an inspected single-parent working-copy commit containing separable file
changes, put the selected files into a completed parent and leave the rest in
the working copy:

```sh
jj split -m "fix(component): task-owned change" path/to/owned-file another/owned-file
jj show @-
jj diff --git
jj status
```

With the default sequential split, the selected part becomes the first commit;
the remainder becomes its child. Verify IDs and descriptions afterward: do not
assume the original change ID stayed on the selected part. Exact behavior/options
can evolve; read `jj split --help` for the installed version.

- Use literal filesets for paths with special characters; see the query reference.
- A path selection takes **all** changes to that path, not just the agent's hunks.
- `jj split` without paths usually opens a diff editor. `jj split -i` and
  `jj squash -i` need an interactive diff editor; don't launch them in a headless
  tool session expecting an automatic result. Ask for user involvement or use an
  explicitly designed, reviewed noninteractive diff-editor tool.
- If user and agent edits overlap in one file, agree on hunk ownership. Do not
  stage with Git, restore the user's edits away, or commit everything to avoid
  making a selection.

## Amend and move deltas

Edit a task-owned mutable revision directly:

```sh
jj edit REV
# Edit files; subsequent snapshot rewrites REV and rebases descendants.
jj diff --git
```

Or make a reviewable fixup on top of it:

```sh
jj new REV
# Edit files and review the fixup delta.
jj diff --git
jj squash --into REV -m "fix(component): complete description"
```

`jj squash` with no source/destination moves `@` into its parent; prefer an
explicit destination, especially around merges. To move only selected files
between inspected changes:

```sh
jj squash --from SOURCE --into DEST -m "Complete destination message" path/to/file
```

Use `--use-destination-message` instead of `-m` when preserving the destination's
message is intentional. This discards source descriptions: inspect them first.
Without explicit message handling a squash can open an editor. It may abandon
the source when emptied; `--keep-emptied` changes that. Descendants and bookmarks
are updated as commits are rewritten. Re-inspect the graph and working-copy ID.

`jj absorb` can distribute edits to appropriate mutable ancestors, and
`jj diffedit` can edit a revision's delta. Both require careful scope review;
consult their help rather than using them as automatic cleanup.

## Rebase exactly the intended graph

Preview the source set and destination first:

```sh
jj log -r 'SOURCE:: | BASE'
jj rebase -s SOURCE -o BASE
```

| Selection | Effect |
| --- | --- |
| `-s SOURCE` | Moves SOURCE and its descendant subgraph to the new base. |
| `-r REV` | Moves selected revision(s); descendants are rebased onto the old parents so they stay behind. |
| `-b TIP` | Moves the branch containing TIP relative to the destination's ancestors; can select more than TIP's direct ancestry. |

`jj rebase -o BASE` defaults to branch-style selection around `@`; don't use this
shorthand unless its scope is understood. `-o/--onto` has the older aliases
`-d/--destination` on current versions. Use whichever local help documents.

After fetching, a task-owned stack can often be updated using
`jj rebase -s FIRST_TASK_CHANGE -o 'trunk()'`. Verify `trunk()` first. Do not
automatically rebase all mutable commits, other developers' stacks, or shared
published history. Re-run tests and inspect conflicts in all affected revisions.

Insertion flags can reorder commits (check `--insert-before`/`--before` and
`--insert-after`/`--after` in local help):

```sh
jj rebase -r REV --before NEXT
```

Unlike Git's interactive rebase, there is no todo list or `--continue` loop.
Use individual explicit transformations; `jj arrange` is an interactive,
version-dependent alternative, not a headless default.

## Merge and cherry-pick equivalents

Merge two inspected heads by creating a multi-parent commit:

```sh
jj new LEFT RIGHT -m "Merge the two development lines"
jj status
```

Resolve conflicts in the merge working copy, snapshot with `jj status`, inspect
its delta, and test. No `git merge`, staging, or separate merge-finalization
command is required. More than two parents are supported but should be deliberate.

To copy an existing change onto a different base without moving the original:

```sh
jj duplicate SOURCE -o DEST
jj log -r 'DEST::'
# Inspect the newly reported change ID before choosing to edit it.
```

This creates a different change identity. A copy operation need not switch the
working copy to that new revision. On older versions without destination flags,
consult help for a duplicate-then-rebase workflow; do not guess the resulting ID.

For a **new inverse commit** that leaves published history intact, an empty
working-copy child of the intended tip allows:

```sh
jj revert -r BAD_REV --before @
jj log -r 'ancestors(@, 5)'
```

Confirm `@` really is the intended empty child first. Alternatively,
`jj revert -r BAD_REV -o DEST` creates the inverse on DEST; inspect where the
result landed and whether the working copy moved. Revert is not operation undo.

## Restore or abandon: content-changing, not housekeeping

Only after authorization to discard/replace the selected content:

```sh
jj restore --from REV path/to/file
jj abandon REV
```

A bare `jj restore path/to/file` restores from `@`'s merged parents, removing that
path's current delta. Omitting paths can replace the whole current tree.
`jj abandon REV` hides the revision and rebases descendants onto its parents,
removing its delta from their ancestry and potentially causing conflicts.
Bookmarks on an abandoned revision can be deleted. Neither is a “safe cleanup”
default. Read the recovery reference before applying them.

## Workspaces, sparse checkouts, and automation

Use jj workspaces, not `git worktree`, in a jj repository:

```sh
jj workspace list
jj workspace add ../task-workspace -r BASE
# Continue in that directory; run VCS detection there too.
```

A workspace has its own `@`, but shares commits, bookmarks, and operations.
Rewriting shared ancestors can stale other workspaces. In the affected workspace,
inspect and follow `jj workspace update-stale` recovery guidance.
`workspace forget` leaves files on disk; newer `workspace remove` deletes the
workspace directory, including ignored files. Never remove one casually.

`jj sparse list` inspects sparse patterns; changing sparse patterns materializes
or removes working-copy paths. Don't treat an absent sparse path as a deletion.
Check `jj sparse --help` before changing them.

Advanced tools are optional and version-dependent:

- `jj fix` runs configured content transformers over selected revisions; it
  rewrites commits/descendants. Inspect configured tools and scope first.
- `jj run` can execute commands in isolated checkouts **and amend revisions with
  resulting edits**. It is not necessarily a read-only test runner.
- `jj bisect` can help locate a bad revision; read local help for selection,
  command execution, and state effects before starting.

Never execute repository-provided automation or aliases solely because a
reference suggests them; apply the project's normal trust and execution policy.

## Official sources

- [Tutorial](https://docs.jj-vcs.dev/latest/tutorial/)
- [Git comparison](https://docs.jj-vcs.dev/latest/git-comparison/)
- [Git command table](https://docs.jj-vcs.dev/latest/git-command-table/)
- [Working copy and workspaces](https://docs.jj-vcs.dev/latest/working-copy/)
- [CLI reference](https://docs.jj-vcs.dev/latest/cli-reference/)
