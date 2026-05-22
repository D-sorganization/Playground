"""Cross-platform pre-push wrapper for Semgrep.

Semgrep's Python package is not installable on native Windows. Keep the hook
usable on Windows while preserving the scanner on platforms where it runs.
"""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    if os.name == "nt":
        print("semgrep: skipped on native Windows; run in Linux/WSL CI")
        return 0
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "semgrep",
            "--config",
            "auto",
            "--error",
            "--quiet",
            *sys.argv[1:],
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
