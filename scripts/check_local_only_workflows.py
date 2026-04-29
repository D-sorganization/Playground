# Copyright (c) 2026 D-Sorganization
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""Fail when a PR adds GitHub Actions hosted-runner routing."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

WORKFLOW_DIR = Path(".github") / "workflows"
BANNED = (
    "ubuntu-latest",
    "windows-latest",
    "macos-latest",
    "force_cloud",
    "mode=cloud",
    "Routing to GitHub-hosted",
    "using GitHub-hosted",
    "runner=ubuntu-latest",
    "runner=windows-latest",
    "runner=macos-latest",
)


def changed_workflow_lines() -> list[tuple[str, int, str]]:
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")
    if base_ref:
        subprocess.run(
            ["git", "fetch", "--depth=1", "origin", base_ref],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    base = f"origin/{base_ref}" if base_ref else "origin/main"
    diff = subprocess.run(
        [
            "git",
            "diff",
            "--unified=0",
            "--no-ext-diff",
            f"{base}...HEAD",
            "--",
            str(WORKFLOW_DIR),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if diff.returncode != 0:
        return []

    changed: list[tuple[str, int, str]] = []
    current_path = ""
    new_line = 0
    for line in diff.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_path = line.removeprefix("+++ b/")
            continue
        if line.startswith("@@"):
            marker = line.split("+", 1)[1].split(" ", 1)[0]
            start = marker.split(",", 1)[0]
            new_line = int(start)
            continue
        if line.startswith("+") and not line.startswith("+++"):
            changed.append((current_path, new_line, line[1:]))
            new_line += 1
        elif not line.startswith("-"):
            new_line += 1
    return changed


def main() -> int:
    failures: list[str] = []
    for path, line_number, line in changed_workflow_lines():
        for token in BANNED:
            if token in line:
                failures.append(
                    f"{path}:{line_number}: added banned hosted-runner token {token!r}"
                )

    if failures:
        print("New GitHub-hosted runner routing is forbidden.")
        print("Use local self-hosted runners only.")
        print("\n".join(failures))
        return 1

    print("No new GitHub-hosted runner routing was added.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
