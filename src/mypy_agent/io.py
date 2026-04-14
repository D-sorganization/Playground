"""I/O helpers for the mypy autofix agent.

Handles file reading/writing, mypy invocation, and output parsing.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from src.mypy_agent.types import MypyError


def run_mypy(config_file: str | None = None, targets: list[str] | None = None) -> str:
    """Run mypy and return raw combined stdout/stderr output.

    Args:
        config_file: Optional path to a mypy config file.
        targets: List of files/directories to check. Defaults to src/ and tests/.

    Returns:
        Raw mypy output string.
    """
    if not targets:
        targets = []
        if Path("src").exists():
            targets.append("src")
        if Path("tests").exists():
            targets.append("tests")
        if not targets:
            targets = ["."]

    cmd = ["mypy"] + targets + ["--no-error-summary"]
    if config_file:
        cmd.extend(["--config-file", config_file])
    cmd.append("--show-error-codes")
    cmd.extend(["--ignore-missing-imports", "--non-interactive"])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return result.stdout + result.stderr


def parse_mypy_output(output: str) -> list[MypyError]:
    """Parse mypy output text into a list of structured MypyError objects.

    Args:
        output: Raw mypy output string.

    Returns:
        List of MypyError instances (errors only, notes excluded).
    """
    errors = []
    pattern = re.compile(
        r"^(.+?):(\d+):(\d+):\s+(error|note):\s+(.+?)(?:\s+\[([^\]]+)\])?\s*$"
    )
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if match:
            file_path, line_no, col, severity, message, code = match.groups()
            if severity == "error" and code:
                errors.append(
                    MypyError(
                        file=file_path,
                        line=int(line_no),
                        column=int(col),
                        severity=severity,
                        message=message,
                        code=code or "unknown",
                    )
                )
    return errors


def read_file_lines(filepath: str) -> list[str]:
    """Read a source file and return its lines (preserving newlines).

    Args:
        filepath: Path to the file.

    Returns:
        List of lines with newline characters preserved.
    """
    path = Path(filepath)
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def write_file_lines(filepath: str, lines: list[str]) -> None:
    """Write lines back to a file, replacing its current contents.

    Args:
        filepath: Path to the file.
        lines: Lines to write (newline characters must be present).
    """
    Path(filepath).write_text("".join(lines), encoding="utf-8")


def is_safe_path(filepath: str) -> bool:
    """Return True if the file is safe to modify by the agent.

    Only src/ and tests/ Python files are considered safe.

    Args:
        filepath: File path to check.

    Returns:
        True if the file may be modified.
    """
    path = Path(filepath)
    parts = path.parts
    if not any(p in ("src", "tests") for p in parts):
        return False
    if any(p.startswith(".") or p == "__pycache__" or p == "vendor" for p in parts):
        return False
    return path.suffix == ".py"
