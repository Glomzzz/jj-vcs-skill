#!/bin/sh
# Select the VCS for a filesystem directory without snapshotting or initializing.
# stdout: jj|git (exit 0), none (exit 1); diagnostics only on failure (exit 2).
set -eu

if [ "$#" -gt 1 ]; then
    printf '%s\n' 'Usage: detect-vcs.sh [directory]' >&2
    exit 2
fi

# These must not redirect Git's probe into a different repository. This script
# runs in its own process; it does not change the caller's environment.
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_INDEX_FILE

target=${1:-.}
case "$target" in
    /*) ;;
    *) target=./$target ;;
esac
if ! CDPATH= cd -P "$target"; then
    printf 'Cannot inspect directory: %s\n' "$target" >&2
    exit 2
fi
directory=$(pwd -P)

has_marker() {
    [ -d "$1" ] || [ -f "$1" ] || [ -L "$1" ]
}

has_git() {
    command -v git >/dev/null 2>&1 &&
        git -C "$1" rev-parse --git-dir >/dev/null 2>&1
}

while :; do
    if has_marker "$directory/.jj" || has_marker "$directory/.git"; then
        if has_marker "$directory/.jj"; then
            if command -v jj >/dev/null 2>&1; then
                # -R pins discovery to this boundary. Unlike `jj root`, log
                # actually loads the repo, so an empty/broken .jj won't pass.
                # --at-op=@ also prevents integrating concurrent operations.
                if jj --ignore-working-copy --at-op=@ --no-pager --color never \
                    -R "$directory" log --no-graph -r @ -T commit_id >/dev/null; then
                    printf '%s\n' jj
                    exit 0
                fi
                printf 'jj workspace could not be opened at %s; refusing silent Git fallback.\n' \
                    "$directory" >&2
                exit 2
            fi
            printf 'jj is unavailable; checking for a usable Git repository at %s.\n' \
                "$directory" >&2
        fi
        if has_marker "$directory/.git" && has_git "$directory"; then
            printf '%s\n' git
            exit 0
        fi
        printf 'Repository marker found at %s, but no usable VCS could be opened.\n' \
            "$directory" >&2
        exit 2
    fi
    [ "$directory" != / ] || break
    directory=${directory%/*}
    [ -n "$directory" ] || directory=/
done

# Bare Git repos have no .git marker. Git also respects its normal discovery
# rules here (e.g. filesystem boundaries); no repository is created.
if has_git .; then
    printf '%s\n' git
    exit 0
fi
printf '%s\n' none
exit 1
