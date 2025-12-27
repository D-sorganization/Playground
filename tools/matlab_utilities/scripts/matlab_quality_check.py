#!/usr/bin/env python3
"""
MATLAB Quality Check Tool

Performs quality checks on MATLAB code without requiring a MATLAB license.
This tool analyzes .m files for common issues and best practices.
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class MatlabQualityChecker:
    """Quality checker for MATLAB code."""

    def __init__(self) -> None:
        self.issues: list[dict[str, str | int]] = []
        self.stats: dict[str, int] = {
            "files_checked": 0,
            "functions_found": 0,
            "scripts_found": 0,
            "issues_found": 0,
        }

    def find_matlab_files(self, root_path: Path) -> list[Path]:
        """Find all MATLAB files in the directory tree."""
        matlab_files = []

        for file_path in root_path.rglob("*.m"):
            # Skip backup files and temporary files
            if file_path.name.endswith((".asv", ".m~")):
                continue
            # Skip files in .git and other version control directories
            if any(part.startswith(".") for part in file_path.parts):
                continue

            matlab_files.append(file_path)

        return matlab_files

    def analyze_file(self, file_path: Path) -> dict[str, Any]:
        """Analyze a single MATLAB file."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = content.split("\n")
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return {"type": "error", "issues": []}

        file_info: dict[str, Any] = {
            "path": str(file_path),
            "type": "unknown",
            "issues": [],
            "functions": [],
            "has_help": False,
            "line_count": len(lines),
        }

        # Determine file type and analyze
        self._determine_file_type(lines, file_info)
        self._check_documentation(lines, file_info)
        self._check_style_issues(lines, file_info)
        self._check_best_practices(lines, file_info)

        return file_info

    def _determine_file_type(self, lines: list[str], file_info: dict[str, Any]) -> None:
        """Determine if file is a function or script."""
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or line_clean.startswith("%"):
                continue

            # Check for function definition
            func_match = re.match(
                r"function\s+(?:\[.*?\]\s*=\s*|\w+\s*=\s*)?(\w+)", line_clean
            )
            if func_match:
                file_info["type"] = "function"
                file_info["functions"].append(
                    {
                        "name": func_match.group(1),
                        "line": i + 1,
                        "signature": line_clean,
                    }
                )
                self.stats["functions_found"] += 1
                return

            # If we hit executable code without function, it's a script
            if not re.match(r"^\s*(%|$)", line):
                file_info["type"] = "script"
                self.stats["scripts_found"] += 1
                return

    def _check_documentation(self, lines: list[str], file_info: dict[str, Any]) -> None:
        """Check for proper documentation."""
        # Look for help text (comments at the beginning)
        help_lines = 0
        in_help = False

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            if line_clean.startswith("%"):
                if not in_help:
                    in_help = True
                help_lines += 1
            elif in_help:
                break
            elif not line_clean.startswith("%"):
                break

        file_info["has_help"] = help_lines > 0

        if file_info["type"] == "function" and help_lines == 0:
            file_info["issues"].append(
                {
                    "type": "documentation",
                    "severity": "warning",
                    "message": "Function lacks help documentation",
                    "line": 1,
                }
            )

        # Check for function signature documentation
        if file_info["type"] == "function":
            has_input_doc = any(
                "%" in line and ("input" in line.lower() or "parameter" in line.lower())
                for line in lines[:20]
            )

            if not has_input_doc and len(file_info["functions"]) > 0:
                file_info["issues"].append(
                    {
                        "type": "documentation",
                        "severity": "info",
                        "message": "Consider documenting input parameters",
                        "line": 1,
                    }
                )

    def _check_style_issues(self, lines: list[str], file_info: dict[str, Any]) -> None:
        """Check for style and formatting issues."""
        for i, line in enumerate(lines, 1):
            # Check line length (MATLAB convention is often 75-80 chars)
            if len(line) > 100:
                file_info["issues"].append(
                    {
                        "type": "style",
                        "severity": "info",
                        "message": f"Long line ({len(line)} chars)",
                        "line": i,
                    }
                )

            # Check for semicolon usage (suppress output)
            line_clean = line.strip()
            if (
                line_clean
                and not line_clean.startswith("%")
                and not line_clean.endswith(";")
                and not line_clean.endswith("...")
                and "=" in line_clean
                and not any(
                    keyword in line_clean
                    for keyword in ["if", "for", "while", "function", "end"]
                )
            ):
                file_info["issues"].append(
                    {
                        "type": "style",
                        "severity": "info",
                        "message": "Consider adding semicolon to suppress output",
                        "line": i,
                    }
                )

    def _check_best_practices(
        self, lines: list[str], file_info: dict[str, Any]
    ) -> None:
        """Check for MATLAB best practices."""
        for i, line in enumerate(lines, 1):
            line_clean = line.strip().lower()

            # Check for clear/clc at beginning of scripts
            if (
                i <= 5
                and file_info["type"] == "script"
                and ("clear" in line_clean or "clc" in line_clean)
            ):
                file_info["issues"].append(
                    {
                        "type": "best_practice",
                        "severity": "warning",
                        "message": "Avoid clear/clc in reusable scripts",
                        "line": i,
                    }
                )

            # Check for magic numbers
            if re.search(r"\b[0-9]{3,}\b", line_clean) and not line_clean.startswith(
                "%"
            ):
                file_info["issues"].append(
                    {
                        "type": "best_practice",
                        "severity": "info",
                        "message": "Consider defining large numbers as named constants",
                        "line": i,
                    }
                )

    def generate_report(
        self, files_info: list[dict[str, Any]], output_format: str = "text"
    ) -> str:
        """Generate quality report."""
        if output_format == "text":
            return self._generate_text_report(files_info)
        elif output_format == "json":
            import json

            return json.dumps({"stats": self.stats, "files": files_info}, indent=2)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    def _generate_text_report(self, files_info: list[dict[str, Any]]) -> str:
        """Generate text format report."""
        report_lines = []
        report_lines.append("MATLAB Quality Check Report")
        report_lines.append("=" * 40)
        report_lines.append(f"Files checked: {self.stats['files_checked']}")
        report_lines.append(f"Functions found: {self.stats['functions_found']}")
        report_lines.append(f"Scripts found: {self.stats['scripts_found']}")
        report_lines.append(f"Total issues: {self.stats['issues_found']}")
        report_lines.append("")

        if self.stats["issues_found"] == 0:
            report_lines.append("✓ No issues found!")
            return "\n".join(report_lines)

        # Group issues by severity
        by_severity: dict[str, list[tuple[str, Any]]] = {
            "error": [],
            "warning": [],
            "info": [],
        }

        for file_info in files_info:
            for issue in file_info["issues"]:
                severity = issue.get("severity", "info")
                by_severity[severity].append((file_info["path"], issue))

        for severity in ["error", "warning", "info"]:
            issues = by_severity[severity]
            if issues:
                report_lines.append(f"{severity.upper()} ISSUES ({len(issues)}):")
                for file_path, issue in issues:
                    report_lines.append(
                        f"  {file_path}:{issue['line']} - {issue['message']}"
                    )
                report_lines.append("")

        return "\n".join(report_lines)

    def run_check(self, root_path: Path, output_format: str = "text") -> str:
        """Run the complete quality check."""
        logger.info(f"Scanning for MATLAB files in {root_path}")

        matlab_files = self.find_matlab_files(root_path)
        self.stats["files_checked"] = len(matlab_files)

        if not matlab_files:
            logger.info("No MATLAB files found")
            return "No MATLAB files found in the specified directory."

        logger.info(f"Found {len(matlab_files)} MATLAB files")

        files_info = []
        for file_path in matlab_files:
            file_info = self.analyze_file(file_path)
            files_info.append(file_info)
            issues_list = file_info["issues"]
            if isinstance(issues_list, list):
                self.stats["issues_found"] += len(issues_list)

        return self.generate_report(files_info, output_format)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MATLAB Quality Check Tool")
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to check (default: current directory)",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    checker = MatlabQualityChecker()
    root_path = Path(args.path)

    if not root_path.exists():
        logger.error(f"Path does not exist: {root_path}")
        sys.exit(1)

    try:
        report = checker.run_check(root_path, args.output_format)
        print(report)

        # Exit with error code if issues found (for CI)
        if checker.stats["issues_found"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"Error during quality check: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
