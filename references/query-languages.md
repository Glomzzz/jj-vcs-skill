# Revsets, filesets, and templates

Use after selecting jj. These are different languages: a revision selector is
not a path selector, and neither is an output template. Shell quoting is a
separate layer around all three. Verify expressions with read-only queries
before passing them to mutating commands.

## Revision symbols

| Expression | Meaning |
| --- | --- |
| `@` | Current workspace's working-copy commit. |
| `@-` | All parents of `@`, not necessarily one. |
| `@--` | Parents of parents, not an exact first-parent traversal. |
| `NAME` | A local bookmark, tag, or unambiguous ID. |
| `NAME@REMOTE` | Last recorded remote bookmark/tag position, not a live network query. |
| `WORKSPACE@` | Working-copy commit in another workspace. |
| `root()` | Virtual common root, not Git's initial commit. |
| `trunk()` | Configurable main-line alias; inspect its resolution. |

Prefer stable change IDs for evolving revisions. After divergence, a change ID
may resolve ambiguously: use an exact commit ID after inspecting the alternatives.
Short prefixes must be unambiguous. Symbols resolve tags before bookmarks before
IDs; `commit_id("HASH")` and `change_id("PREFIX")` can remove name ambiguity.

## Graph and set operators

| Expression | Selects |
| --- | --- |
| `X-`, `X+` | Parents, children. |
| `::X`, `X::` | Ancestors, descendants, including X itself. |
| `X::Y` | Commits descended from X and ancestral to Y, including endpoints. |
| `X..Y` | Ancestors of Y minus ancestors of X; X and Y need not be related. |
| `X | Y` | Union. |
| `X & Y` | Intersection. |
| `X ~ Y` | Set difference. |
| `~X` | Complement in the revset search space. |
| `all()` | Visible commits, plus history brought into scope by explicit hidden revisions. |

`X..Y` is not a literal path and `X::Y` is not Git's symmetric difference.
Parenthesize compound expressions. Quote expressions so the shell doesn't
interpret `|`, `&`, `~`, parentheses, or globs. A name ending in `-`, or containing
operators, may need inner string quotes too:

```sh
jj log -r '"release-"'       # The bookmark named release-, not its parents.
```

Many commands require exactly one revision. Never add an `all:` modifier or
broaden a revset merely to bypass a “multiple revisions” error. Inspect and
choose the intended targets explicitly.

## Useful queries

```sh
jj log -r 'all()'                           # Wider view than default log.
jj log -r 'ancestors(@, 10)'                 # Bounded ancestry.
jj log -r 'trunk()..@'                       # Current ancestry outside trunk.
jj log -r 'SOURCE::'                        # Descendants affected by -s rebase.
jj log -r 'mutable() & ::@'                 # Mutable ancestors of @.
jj log -r 'conflicts() & ::TIP'             # Conflicts in intended tip ancestry.
jj log -r 'divergent()'                     # Divergent changes.
jj log -r 'bookmarks() | remote_bookmarks()'
jj log -r 'remote_bookmarks(remote=origin)..@'
jj log -r 'files("src") & ::@'              # Commits modifying src.
```

`mine()` selects author email, not ownership of every edit or permission to
rewrite a commit. `mutable()` means jj permits rewriting, not that published
history is safe to rewrite. `empty()` means no delta relative to merged parents;
it does not mean a commit is disposable. `heads(SET)`/`roots(SET)` select the
DAG heads/roots within a set, not a timestamp ordering. `latest(SET)` uses time;
it does not select a task's semantic tip.

Default log output is filtered and configurable: a missing revision isn't proof
it was deleted. Explicit commit IDs, `jj evolog`, and old operations can expose
hidden history. `present(EXPR)` suppresses missing-revision errors: use it for
optional inspection, not to conceal a mistyped destination.

String-pattern defaults have changed across jj versions. For predictable
matching use explicit patterns such as `description(substring:"parser")`,
`author(exact:"person@example.com")`, or `bookmarks(glob:"feature/*")`.

## Filesets and literal paths

Paths are generally relative to the command's current directory, not always the
workspace root. Use root-relative patterns when the command may run below root.
`--` ends command-option parsing; it does **not** disable the fileset parser.

```sh
jj diff --git -- path/to/file
jj diff --git 'root:src'
jj diff --git 'glob:"**/*.rs"'
jj diff --git 'all() ~ root-file:package-lock.json'
jj diff --git 'file:"src/Foo(1).txt"'
jj file list 'src ~ glob:"**/*.generated.rs"'
```

- Bare paths can be prefix/glob patterns on current versions; don't assume
  special characters are literal.
- `file:"PATH"` is an exact cwd-relative path; `root-file:"PATH"` is exact and
  workspace-relative. `cwd:"PATH"`/`root:"PATH"` include a directory subtree.
- Shell quotes protect arguments from the shell; inner quotes protect names
  containing fileset operators/whitespace where required.
- Filesets support union `|`, intersection `&`, difference `~`, `all()`, and
  `none()`. Selecting a file selects all its changed hunks, not their authors.
- A fileset passed to `split` or `squash` restricts transferred content; preview
  the same fileset with `diff` before mutating.

## Machine-readable inspection

Do not parse the human log graph by column position or assume configured aliases
and templates are defaults. Request no graph, no color, and explicit templates:

```sh
jj --no-pager --color never log --no-graph -r @ -T 'change_id ++ "\n"'
jj --no-pager --color never log --no-graph -r @ -T 'commit_id ++ "\n"'
jj --no-pager --color never log --no-graph -r @ -T 'empty ++ "\n"'
jj --no-pager --color never log --no-graph -r 'trunk()..@' \
  -T 'change_id ++ " " ++ commit_id ++ "\n"'
```

For descriptions or arbitrary strings use JSON escaping rather than splitting
on newlines. On versions supporting `json()` and object literals:

```sh
jj --no-pager --color never log --no-graph -r @ \
  -T 'json({"change_id" => change_id, "commit_id" => commit_id, "description" => description}) ++ "\n"'
```

Test template support locally. Serialization details aren't guaranteed across
versions. Do not dump complete configuration or environment variables just to
parse status; they can contain sensitive data.

## Official sources

- [Revset language](https://docs.jj-vcs.dev/latest/revsets/)
- [Fileset language](https://docs.jj-vcs.dev/latest/filesets/)
- [Templating language](https://docs.jj-vcs.dev/latest/templates/)
- [Glossary](https://docs.jj-vcs.dev/latest/glossary/)
