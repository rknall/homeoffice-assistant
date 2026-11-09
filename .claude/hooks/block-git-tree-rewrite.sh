#!/usr/bin/env bash
# PreToolUse hook (Bash): block git commands that rewrite the shared working tree
# (stash, checkout, reset, restore). Parallel agents edit one tree, so these can
# silently drop or hide other agents' edits. `git stash list` / `git stash show`
# stay allowed; use `git switch` to change branches.
# ponytail: regex over command segments, not a shell parser; `bash -c '...'` slips through.

cmd=$(jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0

seg='(^|[;&|(`]|\$\()[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*'
git_opts='git([[:space:]]+(-C[[:space:]]+[^[:space:]]+|-c[[:space:]]+[^[:space:]]+|--[a-z-]+(=[^[:space:]]+)?))*[[:space:]]+'
# Each match carries the subcommand plus its next word, so every match is judged alone.
pattern="${seg}${git_opts}(stash|checkout|reset|restore)([[:space:]]+[^[:space:];&|)]+)?"
allowed="stash[[:space:]]+(list|show)$"

while IFS= read -r m; do
  [ -z "$m" ] && continue
  if ! printf '%s\n' "$m" | grep -Eq "$allowed"; then
    echo "Blocked: git stash/checkout/reset/restore rewrite the shared working tree that parallel agents edit. Use read-only git (status, diff, log, show, stash list) or git switch for branches. Ask the user if you really need this." >&2
    exit 2
  fi
done < <(printf '%s\n' "$cmd" | grep -Eo "$pattern")
exit 0
