#!/usr/bin/env python3
"""
Run a specific assessment (A-O) on the repository.

This script executes an individual assessment and generates a detailed report
based on actual code analysis.
"""

import argparse
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Assessment definitions matched to prompt
ASSESSMENTS = {
    "A": {"name": "Code Structure", "description": "Project organization and layout"},
    "B": {"name": "Documentation", "description": "Documentation quality and presence"},
    "C": {"name": "Test Coverage", "description": "Test quantity and coverage"},
    "D": {
        "name": "Error Handling",
        "description": "Exception management and robustness",
    },
    "E": {"name": "Performance", "description": "Efficiency and optimization"},
    "F": {"name": "Security", "description": "Security practices and vulnerabilities"},
    "G": {"name": "Dependencies", "description": "Dependency management"},
    "H": {"name": "CI/CD", "description": "Continuous Integration/Deployment"},
    "I": {"name": "Code Style", "description": "Linting and formatting compliance"},
    "J": {"name": "API Design", "description": "Interface clarity and consistency"},
    "K": {"name": "Data Handling", "description": "Data processing and storage"},
    "L": {"name": "Logging", "description": "Logging implementation"},
    "M": {"name": "Configuration", "description": "Configuration management"},
    "N": {"name": "Scalability", "description": "Ability to scale"},
    "O": {"name": "Maintainability", "description": "Ease of maintenance"},
}


def find_python_files() -> list[Path]:
    """Find all Python files in the repository."""
    python_files: list[Path] = []
    for pattern in ["**/*.py"]:
        python_files.extend(Path(".").glob(pattern))
    # Exclude common non-source directories
    excluded = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".tox",
        "build",
        "dist",
    }
    # Exclude self to avoid self-counting patterns
    return [
        f
        for f in python_files
        if not any(p in f.parts for p in excluded) and f.name != "run_assessment.py"
    ]


def run_ruff_check() -> dict[str, object]:
    """Run ruff and return statistics."""
    try:
        result = subprocess.run(
            ["ruff", "check", ".", "--statistics", "--output-format=json"],
            capture_output=True,
            text=True,
        )
        return {
            "exit_code": result.returncode,
            "output": result.stdout,
            "errors": result.stderr,
        }
    except FileNotFoundError:
        return {"exit_code": -1, "output": "", "errors": "ruff not installed"}


def run_black_check() -> dict[str, object]:
    """Run black check and return results."""
    try:
        result = subprocess.run(
            ["black", "--check", "--quiet", "."],
            capture_output=True,
            text=True,
        )
        return {
            "exit_code": result.returncode,
            "files_to_format": result.stdout.count("would reformat"),
        }
    except FileNotFoundError:
        return {"exit_code": -1, "files_to_format": 0, "errors": "black not installed"}


def count_test_files() -> int:
    """Count test files in the repository."""
    test_patterns = ["**/test_*.py", "**/*_test.py", "**/tests/*.py"]
    test_files: set[Path] = set()
    for pattern in test_patterns:
        test_files.update(Path(".").glob(pattern))
    return len(test_files)


def check_documentation() -> dict[str, bool]:
    """Check documentation status."""
    has_readme = Path("README.md").exists()
    has_docs = Path("docs").exists()
    has_changelog = Path("CHANGELOG.md").exists()
    has_agents = Path("AGENTS.md").exists()
    return {
        "has_readme": has_readme,
        "has_docs_dir": has_docs,
        "has_changelog": has_changelog,
        "has_agents": has_agents,
    }


def count_occurrences(pattern: str, files: list[Path]) -> int:
    """Count occurrences of a regex pattern in files."""
    count = 0
    for file in files:
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
            count += len(re.findall(pattern, content))
        except Exception:  # noqa: BLE001  # noqa: BLE001
            pass
    return count


# --- Per-assessment metric collectors ---


def _assess_code_structure(
    python_files: list[Path],
) -> tuple[list[str], int]:
    """Assessment A: Code Structure."""
    findings: list[str] = []
    score = 10
    file_count = len(python_files)
    has_src = Path("src").exists()
    has_tests = Path("tests").exists()
    has_scripts = Path("scripts").exists()
    findings.append(f"- Python files found: {file_count}")
    findings.append(f"- 'src/' directory: {'v' if has_src else 'x'}")
    findings.append(f"- 'tests/' directory: {'v' if has_tests else 'x'}")
    findings.append(f"- 'scripts/' directory: {'v' if has_scripts else 'x'}")
    if not has_src:
        score -= 2
    if not has_tests:
        score -= 1
    if not has_scripts:
        score -= 1
    return findings, score


