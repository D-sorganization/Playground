"""Assessment Utilities."""

import logging
import re
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Assessment definitions matched to prompt


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
