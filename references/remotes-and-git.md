# Remotes, bookmarks, and Git interoperability

Use after the selection/safety rules in `SKILL.md`. All uppercase names below
are placeholders. Inspect the actual repository and local command help.

## Bookmarks aren't checked-out branches

```sh
jj bookmark list --all
jj bookmark list --tracked
jj bookmark create NAME -r TIP
jj bookmark move NAME --to TIP
```

Creation and movement are alternatives, not commands to run blindly in sequence.
Inspect an existing name before reusing it. Moving a bookmark backwards/sideways
may require `--allow-backwards`; this is a safety override, not a default.

Creating a new commit on top of a bookmarked commit does not move the bookmark.
Rewriting that bookmarked commit (describe, amend, rebase) normally moves it to
the rewritten version. After `jj commit`, the completed change is normally `@-`;
after only `jj describe`, it is normally `@`. Always verify rather than assume.

`jj bookmark delete NAME` deletes locally and can schedule deletion on tracked
remotes for a later push. It is not just hiding a name. `bookmark forget` is a
different operation; read local help before using either.

## Fetching and tracking

```sh
jj git remote list
jj git fetch --remote REMOTE
jj bookmark list --all
```

A fetch updates recorded remote positions, and merges tracked remote changes
into corresponding local bookmarks. It can therefore create a **bookmark
conflict**; it does not automatically rebase your work onto the new trunk.

`NAME@REMOTE` is the last fetched/pushed record, not the remote's live state.
Remote bookmark tracking is an association between that record and a same-named
local bookmark. Clone normally tracks the default branch; other fetched remote
bookmarks are not necessarily tracked.

To follow an inspected remote bookmark on current versions:

```sh
jj bookmark track NAME --remote REMOTE
```

Older versions can use a different argument form, such as `NAME@REMOTE`.
Check `jj bookmark track --help`. Tracking can create/update a local name;
inspect it first. Untracking stops propagation; it doesn't delete remote work.
Don't enable global auto-tracking of every bookmark just to push one change.

To inspect/build on someone else's remote work without rewriting their commit:

```sh
jj new NAME@REMOTE
```

## Scoped publication

1. Confirm publishing is requested, the remote is correct, and the intended tip
   is not the empty WIP child. Check the whole outgoing ancestry for unrelated
   work, secrets, missing descriptions, and conflicts.
2. Run project tests, formatting, and policy checks explicitly. Git hooks are
   not a reliable substitute under jj.
3. Create/move only the intended bookmark and establish tracking as required
   by the installed version.
4. Preview the exact named push, inspect remote creations/rewrites/deletions,
   then push if authorized:

```sh
jj log -r 'conflicts() & ::TIP'
jj git push --remote REMOTE --bookmark NAME --dry-run
jj git push --remote REMOTE --bookmark NAME
```

Don't use unscoped `jj git push`, `--all`, `--tracked`, or `--deleted` by default.
They can publish unrelated refs. Current versions can create a remote bookmark
through a scoped named push; older versions may require `--allow-new`. Use only
flags shown by installed help, and understand whether the local bookmark needs
tracking first. `--change REV` auto-generates a bookmark; choose that workflow
only if a generated name is acceptable, and resolve REV explicitly.

A normal jj push checks the remote position against the recorded expectation
and supports history rewrites without a separate force flag. This is
lease-like protection, **not a guarantee of fast-forward publication**, nor
permission to overwrite collaborators' history. Don't bypass guards for private
commits, conflicts, or missing descriptions. Fetch/inspect rather than retrying
with increasingly permissive flags.

A failed push can leave local changes such as bookmark creation or signing.
A dry run can also affect local repository state. Inspect afterward instead of
assuming failure/dry-run means absolutely nothing changed.

## Bookmark conflict versus file conflict

`NAME??` or multiple targets in `jj bookmark list` indicates a conflicted name,
not necessarily conflicted files. A normal revset using that name can resolve
to multiple revisions and be rejected where one target is required.

1. `jj bookmark list --all` and `jj log` to inspect every target by ID.
2. Decide whether to integrate them by a rebase or merge; preserve both sides'
   work. If merging, pass the individually verified IDs to `jj new LEFT RIGHT`.
   Don't depend on a conflicted symbol silently expanding into merge parents.