def _assess_documentation(python_files: list[Path]) -> tuple[list[str], int]:  # noqa: ARG001
    """Assessment B: Documentation."""
    findings: list[str] = []
    score = 10
    docs = check_documentation()
    findings.append(f"- README.md: {'v' if docs['has_readme'] else 'x'}")
    findings.append(f"- docs/ directory: {'v' if docs['has_docs_dir'] else 'x'}")
    findings.append(f"- AGENTS.md: {'v' if docs['has_agents'] else 'x'}")
    if not docs["has_readme"]:
        score -= 3
    if not docs["has_docs_dir"]:
        score -= 1
    if not docs["has_agents"]:
        score -= 1
    return findings, score


def _assess_test_coverage(python_files: list[Path]) -> tuple[list[str], int]:  # noqa: ARG001
    """Assessment C: Test Coverage."""
    findings: list[str] = []
    score = 10
    test_count = count_test_files()
    findings.append(f"- Test files found: {test_count}")
    if test_count == 0:
        score -= 5
        findings.append("CRITICAL: No tests found!")
    elif test_count < 3:
        score -= 2
        findings.append("MAJOR: Very few tests found.")
    return findings, score


def _assess_error_handling(python_files: list[Path]) -> tuple[list[str], int]:
    """Assessment D: Error Handling."""
    findings: list[str] = []
    score = 10
    try_count = count_occurrences(r"try:", python_files)
    except_count = count_occurrences(r"except\s+.*:", python_files)
    bare_except_count = count_occurrences(r"except Exception as e:", python_files)  # noqa: BLE001
    findings.append(f"- Try blocks: {try_count}")
    findings.append(f"- Except blocks: {except_count}")
    findings.append(f"- Bare except blocks: {bare_except_count}")
    if bare_except_count > 0:
        score -= min(5, bare_except_count)
        findings.append(
            "MAJOR: Found "
            f"{bare_except_count} bare "
            "'except Exception as e:' blocks. "  # noqa: BLE001
            "Catch specific exceptions."
        )
    return findings, score


def _assess_performance(python_files: list[Path]) -> tuple[list[str], int]:
    """Assessment E: Performance."""
    findings: list[str] = []
    score = 10
    sleep_count = count_occurrences(r"time\.sleep\(", python_files)
    while_true_count = count_occurrences(r"while\s+True", python_files)
    findings.append(f"- time.sleep() calls: {sleep_count}")
    findings.append(f"- 'while True' loops: {while_true_count}")
    if sleep_count > 0:
        score -= int(min(4, sleep_count * 0.5))
        findings.append(
            "MAJOR: Avoid 'time.sleep()'; use async/await or event-driven design."
        )
    if while_true_count > 2:
        score -= 1
        findings.append(
            "MINOR: Check 'while True' loops for potential infinite blocking."
        )
    return findings, score


def _assess_security(python_files: list[Path]) -> tuple[list[str], int]:
    """Assessment F: Security."""
    findings: list[str] = []
    score = 10
    shell_true_count = count_occurrences(r"shell=True", python_files)
    hardcoded_secrets = count_occurrences(
        r"(?i)(api_key|password|secret)\s*=\s*['\"].+['\"]", python_files
    )
    findings.append(f"- shell=True usage: {shell_true_count}")
    findings.append(f"- Potential hardcoded secrets: {hardcoded_secrets}")
    if shell_true_count > 0:
        score -= min(5, shell_true_count * 2)
        findings.append("CRITICAL: Avoid 'shell=True' to prevent command injection.")
    if hardcoded_secrets > 0:
        score -= 5
        findings.append("CRITICAL: Potential hardcoded secrets detected.")
    return findings, score


def _assess_dependencies(python_files: list[Path]) -> tuple[list[str], int]:  # noqa: ARG001
    """Assessment G: Dependencies."""
    findings: list[str] = []
    score = 10
    has_reqs = Path("requirements.txt").exists() or Path("pyproject.toml").exists()
    findings.append(f"- requirements.txt/pyproject.toml: {'v' if has_reqs else 'x'}")
    if not has_reqs:
        score -= 5
    return findings, score


def _assess_cicd(python_files: list[Path]) -> tuple[list[str], int]:  # noqa: ARG001
    """Assessment H: CI/CD."""
    findings: list[str] = []
    score = 10
    workflows = (
        list(Path(".github/workflows").glob("*.yml"))
        if Path(".github/workflows").exists()
        else []
    )
    findings.append(f"- Workflows found: {len(workflows)}")
    if len(workflows) == 0:
        score -= 5
    return findings, score


