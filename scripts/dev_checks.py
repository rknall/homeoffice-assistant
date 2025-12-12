#!/usr/bin/env python3
"""Utility runners for combined linting and testing."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
FILE_LINE_PATTERN = re.compile(r"^\s*(?P<path>(?:\.{1,2}/)?[^\s:]+):\d+:\d+")
SUMMARY_LINE_PATTERN = re.compile(r"=+\s+(?P<body>.+?)\s+=+")


@dataclass
class ToolResult:
    """Container for the outcome of a single tool execution."""

    name: str
    returncode: int
    stdout: str
    stderr: str
    per_file: Counter[str]
    extra: dict[str, str] | None = None

    @property
    def ok(self) -> bool:
        """Return True when the tool exited successfully."""
        return self.returncode == 0


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes so downstream parsing stays reliable."""
    return ANSI_ESCAPE.sub("", text)


def normalize_path(raw_path: str) -> str:
    """Convert tool-reported paths into workspace-relative POSIX strings."""
    cleaned = raw_path.strip().lstrip("./")
    if not cleaned:
        return raw_path
    if os.path.isabs(cleaned):
        path_obj = Path(cleaned).resolve()
    else:
        path_obj = (ROOT_DIR / cleaned).resolve()
    try:
        return path_obj.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return path_obj.as_posix()


def collect_file_counts(text: str) -> Counter[str]:
    """Return how many diagnostics each file produced based on textual output."""
    counts: Counter[str] = Counter()
    for line in strip_ansi(text).splitlines():
        match = FILE_LINE_PATTERN.match(line)
        if not match:
            continue
        path = normalize_path(match.group("path"))
        counts[path] += 1
    return counts


def run_command(name: str, cmd: list[str], cwd: Path) -> ToolResult:
    """Execute a subprocess and capture its output for later parsing."""
    env = os.environ.copy()
    env.setdefault("FORCE_COLOR", "0")
    try:
        completed = subprocess.run(  # noqa: S603
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}"
        per_file = collect_file_counts(combined_output)
        return ToolResult(
            name=name,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            per_file=per_file,
        )
    except FileNotFoundError as exc:
        message = f"Command not found for {name}: {exc.filename}"
        return ToolResult(
            name=name,
            returncode=127,
            stdout="",
            stderr=message,
            per_file=Counter(),
        )


def summarize_file_counts(per_file: Counter[str]) -> tuple[int, str]:
    """Aggregate per-file diagnostics into a human readable line."""
    total = sum(per_file.values())
    if total == 0:
        return 0, "clean"
    lines = [f"{path} ({count})" for path, count in sorted(per_file.items())]
    return total, ", ".join(lines)


def format_test_counts(counts: dict[str, int]) -> str:
    """Render parsed test statistics into a concise status string."""
    if not counts:
        return "see raw output"
    ordered = [f"{value} {key}" for key, value in counts.items()]
    return " | ".join(ordered)


def parse_pytest_summary(text: str) -> dict[str, int]:
    """Extract pytest's final summary counts from its textual output."""
    clean_text = strip_ansi(text)
    for line in reversed(clean_text.splitlines()):
        match = SUMMARY_LINE_PATTERN.match(line.strip())
        if not match:
            continue
        body = match.group("body")
        stats: dict[str, int] = {}
        for chunk in body.split(","):
            chunk = chunk.strip()
            chunk = chunk.split(" in ")[0]
            parts = chunk.split()
            if len(parts) < 2:
                continue
            count_part, label = parts[0], parts[1]
            if count_part.isdigit():
                stats[label] = int(count_part)
        if stats:
            return stats
    return {}


def parse_vitest_summary(text: str) -> dict[str, int]:
    """Pull vitest summary lines into a structured dictionary."""
    clean_text = strip_ansi(text)
    stats: dict[str, int] = {}
    for line in clean_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Tests ") or stripped.startswith("Test Files"):
            tokens = [token for token in re.split(r"[|()]+", stripped) if token.strip()]
            for token in tokens:
                parts = token.strip().split()
                if len(parts) >= 2 and parts[0].isdigit():
                    stats[" ".join(parts[1:])] = int(parts[0])
    return stats


