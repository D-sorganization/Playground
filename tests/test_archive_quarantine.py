from __future__ import annotations

import tomllib
from pathlib import Path


def test_archive_is_excluded_from_pytest_collection() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pyproject_text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    pyproject = tomllib.loads(pyproject_text)
    pytest_options = pyproject["tool"]["pytest"]["ini_options"]

    assert "archive" in pytest_options["norecursedirs"]


def test_archive_is_excluded_from_ruff_checks() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pyproject_text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    pyproject = tomllib.loads(pyproject_text)
    ruff_config = pyproject["tool"]["ruff"]

    assert "archive" in ruff_config["exclude"]


