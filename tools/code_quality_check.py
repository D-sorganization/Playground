#!/usr/bin/env python3
"""
Code Quality Check Tool

Validates code quality standards for the playground repository.
This tool checks for placeholders, magic numbers, and other quality issues.
"""

import logging
import re
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class QualityChecker:
    """Code quality checker for playground repository."""

    def __init__(self) -> None:
        self.issues: list[tuple[str, str, int, str]] = []
        self.exclude_patterns = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "node_modules",
            "vendor",
            ".venv",
            "venv",
            ".benchmarks",
        }
        self.exclude_extensions = {".md", ".txt", ".yml", ".yaml", ".json"}

    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped based on patterns."""
        # Skip if any parent directory matches exclude patterns
        for part in file_path.parts:
            if part in self.exclude_patterns:
                return True

        # Skip certain file extensions
        if file_path.suffix in self.exclude_extensions:
            return True

        return False

    def check_placeholders(self, file_path: Path) -> None:
        """Check for TODO/FIXME placeholders."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line_clean = line.strip()
                    if re.search(
                        r"\b(TODO|FIXME|XXX|HACK)\b", line_clean, re.IGNORECASE
                    ):
                        self.issues.append(
                            (
                                str(file_path),
                                "placeholder",
                                line_num,
                                f"Found placeholder: {line_clean[:80]}",
                            )
                        )
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")

    def check_magic_numbers(self, file_path: Path) -> None:
        """Check for magic numbers in Python files."""
        if file_path.suffix != ".py":
            return

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Look for numeric literals that might be magic numbers
            # Exclude common acceptable numbers (0, 1, 2, 100, etc.)
            magic_pattern = r"\b(?<![\w.])[3-9]\d{2,}|[1-9]\d{3,}\b(?![\w.])"

            for line_num, line in enumerate(content.split("\n"), 1):
                # Skip comments and strings
                if re.match(r"^\s*#", line) or '"""' in line or "'''" in line:
                    continue

                matches = re.finditer(magic_pattern, line)
                for match in matches:
                    # Skip if it's in a string literal
                    if self._in_string_literal(line, match.start()):
                        continue

                    self.issues.append(
                        (
                            str(file_path),
                            "magic_number",
                            line_num,
                            f"Potential magic number: {match.group()} in "
                            f"'{line.strip()[:60]}'",
                        )
                    )
        except Exception as e:
            logger.warning(f"Could not analyze {file_path}: {e}")

    def _in_string_literal(self, line: str, pos: int) -> bool:
        """Check if position is inside a string literal."""
        # Simple heuristic - count quotes before position
        before = line[:pos]
        single_quotes = before.count("'") - before.count("\\'")
        double_quotes = before.count('"') - before.count('\\"')

        return (single_quotes % 2 == 1) or (double_quotes % 2 == 1)

    def check_imports(self, file_path: Path) -> None:
        """Check for wildcard imports in Python files."""
        if file_path.suffix != ".py":
            return

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    if re.match(r"^\s*from\s+\w+\s+import\s+\*", line):
                        self.issues.append(
                            (
                                str(file_path),
                                "wildcard_import",
                                line_num,
                                f"Wildcard import found: {line.strip()}",
                            )
                        )
        except Exception as e:
            logger.warning(f"Could not check imports in {file_path}: {e}")

    def run_checks(self, root_path: Path | None = None) -> int:
        """Run all quality checks."""
        if root_path is None:
            root_path = Path.cwd()

        logger.info(f"Running quality checks in {root_path}")

        # Find all files to check
        files_to_check = []
        for file_path in root_path.rglob("*"):
            if file_path.is_file() and not self.should_skip_file(file_path):
                files_to_check.append(file_path)

        logger.info(f"Checking {len(files_to_check)} files")

        # Run checks
        for file_path in files_to_check:
            self.check_placeholders(file_path)
            self.check_magic_numbers(file_path)
            self.check_imports(file_path)

        # Report results
        if self.issues:
            logger.error(f"Found {len(self.issues)} quality issues:")

            # Group by issue type
            by_type: dict[str, list[tuple[str, int, str]]] = {}
            for file_path_str, issue_type, line_num, message in self.issues:
                if issue_type not in by_type:
                    by_type[issue_type] = []
                by_type[issue_type].append((file_path_str, line_num, message))

            for issue_type, issues in by_type.items():
                print(f"\n{issue_type.upper()} ISSUES ({len(issues)}):")
                for file_path_str, line_num, message in issues[:10]:  # Limit output
                    print(f"  {file_path_str}:{line_num} - {message}")
                if len(issues) > 10:
                    print(f"  ... and {len(issues) - 10} more")

            return 1
        else:
            logger.info("✓ No quality issues found")
            return 0


def main() -> None:
    """Main entry point."""
    checker = QualityChecker()
    exit_code = checker.run_checks()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
