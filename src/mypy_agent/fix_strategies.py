"""Fix strategy functions for the mypy autofix agent.

Each function attempts to apply a targeted fix to a specific mypy error.
Returns a Fix on success, None if the strategy does not apply.
"""

from __future__ import annotations

import re

from src.mypy_agent.types import (
    COMMON_TYPE_IMPORTS,
    SUPPRESSIBLE_CODES,
    Fix,
    MypyError,
)


def has_type_ignore(line: str, code: str | None = None) -> bool:
    """Return True if *line* already carries a matching type: ignore comment.

    Args:
        line: Source code line text.
        code: Specific error code to check for, or None to match any.
    """
    if "# type: ignore" not in line:
        return False
    if code and f"[{code}]" in line:
        return True
    if code is None:
        return True
    return "# type: ignore\n" in line or line.rstrip().endswith("# type: ignore")


def add_type_ignore(line: str, code: str) -> str:
    """Append a targeted # type: ignore[code] comment to *line*.

    Args:
        line: Original source code line.
        code: Mypy error code to suppress.

    Returns:
        Modified line with the suppression comment appended.
    """
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
    """Return the leading whitespace of *line*."""
    return line[: len(line) - len(line.lstrip())]


def _ensure_import(lines: list[str], import_statement: str) -> bool:
    """Insert *import_statement* into *lines* if not already present.

    Args:
        lines: Source file lines (mutated in-place).
        import_statement: Complete import statement string.

    Returns:
        True if the import was added, False if it was already present.
    """
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

    insert_at = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                insert_at = i + 1
                break
            for j in range(i + 1, len(lines)):
                if '"""' in lines[j] or "'''" in lines[j]:
                    insert_at = j + 1
                    break
            break
        elif stripped and not stripped.startswith("#"):
            insert_at = i
            break
    lines.insert(insert_at, import_statement + "\n")
    return True


def fix_callable_as_type(lines: list[str], error: MypyError) -> Fix | None:
    """Fix 'callable is not valid as a type' by replacing with Callable[..., Any].

    This is a real fix (not a suppression).

    Args:
        lines: Source file lines (mutated on success).
        error: MypyError to fix.

    Returns:
        Fix instance on success, None if this strategy does not apply.
    """
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
    """Fix union-attr by inserting an isinstance narrowing assertion.

    This is a real fix.

    Args:
        lines: Source file lines (mutated on success).
        error: MypyError to fix.

    Returns:
        Fix instance on success, None if this strategy does not apply.
    """
    if error.code != "union-attr":
        return None

    match = re.search(
        r'Item "(\w+)" of "([^"]+)" has no attribute "(\w+)"',
        error.message,
    )
    if not match:
        return None

    bad_type, union_type, attr = match.groups()
    types_in_union = [t.strip() for t in union_type.split("|")]
    good_types = [t for t in types_in_union if t != bad_type and t != "None"]
    if not good_types:
        return None

    idx = error.line - 1
    if idx >= len(lines):
        return None

    line = lines[idx]
    indent = get_line_indent(line)
    var_match = re.search(rf"(\w+)\.{re.escape(attr)}", line)
    if not var_match:
        return None

    var_name = var_match.group(1)
    target_type = good_types[0]

    for check_idx in range(max(0, idx - 3), idx):
        if f"isinstance({var_name}" in lines[check_idx]:
            return None  # Already narrowed

    lines.insert(idx, f"{indent}assert isinstance({var_name}, {target_type})\n")
    return Fix(
        file=error.file,
        line=error.line,
        description=(
            f"Add isinstance({var_name}, {target_type}) narrowing for union-attr"
        ),
        strategy="real-fix",
        original_code=line.strip(),
    )


def fix_name_not_defined(lines: list[str], error: MypyError) -> Fix | None:
    """Fix name-defined errors by adding missing type imports.

    This is a real fix when the name is a known type alias.

    Args:
        lines: Source file lines (mutated on success).
        error: MypyError to fix.

    Returns:
        Fix instance on success, None if this strategy does not apply.
    """
    if error.code != "name-defined":
        return None

    match = re.search(r'Name "(\w+)" is not defined', error.message)
    if not match:
        return None

    name = match.group(1)
    if name in COMMON_TYPE_IMPORTS:
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
    """Suppress import-untyped and import-not-found with targeted type: ignore.

    These are suppressions, but acceptable for third-party packages.

    Args:
        lines: Source file lines (mutated on success).
        error: MypyError to fix.

    Returns:
        Fix instance on success, None if this strategy does not apply.
    """
    if error.code not in ("import-untyped", "import-not-found"):
        return None

    idx = error.line - 1
    if idx >= len(lines):
        return None

    line = lines[idx]
    if has_type_ignore(line, error.code):
        return None

    lines[idx] = add_type_ignore(line, error.code)
    return Fix(
        file=error.file,
        line=error.line,
        description=f"Suppress {error.code} for third-party import",
        strategy="suppression",
        original_code=line.strip(),
    )


def fix_generic_suppression(lines: list[str], error: MypyError) -> Fix | None:
    """Last-resort targeted # type: ignore[code] suppression.

    Only used for well-understood error codes. Uses specific codes rather
    than blanket ignores.

    Args:
        lines: Source file lines (mutated on success).
        error: MypyError to fix.

    Returns:
        Fix instance on success, None if this strategy does not apply.
    """
    if error.code not in SUPPRESSIBLE_CODES:
        return None

    idx = error.line - 1
    if idx >= len(lines):
        return None

    line = lines[idx]
    if has_type_ignore(line, error.code):
        return None

    lines[idx] = add_type_ignore(line, error.code)
    return Fix(
        file=error.file,
        line=error.line,
        description=f"Suppress mypy [{error.code}]: {error.message[:80]}",
        strategy="suppression",
        original_code=line.strip(),
    )


# Priority-ordered list of all fix strategies (real fixes first)
ALL_FIX_STRATEGIES = [
    fix_callable_as_type,
    fix_union_attr,
    fix_name_not_defined,
    fix_import_errors,
    fix_generic_suppression,
]