def print_lint_summary(results: Iterable[ToolResult]) -> None:
    """Display aggregate lint information across all tools."""
    print("Lint summary")
    for result in results:
        total, detail = summarize_file_counts(result.per_file)
        status = detail if total else "clean"
        state = "OK" if result.ok else "FAIL"
        print(f"- {result.name}: {state} | {status}")
    print()


def print_test_summary(pytest_result: ToolResult, vitest_result: ToolResult) -> None:
    """Display aggregate test outcomes for backend and frontend suites."""
    print("Test summary")
    pytest_counts = parse_pytest_summary(
        f"{pytest_result.stdout}\n{pytest_result.stderr}"
    )
    vitest_counts = parse_vitest_summary(
        f"{vitest_result.stdout}\n{vitest_result.stderr}"
    )
    print(
        f"- Pytest: {'OK' if pytest_result.ok else 'FAIL'} | "
        f"{format_test_counts(pytest_counts)}"
    )
    print(
        f"- Vitest: {'OK' if vitest_result.ok else 'FAIL'} | "
        f"{format_test_counts(vitest_counts)}"
    )
    print()


def run_lint(verbose: bool, fix: bool) -> int:
    """Run backend and frontend linters and print combined results."""
    print("Running lint checks...\n")
    ruff_cmd = ["ruff", "check", "."]
    if fix:
        ruff_cmd.append("--fix")
    biome_cmd = ["npm", "run", "lint:fix" if fix else "lint"]
    ruff = run_command("Ruff", ruff_cmd, ROOT_DIR)
    biome = run_command("Frontend lint", biome_cmd, FRONTEND_DIR)
    print_lint_summary([ruff, biome])
    _print_failure_snippets([ruff, biome], verbose)
    if verbose:
        _print_verbose_output([ruff, biome])
    return 0 if ruff.ok and biome.ok else 1


def run_tests(verbose: bool) -> int:
    """Run backend and frontend unit tests with a combined summary."""
    print("Running unit tests...\n")
    pytest_result = run_command("Pytest", ["pytest"], ROOT_DIR)
    vitest_result = run_command("Vitest", ["npm", "run", "test"], FRONTEND_DIR)
    print_test_summary(pytest_result, vitest_result)
    _print_failure_snippets([pytest_result, vitest_result], verbose)
    if verbose:
        _print_verbose_output([pytest_result, vitest_result])
    return 0 if pytest_result.ok and vitest_result.ok else 1


def _print_verbose_output(results: Iterable[ToolResult]) -> None:
    """Dump raw stdout/stderr content for debugging purposes."""
    for result in results:
        print(f"=== {result.name} stdout ===")
        print(result.stdout or "<empty>")
        print(f"=== {result.name} stderr ===")
        print(result.stderr or "<empty>")
        print()


def _print_failure_snippets(results: Iterable[ToolResult], verbose: bool) -> None:
    """Show short excerpts for failed tools when not in verbose mode."""
    if verbose:
        return
    for result in results:
        if result.ok:
            continue
        print(f"{result.name} failed (exit code {result.returncode}).")
        snippet = _build_output_snippet(result)
        print(snippet)
        print("  ↪ Re-run with --verbose for full logs.\n")


def _build_output_snippet(result: ToolResult, limit: int = 8) -> str:
    """Return the first handful of meaningful output lines for a tool."""
    combined = f"{result.stdout}\n{result.stderr}"
    lines = [line.strip() for line in strip_ansi(combined).splitlines() if line.strip()]
    if not lines:
        return "  (no output captured)"
    trimmed = lines[:limit]
    snippet = "\n".join(f"  {line}" for line in trimmed)
    remaining = len(lines) - limit
    if remaining > 0:
        snippet += f"\n  ... ({remaining} more lines)"
    return snippet


def main() -> None:
    """Entry point for the developer convenience CLI."""
    parser = argparse.ArgumentParser(
        description="Run combined lint or test suites with summaries."
    )
    parser.add_argument(
        "target",
        choices=["lint", "test", "all"],
        default="all",
        nargs="?",
        help="Which set of checks to run (default: all).",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply automatic fixes for linting commands.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full stdout/stderr for each tool.",
    )
    args = parser.parse_args()

    exit_code = 0
    if args.target in {"lint", "all"}:
        exit_code |= run_lint(verbose=args.verbose, fix=args.fix)
    if args.target in {"test", "all"}:
        exit_code |= run_tests(verbose=args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