3. Move the local bookmark to the deliberately chosen single result:
   `jj bookmark move NAME --to RESULT` (review any backwards-movement override).
4. For a conflicted recorded **remote** bookmark, fetch that remote again to
   reconcile its actual state, then inspect the propagated local result.

File conflicts, bookmark conflicts, and divergent change IDs need different
remedies. Don't run `restore` to resolve a bookmark conflict.

## Pull requests and code-host tools

Push the intended bookmark with jj, then use the hosting service's CLI/API if
requested. For GitHub, specify repository, base, and head explicitly where
needed, e.g. `gh pr create --repo OWNER/REPO --base BASE_BRANCH --head NAME ...`.
This is not a complete command: supply the requested title/body/options.

Do not use `gh pr checkout`, `gh repo sync`, or a wrapper that implicitly calls
Git checkout/pull/push in a jj working copy. In non-colocated workspaces, host
CLIs may need an explicit repository and occasionally a **command-scoped**
`GIT_DIR` set from `jj git root`; inspect the command and avoid persistent
exports that might redirect later Git operations.

## Colocated and non-colocated storage

In a colocated workspace, `.jj` and `.git` coexist. jj automatically
imports/exports Git refs during normal commands; manual `jj git import/export`
usually isn't needed. Git `HEAD` is commonly detached and generally represents
the parent of the jj working-copy commit rather than `@`. This is expected:
**do not repair detached HEAD with `git switch`**.

- Use jj for all supported version-control reads/writes. A Git-only read may
  see a different view, ignore `@`, or expose jj's internal preservation refs.
- Git's index does not select jj commit content. Avoid `git add`, `commit`,
  `reset`, `clean`, `checkout`, `switch`, `pull`, `merge`, `rebase`, and `push`
  as substitutes for jj commands.
- An unfinished Git merge/rebase or staged-only edits are not modeled like jj
  conflicts/index state. Stop and inspect; don't complete/abort them implicitly.
- Non-colocated and secondary jj workspaces can have no `.git` at their root.
  They are still jj workspaces. Don't infer their storage path or mutate files
  inside `.jj` manually.
- External Git mutations may appear in the operation log as imports. This
  interoperability is not a reason to interleave writes casually.

Git-backed jj interoperates with Git remotes, but is not feature-identical:
Git hooks, attributes/filter behavior, LFS, submodules, annotated tags, shallow
history, and Git worktrees have limitations that can change by version.
Review the version's compatibility docs before relying on them. If a needed
operation truly requires Git, explain the limitation and obtain agreement on a
narrowly scoped exception, then snapshot/review and inspect jj state afterward.
Never switch the whole workflow to Git just because the backend uses Git.

## Setup and configuration: only when requested

Preference alone is not permission to initialize or migrate a repository.
For an explicit setup/clone request, inspect local help and use the appropriate
form:

```sh
jj git clone URL DESTINATION
# Or, from an existing Git repository root, when migration is requested:
jj git init
```

Modern versions default to colocation; older versions/settings can differ.
Use explicit colocation flags only as needed for the user's chosen arrangement.
Don't change user-wide defaults as a side effect of a task.

Identity and jj configuration are separate from most Git configuration:

```sh
jj config get user.name
jj config get user.email
jj config path --repo
```

Ask for missing identity rather than inventing it. If configuration changes are
requested, prefer the narrowest appropriate scope (`--repo`, `--workspace`,
`--user`), verify supported options, and do not print unrelated secrets.
For one-off output choices use flags such as `--no-pager --color never` instead
of modifying global settings.

Signing uses jj's signing configuration/`jj sign`, not merely Git's signing
settings. Rewriting changes commit hashes/signatures and can trigger signing.
Don't disable signing, immutability, private-commit restrictions, or snapshot
limits simply to make an operation succeed.

## Official sources

- [Bookmarks](https://docs.jj-vcs.dev/latest/bookmarks/)
- [GitHub/GitLab workflows](https://docs.jj-vcs.dev/latest/github/)
- [Git compatibility](https://docs.jj-vcs.dev/latest/git-compatibility/)
- [Configuration](https://docs.jj-vcs.dev/latest/config/)
- [Installation and setup](https://docs.jj-vcs.dev/latest/install-and-setup/)
- [CLI reference](https://docs.jj-vcs.dev/latest/cli-reference/)
