"""Fix strategy functions for the Mypy Autofix Agent.

Each strategy receives the list of file lines and a MypyError and returns
a Fix if applicable, or None if the strategy cannot handle the error.

Strategies are tried in priority order (real fixes before suppressions).
"""

from __future__ import annotations

import re

from scripts.mypy_agent_types import (
    COMMON_TYPE_IMPORTS,
    SUPPRESSIBLE_CODES,
    Fix,
    MypyError,
)


def has_type_ignore(line: str, code: str | None = None) -> bool:
    """Check if a line already has a type: ignore comment."""
    if "# type: ignore" in line:
        if code and f"[{code}]" in line:
            return True
        if code is None:
            return True
        if "# type: ignore\n" in line or line.rstrip().endswith("# type: ignore"):
            return True
    return False


def add_type_ignore(line: str, code: str) -> str:
    """Add # type: ignore[code] to a line."""
    stripped = line.rstrip("\n\r")
    if "# type: ignore" in stripped:
        if re.search(r"# type: ignore\[([^\]]+)\]", stripped):
            return (
                re.sub(
                    r"# type: ignore\[([^\]]+)\]",
                    rf"# type: ignore[\1, {code}]",
                    stripped,
                )
                + "\n"
            )
        return stripped + "\n"
    return stripped + f"  # type: ignore[{code}]\n"


def get_line_indent(line: str) -> str:
    """Get the leading whitespace of a line."""
    return line[: len(line) - len(line.lstrip())]


def _ensure_import(lines: list[str], import_statement: str) -> bool:
    """Add an import statement if not already present. Returns True if added."""
    for line in lines:
        if import_statement in line:
            return False
    last_import_idx = -1
    in_docstring = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if in_docstring:
                in_docstring = False
                continue
            if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                in_docstring = True
                continue
        if in_docstring:
            continue
        if stripped.startswith(("import ", "from ")):
            last_import_idx = i
        elif stripped and not stripped.startswith("#") and last_import_idx >= 0:
            break
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, import_statement + "\n")
        return True
    insert_at = _find_docstring_end(lines)
    lines.insert(insert_at, import_statement + "\n")
    return True


def _find_docstring_end(lines: list[str]) -> int:
    """Return line index after module docstring (or 0 if none)."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                return i + 1
            for j in range(i + 1, len(lines)):
                if '"""' in lines[j] or "'''" in lines[j]:
                    return j + 1
            return i + 1
        if stripped and not stripped.startswith("#"):
            return i
    return 0


def fix_callable_as_type(lines: list[str], error: MypyError) -> Fix | None:
    """Replace 'callable' with 'Callable[..., Any]' (real fix)."""
    if error.code != "valid-type":
        return None
    if '"callable" is not valid as a type' not in error.message.lower():
        return None
    idx = error.line - 1
    if idx >= len(lines):
        return None
    line = lines[idx]
    if ": callable" not in line.lower():
        return None
    original = line
    line = re.sub(r":\s*callable\b", ": Callable[..., Any]", line, flags=re.IGNORECASE)
    lines[idx] = line
    _ensure_import(lines, "from collections.abc import Callable")
    _ensure_import(lines, "from typing import Any")
    return Fix(
        file=error.file,
        line=error.line,
        description="Replace 'callable' with 'Callable[..., Any]'",
        strategy="real-fix",
        original_code=original.strip(),
    )


def fix_union_attr(lines: list[str], error: MypyError) -> Fix | None:
    """Add isinstance narrowing for union-attr errors (real fix)."""
    if error.code != "union-attr":
        return None
    match = re.search(
        r'Item "(\w+)" of "([^"]+)" has no attribute "(\w+)"', error.message
    )
    if not match:
        return None
    bad_type, union_type, attr = match.groups()
    excluded = (bad_type, "None")
    good_types = [t.strip() for t in union_type.split("|") if t.strip() not in excluded]
    if not good_types:
        return None
    idx = error.line - 1
    if idx >= len(lines):
        return None
    line = lines[idx]
    var_match = re.search(rf"(\w+)\.{re.escape(attr)}", line)
    if not var_match:
        return None
    var_name = var_match.group(1)
    if any(f"isinstance({var_name}" in lines[j] for j in range(max(0, idx - 3), idx)):
        return None
    indent = get_line_indent(line)
    lines.insert(idx, f"{indent}assert isinstance({var_name}, {good_types[0]})\n")
    return Fix(
        file=error.file,
        line=error.line,
        description=f"Add isinstance({var_name}, {good_types[0]}) narrowing",
        strategy="real-fix",
        original_code=line.strip(),
    )


def fix_name_not_defined(lines: list[str], error: MypyError) -> Fix | None:
    """Add missing imports for known type names (real fix)."""
    if error.code != "name-defined":
        return None
    match = re.search(r'Name "(\w+)" is not defined', error.message)
    if not match:
        return None
    name = match.group(1)
    if name not in COMMON_TYPE_IMPORTS:
        return None
    import_line = COMMON_TYPE_IMPORTS[name]
    if _ensure_import(lines, import_line):
        return Fix(
            file=error.file,
            line=error.line,
            description=f"Add missing import: {import_line}",
            strategy="real-fix",
        )
    return None


def fix_import_errors(lines: list[str], error: MypyError) -> Fix | None:
    """Suppress import-untyped and import-not-found with targeted ignore."""
    if error.code not in ("import-untyped", "import-not-found"):
        return None
    idx = error.line - 1
    if idx >= len(lines) or has_type_ignore(lines[idx], error.code):
        return None
    lines[idx] = add_type_ignore(lines[idx], error.code)
    return Fix(
        file=error.file,
        line=error.line,
        description=f"Suppress {error.code} for third-party import",
        strategy="suppression",
        original_code=lines[idx - 1].strip() if idx > 0 else "",
    )


def fix_generic_suppression(lines: list[str], error: MypyError) -> Fix | None:
    """Last resort: add targeted # type: ignore[code] suppression."""
    if error.code not in SUPPRESSIBLE_CODES:
        return None
    idx = error.line - 1
    if idx >= len(lines) or has_type_ignore(lines[idx], error.code):
        return None
    lines[idx] = add_type_ignore(lines[idx], error.code)
    return Fix(
        file=error.file,
        line=error.line,
        description=f"Suppress mypy [{error.code}]: {error.message[:80]}",
        strategy="suppression",
        original_code=lines[idx - 1].strip() if idx > 0 else "",
    )


ALL_STRATEGIES = [
    fix_callable_as_type,
    fix_union_attr,
    fix_name_not_defined,
    fix_import_errors,
    fix_generic_suppression,
]
