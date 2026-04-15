"""Compatibility wrapper for the shared fleet mypy autofix command.

Historically, this file contained a 700+ LOC monolithic mypy autofix agent
that was duplicated across AffineDrift, Games, MLProjects, and Playground.
The implementation has been decomposed into ``src/mypy_agent/`` (local) and
is also available as a shared fleet tool installable as ``mypy-autofix``.

This wrapper exists so the pre-existing GitHub autofix workflow
(``.github/workflows/Jules-PR-AutoFix.yml``), which invokes
``python scripts/mypy_autofix_agent.py``, continues to work:

* If ``mypy-autofix`` is on the PATH, arguments are forwarded to it.
* If not, the step is a no-op (exit 0) so CI does not regress when the
  shared command is not yet installed in the workflow's environment.

See: Playground#247, MLProjects#302 (pattern source), AffineDrift#2364.
"""

from __future__ import annotations

import shutil
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    """Run the shared ``mypy-autofix`` command when it is installed."""
    args = sys.argv[1:] if argv is None else argv
    command = shutil.which("mypy-autofix")
    if command is None:
        print("mypy-autofix is not installed; skipping mypy autofix step.")
        return 0
    return subprocess.call([command, *args])


# Backwards-compatibility alias: older callers and tests referenced ``run_agent``.
run_agent = main


if __name__ == "__main__":
    sys.exit(main())
