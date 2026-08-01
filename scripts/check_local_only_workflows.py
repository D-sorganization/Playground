#!/usr/bin/env python3
"""Check that workflow runner routing matches repository visibility.

This started life as a flat ban on hosted-runner tokens, which was right while
the repo was private: hosted runners bill against the org quota, so every job
belonged on the self-hosted fleet.

Going public reverses it. GitHub-hosted standard runners are free and unmetered
on public repositories, so the cost argument disappears; and the safety argument
inverts outright, because GitHub advises against pairing self-hosted runners
with public repos -- a fork pull request can execute attacker-controlled code on
a persistent machine we own.

So the rule is now conditional rather than absolute:

    private / internal -- hosted routing is an error, as before.
    public             -- hosted routing is expected; fleet-pinned jobs are
                          reported as warnings instead.

Visibility is read from REPO_VISIBILITY, which the workflow supplies from
`github.event.repository.visibility`. When it is unreadable we enforce, because
failing closed costs a re-run while failing open costs a billed month.
"""

from __future__ import annotations

import os
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
FLEET_TOKENS = ("d-sorg-fleet", "self-hosted")

# Files allowlisted from the hosted-runner scan. The tripwire workflow
# intentionally runs on a hosted runner, since it is the canary that has to stay
# operable when the fleet itself is down.
LEGACY_HOSTED_RUNNER_ALLOWLIST = {
    ".github/workflows/local-only-runner-guard.yml",
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def main() -> int:
    if not WORKFLOW_DIR.exists():
        return 0

    visibility = (os.environ.get("REPO_VISIBILITY") or "").strip().lower()
    is_public = visibility == "public"
    print(f"Repository visibility: {visibility or '<unknown>'}")
    print(
        "Hosted runners are FREE here; fleet-pinned jobs are reported as warnings."
        if is_public
        else "Hosted runners are METERED here; every job must route to the fleet."
    )

    hosted_hits: list[str] = []
    fleet_hits: list[str] = []

    for path in sorted(WORKFLOW_DIR.rglob("*")):
        if path.suffix not in {".yml", ".yaml"}:
            continue
        if path.as_posix() in LEGACY_HOSTED_RUNNER_ALLOWLIST:
            continue
        for line_number, line in enumerate(read_text(path).splitlines(), start=1):
            for token in BANNED:
                if token in line:
                    hosted_hits.append(
                        f"{path}:{line_number}: hosted-runner token {token!r}"
                    )
            if "runs-on" in line:
                for token in FLEET_TOKENS:
                    if token in line:
                        fleet_hits.append(
                            f"{path}:{line_number}: fleet-pinned {token!r}"
                        )

    if is_public:
        for hit in fleet_hits:
            print(
                f"::warning::{hit} on a public repo; "
                "a fork PR could run on fleet hardware"
            )
        print(
            f"Public repo: hosted runners permitted. "
            f"{len(fleet_hits)} line(s) can still reach the self-hosted fleet."
        )
        return 0

    if hosted_hits:
        print(
            "GitHub-hosted runner routing is forbidden. "
            "This repository is not public, so hosted runners are billed against "
            "the org quota. Use local self-hosted runners only."
        )
        print("\n".join(hosted_hits))
        return 1

    print("Workflow runner routing is local-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