def _assess_code_style(python_files: list[Path]) -> tuple[list[str], int]:  # noqa: ARG001
    """Assessment I: Code Style."""
    findings: list[str] = []
    score = 10
    ruff_result = run_ruff_check()
    black_result = run_black_check()
    ruff_status = "v passed" if ruff_result["exit_code"] == 0 else "x issues found"
    findings.append(f"- Ruff check: {ruff_status}")
    black_status = (
        "v formatted" if black_result["exit_code"] == 0 else "x needs formatting"
    )
    findings.append(f"- Black formatting: {black_status}")
    if ruff_result["exit_code"] != 0:
        score -= 2
    if black_result["exit_code"] != 0:
        score -= 1
    return findings, score


def _assess_api_design(python_files: list[Path]) -> tuple[list[str], int]:
    """Assessment J: API Design."""
    findings: list[str] = []
    score = 10
    func_defs = count_occurrences(r"def\s+\w+\(", python_files)
    type_hints = count_occurrences(r"def\s+\w+\(.*->", python_files)
    findings.append(f"- Function definitions: {func_defs}")
    findings.append(f"- Functions with return type hints: {type_hints}")
    if func_defs > 0:
        coverage = type_hints / func_defs
        findings.append(f"- Type hint coverage: {coverage:.1%}")
        if coverage < 0.5:
            score -= 3
            findings.append("MAJOR: Low type hint coverage (< 50%).")
        elif coverage < 0.8:
            score -= 1
            findings.append("MINOR: Improve type hint coverage (> 80%).")
    else:
        findings.append("- No functions found.")
    return findings, score


def _assess_data_handling(python_files: list[Path]) -> tuple[list[str], int]:
    """Assessment K: Data Handling."""
    findings: list[str] = []
    score = 10
    json_usage = count_occurrences(r"json\.(load|dump)", python_files)
    csv_usage = count_occurrences(r"csv\.(reader|writer)", python_files)
    open_usage = count_occurrences(r"open\(", python_files)
    sqlite_usage = count_occurrences(r"sqlite3", python_files)
    findings.append(f"- JSON operations: {json_usage}")
    findings.append(f"- CSV operations: {csv_usage}")
    findings.append(f"- File open() calls: {open_usage}")
    findings.append(f"- SQLite usage: {sqlite_usage}")
    if open_usage > 0 and (json_usage == 0 and csv_usage == 0 and sqlite_usage == 0):
        findings.append("INFO: Raw file I/O detected. Consider structured formats.")
    return findings, score


def _assess_logging(python_files: list[Path]) -> tuple[list[str], int]:
    """Assessment L: Logging."""
    findings: list[str] = []
    score = 10
    file_count = len(python_files)
    print_count = count_occurrences(r"(?m)^\s*print\(", python_files)
    logger_count = count_occurrences(
        r"logger\.(info|error|warning|debug)", python_files
    )
    findings.append(f"- print() calls: {print_count}")
    findings.append(f"- logger usages: {logger_count}")
    if print_count > 0:
        findings.append("MAJOR: 'print()' statements found. Use 'logging' instead.")
        score -= int(min(3, print_count * 0.1))
    if logger_count == 0 and file_count > 0:
        score -= 2
        findings.append("MINOR: No logging usage detected.")
    return findings, score


def _assess_configuration(python_files: list[Path]) -> tuple[list[str], int]:
    """Assessment M: Configuration."""
    findings: list[str] = []
    score = 10
    config_files = [
        "config.py",
        "settings.py",
        ".env",
        "pytest.ini",
        "tox.ini",
        "setup.cfg",
    ]
    found_configs = [f for f in config_files if Path(f).exists()]
    env_vars = count_occurrences(r"os\.(environ|getenv)", python_files)
    config_msg = ", ".join(found_configs) if found_configs else "None"
    findings.append(f"- Config files found: {config_msg}")
    findings.append(f"- Environment variable usage: {env_vars}")
    if not found_configs:
        score -= 2
        findings.append("MINOR: No standard configuration files found.")
    if env_vars == 0 and not found_configs:
        score -= 1
        findings.append(
            "MINOR: No configuration mechanism detected (env vars or config files)."
        )
    return findings, score


def _assess_scalability(python_files: list[Path]) -> tuple[list[str], int]:
    """Assessment N: Scalability."""
    findings: list[str] = []
    score = 10
    async_defs = count_occurrences(r"async\s+def", python_files)
    awaits = count_occurrences(r"\bawait\b", python_files)
    threading_import = count_occurrences(r"import\s+threading", python_files)
    multiprocessing_import = count_occurrences(
        r"import\s+multiprocessing", python_files
    )
    findings.append(f"- Async functions: {async_defs}")
    findings.append(f"- Await usage: {awaits}")
    findings.append(f"- Threading imports: {threading_import}")
    findings.append(f"- Multiprocessing imports: {multiprocessing_import}")
    if async_defs == 0 and threading_import == 0 and multiprocessing_import == 0:
        findings.append(
            "INFO: No concurrency patterns detected. Consider for scalability."
        )
    return findings, score


