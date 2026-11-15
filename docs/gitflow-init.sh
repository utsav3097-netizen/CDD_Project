#!/usr/bin/env bash
set -euo pipefail

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  printf 'Error: run this script from inside a Git repository.\n' >&2
  exit 1
fi

# Refuse to switch branches with uncommitted work, so initialization cannot
# disturb or strand the caller's changes.
if [[ -n "$(git status --porcelain)" ]]; then
  printf 'Error: working tree is not clean; commit or stash changes before initializing branches.\n' >&2
  exit 1
fi

if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  printf "Error: create the repository's first commit before initializing branches.\n" >&2
  exit 1
fi

branch_exists() {
  git show-ref --verify --quiet "refs/heads/$1"
}

create_branch_if_missing() {
  local branch="$1"
  local start_point="$2"
  if branch_exists "$branch"; then
    printf 'Keeping existing branch %s.\n' "$branch"
  else
    git branch "$branch" "$start_point"
    printf 'Created branch %s from %s.\n' "$branch" "$start_point"
  fi
}

create_branch_if_missing main HEAD
create_branch_if_missing develop main
create_branch_if_missing feature/valuation-engine develop
create_branch_if_missing feature/trustlend-qr develop
create_branch_if_missing feature/dealer-pool develop
create_branch_if_missing feature/gsap-ui develop

git switch develop
printf 'GitFlow branches are ready; current branch is develop.\n'
