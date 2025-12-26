import json
import logging
import os
import time
from pathlib import Path

from .types import TitleResult

logger = logging.getLogger(__name__)


class GeminiTitleLLM:
    def __init__(self, api_key: str | None = None):
        try:
            import google.generativeai as genai

            self.genai = genai
            key = api_key or os.environ.get("GEMINI_API_KEY")
            if not key:
                logger.warning("GEMINI_API_KEY not found in environment")
            else:
                genai.configure(api_key=key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        except ImportError:
            self.genai = None
            logger.error("google-generativeai package not installed")

    def extract_title(self, pdf_path: Path) -> TitleResult:
        if not self.genai:
            return TitleResult(None, 0.0, "llm", "google-generativeai not installed")

        uploaded_file = None
        try:
            logger.info(f"Uploading {pdf_path.name} to Gemini...")
            uploaded_file = self.genai.upload_file(
                path=str(pdf_path), mime_type="application/pdf"
            )

            # Wait for processing state if needed (usually fast for small PDFs)
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(1)
                uploaded_file = self.genai.get_file(uploaded_file.name)

            if uploaded_file.state.name == "FAILED":
                return TitleResult(None, 0.0, "llm", "Gemini file processing failed")

            prompt = """
            Extract the main title of this document.
            Ignore headers/footers/generic text like "Draft" unless part of the title.
            Return ONLY a JSON object with this structure:
            {
                "title": "The exact title string",
                "confidence": 0.0 to 1.0,
                "reason": "Why you chose this title"
            }
            """

            response = self.model.generate_content(
                [uploaded_file, prompt],
                generation_config={"response_mime_type": "application/json"},
            )

            text = response.text
            try:
                data = json.loads(text)
                title = data.get("title")
                conf = float(data.get("confidence", 0.0))
                details = data.get("reason", "")

                if title:
                    return TitleResult(title, conf, "llm", f"Gemini: {details}")
                else:
                    return TitleResult(
                        None, 0.0, "llm", f"Gemini found no title: {details}"
                    )

            except json.JSONDecodeError:
                return TitleResult(
                    None,
                    0.0,
                    "llm",
                    f"Gemini response parsing failed: {text[:100]}",
                )

        except Exception as e:
            logger.error(f"Gemini LLM error: {e}")
            return TitleResult(None, 0.0, "llm", f"Gemini error: {e}")
        finally:
            if uploaded_file:
                try:
                    self.genai.delete_file(uploaded_file.name)
                except Exception:
                    pass
