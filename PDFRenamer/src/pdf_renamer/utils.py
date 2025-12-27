import hashlib
import re
from pathlib import Path

MAX_TITLE_LENGTH = 300


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculates the SHA256 hash of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def clean_title(s: str) -> str:
    """Cleans up a title string by removing extra whitespace and special characters."""
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^[\W_]+|[\W_]+$", "", s)
    return s[:MAX_TITLE_LENGTH]


def looks_like_title(s: str) -> bool:
    """Heuristic check to see if a string looks like a valid title."""
    if not s or len(s) < 6:
        return False
    bad = ["arxiv", "doi:", "http", "www.", "copyright", "all rights reserved"]
    if any(b in s.lower() for b in bad):
        return False
    # avoid "Abstract" etc.
    if s.strip().lower() in {"abstract", "introduction"}:
        return False
    return True


def sanitize_filename(s: str) -> str:
    """Removes characters invalid in filenames."""
    s = re.sub(r'[\\/*?:"<>|]', "", s)
    return s.strip()


def to_snake_case(s: str) -> str:
    """Converts string to snake_case."""
    s = sanitize_filename(s).lower()
    return re.sub(r"\s+", "_", s)


def to_kebab_case(s: str) -> str:
    """Converts string to kebab-case."""
    s = sanitize_filename(s).lower()
    return re.sub(r"\s+", "-", s)


def to_title_case(s: str) -> str:
    """Converts string to Title Case."""
    return s.title()


def get_last_name(author: str) -> str:
    """Extracts the last name from an author string."""
    if not author:
        return ""
    # Simple heuristic: split by space and take the last part
    parts = author.split()
    if not parts:
        return ""
    return parts[-1]