def _assess_maintainability(python_files: list[Path]) -> tuple[list[str], int]:
    """Assessment O: Maintainability."""
    findings: list[str] = []
    score = 10
    large_files = 0
    for f in python_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            line_count = len(text.splitlines())
            if line_count > 300:
                large_files += 1
        except Exception:  # noqa: BLE001  # noqa: BLE001
            pass
    findings.append(f"- Large files (>300 lines): {large_files}")
    if large_files > 0:
        score -= int(min(3, large_files * 0.5))
        findings.append(f"MAJOR: Found {large_files} large files. Refactor modules.")
    return findings, score


# Dispatch table mapping assessment IDs to their collector functions
_ASSESSMENT_COLLECTORS = {
    "A": _assess_code_structure,
    "B": _assess_documentation,
    "C": _assess_test_coverage,
    "D": _assess_error_handling,
    "E": _assess_performance,
    "F": _assess_security,
    "G": _assess_dependencies,
    "H": _assess_cicd,
    "I": _assess_code_style,
    "J": _assess_api_design,
    "K": _assess_data_handling,
    "L": _assess_logging,
    "M": _assess_configuration,
    "N": _assess_scalability,
    "O": _assess_maintainability,
}


def _collect_assessment_metrics(
    assessment_id: str, python_files: list[Path]
) -> tuple[list[str], int]:
    """Dispatch to the appropriate per-assessment collector.

    Args:
        assessment_id: Assessment ID (A-O).
        python_files: Python source files to analyse.

    Returns:
        (findings, score) tuple.
    """
    collector = _ASSESSMENT_COLLECTORS.get(assessment_id)
    if collector is not None:
        return collector(python_files)
    # Generic fallback
    findings = [
        f"- Python files analyzed: {len(python_files)}",
        "- Manual review recommended for detailed assessment",
    ]
    return findings, 7


def _assessment_header(assessment_id: str, assessment: dict, score: int) -> str:
    """Return the YAML-front-matter and score header lines for the report."""
    name = assessment["name"]
    description = assessment["description"]
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"# Assessment {assessment_id}: {name}\n\n"
        f"**Date**: {date_str}\n"
        f"**Assessment**: {assessment_id} - {name}\n"
        f"**Description**: {description}\n"
        "**Generated**: Automated via Jules Assessment Auto-Fix workflow\n\n"
        f"## Score: {score}/10\n"
    )


def _assessment_footer() -> str:
    """Return the Recommendations and Automation Notes sections."""
    return (
        "\n## Recommendations\n\n"
        "- Review findings above\n"
        "- Address any x items\n"
        "- Re-run assessment after fixes\n\n"
        "## Automation Notes\n\n"
        "This assessment was generated automatically. For detailed analysis:\n"
        "1. Run specific tools (ruff, black, pytest, etc.)\n"
        "2. Review code manually for context-specific issues\n"
        "3. Create GitHub issues for actionable items\n"
    )


def _build_assessment_markdown(
    assessment_id: str, assessment: dict, score: int, findings: list[str]
) -> str:
    """Return the complete markdown report string for an assessment."""
    findings_block = "\n## Findings\n\n" + chr(10).join(findings)
    return (
        _assessment_header(assessment_id, assessment, score)
        + findings_block
        + _assessment_footer()
    )


def _write_assessment_report(
    assessment_id: str,
    assessment: dict,
    score: int,
    findings: list[str],
    output_path: Path,
) -> None:
    """Build markdown report and write to output_path."""
    report_content = _build_assessment_markdown(
        assessment_id, assessment, score, findings
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as output_file:
        output_file.write(report_content)


def run_assessment(assessment_id: str, output_path: Path) -> int:
    """
    Run a specific assessment and generate report.

    Args:
        assessment_id: Assessment ID (A-O)
        output_path: Path to save the assessment report

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    assessment = ASSESSMENTS.get(assessment_id)
    if not assessment:
        logger.error("Unknown assessment: %s", assessment_id)
        return 1

    logger.info("Running Assessment %s: %s...", assessment_id, assessment["name"])

    python_files = find_python_files()
    findings, score = _collect_assessment_metrics(assessment_id, python_files)
    score = max(0, min(10, round(score, 1)))

    _write_assessment_report(assessment_id, assessment, score, findings, output_path)

    logger.info("+ Assessment %s report saved to %s", assessment_id, output_path)
    logger.info("  Score: %s/10", score)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repository assessment")
    parser.add_argument(
        "--assessment",
        required=True,
        choices=list("ABCDEFGHIJKLMNO"),
        help="Assessment ID (A-O)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output file path for assessment report",
    )

    args = parser.parse_args()

    exit_code = run_assessment(args.assessment, args.output)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
