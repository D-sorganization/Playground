from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from .types import TitleResult
from .utils import clean_title, looks_like_title

logger = logging.getLogger(__name__)


MIN_TITLE_FONT_SIZE = 10.0
TOP_PAGE_FRACTION = 0.35


# ---------- Layer 0: metadata ----------
def title_from_metadata(pdf_path: Path) -> TitleResult:
    try:
        from pypdf import PdfReader  # type: ignore

        r = PdfReader(str(pdf_path))
        md = r.metadata
        if md and md.title:
            t = clean_title(str(md.title))
            if looks_like_title(t):
                return TitleResult(t, 0.95, "metadata", "pypdf metadata /Title")
        return TitleResult(None, 0.0, "metadata", "no usable metadata title")
    except Exception as e:
        logger.debug(f"Metadata extraction failed: {e}")
        return TitleResult(None, 0.0, "metadata", f"metadata error: {e}")


# ---------- Layer 1: first-page heuristic (layout-aware) ----------
def title_from_first_page(pdf_path: Path) -> TitleResult:
    try:
        import fitz  # type: ignore

        doc = fitz.open(str(pdf_path))
        if doc.page_count == 0:
            return TitleResult(None, 0.0, "heuristic", "empty PDF")
        page = doc.load_page(0)
        blocks = page.get_text("dict")["blocks"]

        # Collect spans with font sizes + positions
        spans = []
        for b in blocks:
            for line in b.get("lines", []):
                for sp in line.get("spans", []):
                    text = clean_title(sp.get("text", ""))
                    if text:
                        spans.append(
                            (sp.get("size", 0.0), sp.get("bbox", [0, 0, 0, 0]), text)
                        )

        if not spans:
            return TitleResult(None, 0.0, "heuristic", "no text spans on page 1")

        # Sort by size desc, then by y position (top of page)
        # bbox = [x0, y0, x1, y1], smaller y0 is higher on page
        spans.sort(key=lambda x: (-x[0], x[1][1]))

        # Take top candidates, join adjacent large spans
        candidates = []
        for size, bbox, text in spans[:40]:
            if size < MIN_TITLE_FONT_SIZE:  # crude floor; tune per corpus
                continue
            if looks_like_title(text):
                candidates.append((size, bbox[1], text))

        if not candidates:
            return TitleResult(None, 0.0, "heuristic", "no title-like candidates")

        # Heuristic: take the largest-font line(s) near the top
        best_size = max(c[0] for c in candidates)
        top = [c for c in candidates if c[0] >= best_size - 0.5]
        # Keep ones near top third of page
        top = [c for c in top if c[1] < page.rect.height * TOP_PAGE_FRACTION]
        if not top:
            top = candidates[:5]

        guess = clean_title(" ".join(t[2] for t in top[:3]))
        if not looks_like_title(guess):
            return TitleResult(None, 0.2, "heuristic", f"weak guess: {guess!r}")

        # Confidence: higher if very large font and near top
        conf = 0.75 + min(0.2, (best_size - 12) / 40.0)
        return TitleResult(
            guess, min(conf, 0.9), "heuristic", "largest-font spans near top"
        )
    except ImportError:
        logger.warning("PyMuPDF (fitz) not installed. Skipping heuristic layer.")
        return TitleResult(None, 0.0, "heuristic", "pymupdf not installed")
    except Exception as e:
        logger.debug(f"Heuristic extraction failed: {e}")
        return TitleResult(None, 0.0, "heuristic", f"heuristic error: {e}")


# ---------- Layer 2: LLM fallback ----------
class TitleLLM(Protocol):
    def extract_title(self, pdf_path: Path) -> TitleResult: ...
