import logging
from pathlib import Path

from .utils import get_last_name, sanitize_filename, to_title_case

# Import extractor later to avoid circular dependency issues if any, but ideally here.
# For now, I'll assume extractor is passed or imported.

logger = logging.getLogger(__name__)


class Renamer:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def generate_new_filename(self, author: str, title: str) -> str:
        last_name = get_last_name(author)
        clean_title = sanitize_filename(to_title_case(title))
        clean_author = sanitize_filename(last_name)

        if not clean_title:
            clean_title = "Untitled"
        if not clean_author:
            clean_author = "Unknown"

        return f"{clean_author} - {clean_title}.pdf"

    def rename_file(self, original_path: Path, new_filename: str) -> None:
        if not original_path.exists():
            logger.error(f"File not found: {original_path}")
            return

        target_path = original_path.parent / new_filename

        # Handle filename collision
        counter = 1
        stem = target_path.stem
        suffix = target_path.suffix
        while target_path.exists() and target_path != original_path:
            target_path = original_path.parent / f"{stem}_{counter}{suffix}"
            counter += 1

        if target_path == original_path:
            logger.info(f"Skipping {original_path.name} (already named correctly)")
            return

        logger.info(f"Renaming '{original_path.name}' -> '{target_path.name}'")

        if not self.dry_run:
            try:
                original_path.rename(target_path)
            except OSError as e:
                logger.error(f"Failed to rename {original_path}: {e}")
