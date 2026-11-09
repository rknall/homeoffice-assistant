#!/usr/bin/env bash
# PreToolUse hook (Bash): block python/python3/pip run outside `uv run` / `uvx`.
# Reads the hook JSON on stdin; exit 2 blocks the call and shows stderr to the model.
# ponytail: regex over command segments, not a shell parser; a python call hidden
# inside `bash -c '...'` or an alias slips through.

cmd=$(jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0

# A segment starts at line start or after ; & | ( ` or $( . Optional env assignments
# and wrapper words (sudo, env, exec, command, time, nohup, xargs) may come first.
pattern='(^|[;&|(`]|\$\()[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*((sudo|env|exec|command|time|nohup|xargs)[[:space:]]+)*([^[:space:]]*/)?(python[0-9.]*|pip[0-9.]*)([[:space:]]|$)'

if printf '%s\n' "$cmd" | grep -Eq "$pattern"; then
  echo "Blocked: run Python through uv (\`uv run python ...\`, \`uv run --no-project python -I ...\` or \`uvx ...\`), never bare python, python3 or pip. See CLAUDE.md." >&2
  exit 2
fi
exit 0
