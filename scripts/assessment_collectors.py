"""Assessment Collectors."""

import logging
from pathlib import Path

from assessment_utils import (
    check_documentation,
    count_occurrences,
    count_test_files,
    run_black_check,
    run_ruff_check,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Assessment definitions matched to prompt


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
