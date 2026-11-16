"""Legacy entry points delegate policy rather than maintaining a second workflow."""

from pathlib import Path

import yaml

SKILL = (
    Path(__file__).resolve().parents[1] / ".claude/skills/issues-10-sequential/SKILL.md"
)
CANONICAL = "https://github.com/D-sorganization/Repository_Management/blob/main/skills/barb-desktop-lane/SKILL.md"


def test_legacy_entrypoint_is_a_canonical_pointer() -> None:
    text = SKILL.read_text(encoding="utf-8")
    _, header, body = text.split("---", 2)
    metadata = yaml.safe_load(header)
    assert metadata["name"] == "issues-10-sequential"
    assert metadata.get("metadata", {}).get("canonical_source") == CANONICAL
    assert metadata["metadata"]["delivery"] == "pointer-only"
    assert CANONICAL in body


def test_pointer_does_not_reintroduce_a_local_delivery_workflow() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "gh pr merge" not in text
    assert "Continue autonomously" not in text
    assert "### 1. Get Open Issues" not in text
    assert "```" not in text
