"""The legacy .agent/ tree stays removed.

agy and Codex read .agents/; the .agent/ skill and workflow copies were stale
duplicates of .claude/skills (Repository_Management#2567).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_tracked_files_under_legacy_agent_dir() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--", ".agent/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert tracked == []
