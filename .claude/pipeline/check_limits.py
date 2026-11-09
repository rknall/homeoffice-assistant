"""Enforce pipeline document limits.

Hook mode (PostToolUse on Write/Edit): check_limits.py --hook reads the hook
JSON from stdin and exits 2 with a message the agent sees.
CLI mode: check_limits.py <file-or-dir>... checks every .md below the paths.
Self-check: check_limits.py --selftest
"""

import json
import re
import sys
from pathlib import Path

DONE_TODO = re.compile(r"^\s*[-*]\s*\[[xX]\]|^\s*[-*]\s*~~.*~~\s*$")
INSTRUCTION_FILES = ("claude.md", "claude.local.md", "copilot-instructions.md")


def limit_for(path: Path) -> tuple[int | None, bool] | None:
    """Return (max_lines, check_done_todos) for a path, or None if unchecked."""
    name = path.name.lower()
    if not name.endswith(".md"):
        return None
    if name in INSTRUCTION_FILES:
        return 200, False
    if any(k in name for k in ("handover", "todo", "checklist")):
        return 70, True
    parts = path.parts
    in_specs = "specs" in parts and "docs" in parts
    if in_specs and "work" in parts:
        # Design documents carry the overflow, only TODO hygiene applies.
        return (None if "design" in parts else 200), True
    if in_specs:
        return None, True
    return None


def problems(path: Path) -> list[str]:
    """Return the limit violations of one file."""
    rule = limit_for(path)
    if rule is None or not path.is_file():
        return []
    max_lines, check_todos = rule
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    if max_lines is not None and len(lines) > max_lines:
        out.append(
            f"{path}: {len(lines)} lines, limit {max_lines}. "
            "Move detail into a design document and reference it."
        )
    if check_todos:
        done = [i + 1 for i, line in enumerate(lines) if DONE_TODO.match(line)]
        if done:
            out.append(f"{path}: finished TODOs on lines {done[:10]}. Delete them.")
    return out


def main(argv: list[str]) -> int:
    """Run in hook or CLI mode and return the exit code."""
    if argv[1:2] == ["--hook"]:
        data = json.load(sys.stdin)
        fp = (data.get("tool_input") or {}).get("file_path")
        found = problems(Path(fp)) if fp else []
    else:
        found = []
        for arg in argv[1:]:
            p = Path(arg)
            for f in sorted(p.rglob("*.md")) if p.is_dir() else [p]:
                found += problems(f)
    for msg in found:
        print(msg, file=sys.stderr)
    return 2 if found else 0


def selftest() -> None:
    """Check the limit rules against temporary files."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        work = root / "docs" / "specs" / "t" / "work"
        (work / "design").mkdir(parents=True)
        (work / "plan-review-r1.md").write_text("x\n" * 201)
        (work / "design" / "long.md").write_text("x\n" * 500)
        (work / "handover.md").write_text("- [ ] open\n" + "x\n" * 69)
        (work / "todo-r1.md").write_text("- [x] closed\n")
        (root / "docs" / "specs" / "t" / "plan.md").write_text("x\n" * 400)
        (root / "CLAUDE.md").write_text("x\n" * 200)
        (root / "copilot-instructions.md").write_text("x\n" * 201)
        (root / "README.md").write_text("x\n" * 999)
        assert problems(work / "plan-review-r1.md")
        assert not problems(work / "design" / "long.md")
        assert not problems(work / "handover.md")
        assert problems(work / "todo-r1.md")
        assert not problems(root / "docs" / "specs" / "t" / "plan.md")
        assert not problems(root / "CLAUDE.md")
        assert problems(root / "copilot-instructions.md")
        assert not problems(root / "README.md")
        (work / "handover.md").write_text("x\n" * 71)
        assert problems(work / "handover.md")
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selftest"]:
        selftest()
    else:
        sys.exit(main(sys.argv))
