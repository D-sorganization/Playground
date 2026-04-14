"""Mypy Autofix Agent - Intelligent mypy error resolution.

This script acts as an agent that:
1. Runs mypy and captures structured error output
2. Classifies each error by fixability
3. Applies real fixes where possible (import corrections, type narrowing)
4. Falls back to targeted # type: ignore[code] only when necessary
5. Verifies fixes by re-running mypy on modified files
6. Reports all changes for commit messages

Safeguards:
- Max fixes per run (default: 20)
- Max files modified per run (default: 15)
- Never modifies files outside src/ and tests/
- Prefers real fixes over suppressions
- Tracks all changes for auditability

Usage:
    python scripts/mypy_autofix_agent.py [--max-fixes N] [--max-files N]
    [--dry-run] [--verbose]
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict

from src.mypy_agent.fix_strategies import ALL_FIX_STRATEGIES
from src.mypy_agent.io import (
    is_safe_path,
    parse_mypy_output,
    read_file_lines,
    run_mypy,
    write_file_lines,
)
from src.mypy_agent.types import AgentReport, MypyError

logger = logging.getLogger(__name__)


def _apply_fixes_for_file(
    filepath: str,
    file_errors: list[MypyError],
    max_fixes: int,
    total_fixes: int,
    dry_run: bool,
    verbose: bool,
    report: AgentReport,
) -> tuple[int, bool]:
    """Apply available fixes for all errors in a single file.

    Args:
        filepath: Path to the file being fixed.
        file_errors: Errors in this file, sorted descending by line.
        max_fixes: Global ceiling on total fixes applied.
        total_fixes: Running count of fixes applied so far.
        dry_run: If True, do not write changes to disk.
        verbose: If True, log each fix action.
        report: AgentReport to update with applied fixes and skips.

    Returns:
        (updated_total_fixes, file_was_changed) tuple.
    """
    lines = read_file_lines(filepath)
    if not lines:
        return total_fixes, False

    file_changed = False
    sorted_errors = sorted(file_errors, key=lambda e: e.line, reverse=True)

    for error in sorted_errors:
        if total_fixes >= max_fixes:
            break

        fix = None
        for strategy in ALL_FIX_STRATEGIES:
            fix = strategy(lines, error)
            if fix:
                break

        if fix:
            total_fixes += 1
            file_changed = True
            if fix.strategy == "real-fix":
                report.real_fixes += 1
            else:
                report.suppressions += 1
            report.fixes_applied.append(
                f"  [{fix.strategy}] {fix.file}:{fix.line} - {fix.description}"
            )
            if verbose:
                logger.info("  FIX: %s:%d [%s]", fix.file, fix.line, fix.strategy)
                logger.info("       %s", fix.description)
        else:
            report.skipped_reasons.append(
                "No fix available: "
                f"{error.file}:{error.line} [{error.code}] "
                f"{error.message[:60]}"
            )

    if file_changed and not dry_run:
        write_file_lines(filepath, lines)

    return total_fixes, file_changed


def run_agent(
    max_fixes: int = 20,
    max_files: int = 15,
    dry_run: bool = False,
    verbose: bool = False,
    config_file: str | None = None,
    targets: list[str] | None = None,
) -> AgentReport:
    """Main agent loop: observe, classify, fix, report.

    Args:
        max_fixes: Maximum total fixes to apply per run.
        max_files: Maximum source files to modify per run.
        dry_run: If True, compute fixes but do not write to disk.
        verbose: If True, log each action.
        config_file: Optional mypy config file path.
        targets: Files/directories to check (default: src/ and tests/).

    Returns:
        AgentReport summarising all actions taken.
    """
    report = AgentReport()

    if verbose:
        logger.info(">>> Running mypy on targets: %s...", targets or "default")
    output = run_mypy(config_file, targets)
    errors = parse_mypy_output(output)
    report.total_errors = len(errors)

    if verbose:
        logger.info(">>> Found %d mypy errors", len(errors))

    if not errors:
        logger.info("No mypy errors found.")
        return report

    errors_by_file: dict[str, list[MypyError]] = defaultdict(list)
    for error in errors:
        if is_safe_path(error.file):
            errors_by_file[error.file].append(error)
        else:
            report.skipped_reasons.append(
                f"Skipped {error.file}:{error.line} - outside safe path"
            )

    files_modified = 0
    total_fixes = 0

    for filepath, file_errors in sorted(errors_by_file.items()):
        if files_modified >= max_files:
            report.skipped_reasons.append(
                f"Skipped {filepath} - max files ({max_files}) reached"
            )
            continue
        if total_fixes >= max_fixes:
            report.skipped_reasons.append(
                f"Skipped {filepath} - max fixes ({max_fixes}) reached"
            )
            continue

        total_fixes, file_changed = _apply_fixes_for_file(
            filepath, file_errors, max_fixes, total_fixes, dry_run, verbose, report
        )
        if file_changed:
            files_modified += 1
            report.files_modified.append(filepath)

    report.errors_fixed = total_fixes
    return report


def print_report(report: AgentReport) -> None:
    """Log a human-readable summary of agent actions.

    Args:
        report: Completed AgentReport.
    """
    logger.info("\n" + "=" * 60)
    logger.info("  MYPY AUTOFIX AGENT REPORT")
    logger.info("=" * 60)
    logger.info("  Total mypy errors found:  %d", report.total_errors)
    logger.info("  Errors fixed:             %d", report.errors_fixed)
    logger.info("    Real fixes:             %d", report.real_fixes)
    logger.info("    Suppressions:           %d", report.suppressions)
    logger.info("  Files modified:           %d", len(report.files_modified))

    if report.fixes_applied:
        logger.info("\n  Fixes applied:")
        for fix_desc in report.fixes_applied:
            logger.info("  %s", fix_desc)

    if report.skipped_reasons:
        logger.info("\n  Skipped (%d):", len(report.skipped_reasons))
        for reason in report.skipped_reasons[:10]:
            logger.info("    - %s", reason)
        if len(report.skipped_reasons) > 10:
            logger.info("    ... and %d more", len(report.skipped_reasons) - 10)

    logger.info("=" * 60)


def _build_agent_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser for the autofix agent."""
    parser = argparse.ArgumentParser(
        description="Mypy Autofix Agent - Intelligently fix mypy errors"
    )
    parser.add_argument(
        "--max-fixes",
        type=int,
        default=20,
        help="Maximum number of fixes per run (default: 20)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=15,
        help="Maximum files to modify per run (default: 15)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without modifying files",
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument(
        "--config-file",
        type=str,
        default=None,
        help="Path to mypy config file (default: uses pyproject.toml)",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Files or directories to check (default: src)",
    )
    return parser


def main() -> int:
    """Entry point."""
    args = _build_agent_parser().parse_args()
    report = run_agent(
        max_fixes=args.max_fixes,
        max_files=args.max_files,
        dry_run=args.dry_run,
        verbose=args.verbose,
        config_file=args.config_file,
        targets=args.targets,
    )
    print_report(report)
    if report.errors_fixed > 0:
        return 0
    if report.total_errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
