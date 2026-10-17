# Conflicts and recovery

Use after the safety rules in `SKILL.md`. Recovery can discard later work or
rewrite multiple commits. Inspect first; don't perform the suggested commands
as an unconditional sequence. Uppercase IDs/names are placeholders.

## Resolve file conflicts

A successful rebase/merge may leave conflicted commits. jj stores structured
conflicts, not just textual markers. No rebase/merge operation is paused, and
there is no `--continue` step.

```sh
jj status
jj log -r 'conflicts()'
jj resolve --list
```

Select the earliest relevant task-owned conflicted revision. A reviewable
resolution workflow from the official tutorial is:

```sh
jj new CONFLICTED_REV
# Edit conflicted files, replacing markers with the intended resolved content.
# Or run an approved, configured merge tool via jj resolve.
jj status
jj diff --git
jj squash --into CONFLICTED_REV --use-destination-message
jj status
jj log -r 'CONFLICTED_REV::'
```

Creating a child initially inherits the conflict. The resolved child can be
reviewed before squashing the resolution into the conflicted revision. Its
descendants then rebase automatically; resolving an ancestor often resolves
inherited downstream conflicts, but not always. Squashing can abandon the
resolution child and create a new working-copy ID: inspect where you are before
resuming previous work.

Alternatively, `jj edit CONFLICTED_REV`, resolve files, and `jj status` directly
rewrites that revision. It can be harder to review only the resolution delta.
Don't rewrite immutable/published or others' revisions without authorization;
a separate resolution child may be the intended final history instead.

Markers may contain these sections (the marker length can vary):

- `<<<<<<<` / `>>>>>>>`: begin/end of the conflict.
- `+++++++`: a snapshot side.
- `%%%%%%%`: a diff to apply to another side, not just a Git “ours” snapshot.
- `\\\\\\\`: continuation of a diff's label.

Apply the intended combination of changes, not just “keep everything after
`=======`.” Some configurations use snapshot or Git-diff3 markers instead.
For binary files, delete/modify, file/directory, or symlink conflicts, inspect
all sides and consult local help; don't blindly replace them with a text blob.

Run the project tests after resolution. Check `conflicts() & ::TIP` for the
whole intended published ancestry; a clean `@` alone isn't enough. Do not bypass
a push's conflict guard.

## Inspect both kinds of history

```sh
jj op log --limit 10
jj op show OP_ID
jj evolog -r REV
jj --at-op OP_ID log
jj --at-op OP_ID diff --git
```

Operation IDs identify repository-state transitions, not commits/change IDs.
`@` in an operation argument means current operation, while `@` in a revset
means a workspace commit. `--at-op` inspection ignores the current filesystem
and loads the recorded view at that operation.

Even an inspection command may have recorded a snapshot or imported Git refs.
Read the operation description/diff, not just its position, to identify the
actual unwanted action. Avoid mutations with `--at-op`: these can create
concurrent operation history instead of simply traveling back in time.

## Choose the smallest recovery

Only after identifying the operation and preserving any subsequent/user work:

| Goal | Candidate operation | Caveat |
| --- | --- | --- |
| Undo the most recent applicable operation | `jj undo` | Inspect what local help considers undoable; don't assume the previous shell command is the target. |
| Reverse one specific earlier operation | `jj op revert OP_ID` | Creates an inverse operation; can conflict with subsequent changes. |
| Return the local view to an old operation | `jj op restore OP_ID` | Broad restoration can remove visibility of later work and move many refs/workspaces. |
| Inspect/recover a previous change version | `jj evolog -r REV`, then exact commit ID | Prefer a targeted copy/new change over rewinding the whole repo. |
| Undo an already published change in new history | `jj revert -r BAD_REV ...` | New inverse commit, not local operation undo; inspect destination flags. |

Undo syntax has evolved; older jj versions can accept a specific operation in
`jj undo`, whereas current versions have `jj op revert` for selective reversal.
Don't invent `jj undo OP_ID` without checking installed help. Newer versions
also provide `jj redo`; use only if supported and the previewed action is wanted.

Before broad recovery, record the current operation ID and relevant change/commit
IDs, and make an independent backup of content that could be lost (especially
ignored/untracked files). Don't use aggressive garbage collection, `op abandon`,
or hand-edit `.jj` as a troubleshooting shortcut.

Operation recovery is local. It cannot undo a remote push, PR creation, external
command effects, or recover content jj never snapshotted. A later explicit push
could publish restored refs; don't assume local undo synchronized the remote.

## Divergent changes versus concurrent operations

Concurrent operations can be reconciled by jj, but can leave different visible
commits with one change ID. This is **change divergence**, not file-conflict
markers or a bookmark conflict.

```sh
jj log -r 'divergent()'
jj evolog -r EXACT_COMMIT_ID
jj op log --limit 10
```

Use exact commit IDs to inspect the alternatives. Decide which edits must be
preserved before choosing one version or combining them. On versions with
`jj converge`, consult help and preview its revset scope; do not run the broad
default against all mutable divergent changes. Don't arbitrarily abandon one
version solely to remove the “divergent” label.

Serializing mutating agent commands and coordinating with other processes
reduces surprises. jj supports concurrency; it does not know which outcome the
user intended.

## Stale, missing, or broken workspaces

After another workspace rewrites shared history, the current workspace's files
may no longer match its recorded commit. Inspect status and preserve content
before following the diagnostic:

```sh
jj workspace update-stale
```

Run it in the affected workspace. Don't delete `.jj`, reinitialize over it, or
use Git reset to synchronize. Update-stale can create a recovery commit if the
recorded operation has been lost; inspect its output and graph afterward.

If detection or jj commands fail due to invalid config, permissions, repository
format/version, or a broken linked workspace, report that specific failure.
Do not silently switch to mutating the backing Git repo, change global config,
or upgrade/downgrade repository data formats without agreement.

## Official sources

- [First-class conflicts and markers](https://docs.jj-vcs.dev/latest/conflicts/)
- [Working-copy conflicts and stale workspaces](https://docs.jj-vcs.dev/latest/working-copy/)
- [Operation log](https://docs.jj-vcs.dev/latest/operation-log/)
- [Glossary: divergence and operations](https://docs.jj-vcs.dev/latest/glossary/)
- [CLI reference](https://docs.jj-vcs.dev/latest/cli-reference/)
