"""Shared dataclasses and lookup tables for the Mypy Autofix Agent."""

from __future__ import annotations

from dataclasses import dataclass, field

# Common third-party modules that trigger import-untyped
KNOWN_UNTYPED_MODULES = {
    "mujoco",
    "dm_control",
    "pinocchio",
    "pin",
    "drake",
    "pydrake",
    "opensim",
    "myosuite",
    "gymnasium",
    "gym",
    "meshcat",
    "trimesh",
    "pybullet",
    "cv2",
    "mediapipe",
    "onnxruntime",
    "sklearn",
    "scipy",
    "PIL",
    "yaml",
    "toml",
    "rich",
    "click",
    "uvicorn",
    "starlette",
    "websockets",
    "serial",
    "usb",
    "hid",
    "pygame",
    "OpenGL",
    "moderngl",
}

# Common type imports that resolve name-defined errors
COMMON_TYPE_IMPORTS = {
    "Callable": "from collections.abc import Callable",
    "Iterator": "from collections.abc import Iterator",
    "Generator": "from collections.abc import Generator",
    "Sequence": "from collections.abc import Sequence",
    "Mapping": "from collections.abc import Mapping",
    "Iterable": "from collections.abc import Iterable",
    "Optional": "from typing import Optional",
    "Union": "from typing import Union",
    "Any": "from typing import Any",
    "ClassVar": "from typing import ClassVar",
    "TypeVar": "from typing import TypeVar",
    "Protocol": "from typing import Protocol",
    "TypeAlias": "from typing import TypeAlias",
    "Final": "from typing import Final",
    "Literal": "from typing import Literal",
    "overload": "from typing import overload",
    "cast": "from typing import cast",
    "TYPE_CHECKING": "from typing import TYPE_CHECKING",
    "Self": "from typing import Self",
    "TypedDict": "from typing import TypedDict",
    "NamedTuple": "from typing import NamedTuple",
    "Path": "from pathlib import Path",
    "datetime": "from datetime import datetime",
    "timedelta": "from datetime import timedelta",
    "Enum": "from enum import Enum",
    "dataclass": "from dataclasses import dataclass",
    "abstractmethod": "from abc import abstractmethod",
    "ABC": "from abc import ABC",
}

# Error codes that are safe to suppress as a last resort
SUPPRESSIBLE_CODES = {
    "assignment",
    "arg-type",
    "return-value",
    "attr-defined",
    "override",
    "misc",
    "call-overload",
    "type-arg",
    "index",
    "operator",
    "no-untyped-call",
    "redundant-cast",
    "var-annotated",
}


@dataclass
class MypyError:
    """Parsed mypy error."""

    file: str
    line: int
    column: int
    severity: str  # "error" or "note"
    message: str
    code: str  # e.g., "union-attr", "valid-type", "import-untyped"


@dataclass
class Fix:
    """A fix to apply."""

    file: str
    line: int
    description: str
    strategy: str  # "real-fix" or "suppression"
    original_code: str = ""


@dataclass
class AgentReport:
    """Report of all actions taken."""

    total_errors: int = 0
    errors_fixed: int = 0
    real_fixes: int = 0
    suppressions: int = 0
    files_modified: list[str] = field(default_factory=list)
    fixes_applied: list[str] = field(default_factory=list)
    skipped_reasons: list[str] = field(default_factory=list)
