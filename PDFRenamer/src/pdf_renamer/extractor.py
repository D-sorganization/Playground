import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_metadata(file_path: Path) -> tuple[str | None, str | None]:
    """
    Extracts Author and Title from PDF metadata.
    Returns (Author, Title) or (None, None) if extraction fails.
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            metadata = pdf.metadata
            if not metadata:
                return None, None

            # Metadata keys can be Title/Author or title/author
            # We try standard keys
            title = metadata.get("Title") or metadata.get("title")
            author = metadata.get("Author") or metadata.get("author")

            # Clean up empty strings
            if title and not title.strip():
                title = None
            if author and not author.strip():
                author = None

            return author, title
    except Exception as e:
        logger.warning(f"Failed to extract metadata from {file_path}: {e}")
        return None, None
