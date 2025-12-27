# Advanced PDF Renamer with AI

A robust tool to rename PDF files using a layered approach: local metadata, layout heuristics, and AI fallback (Gemini).

## Architecture

- **Layer 0**: Deterministic metadata extraction (fast, free).
- **Layer 1**: Layout-aware heuristic extraction using PyMuPDF (fast, robust).
- **Layer 2**: AI Fallback using Gemini (high accuracy, native PDF support).

## Features

- **Robust Extraction**: Tries multiple methods to find the best title.
- **Smart Caching**: Specific results are stored in SQLite by file hash to avoid re-processing.
- **AI Integration**: Seamlessly offloads difficult PDFs to Gemini.
- **Result Styles**: Standard, snake_case, or kebab_case.
- **Concurrency**: Process multiple files in parallel.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set your Gemini API key (optional, for Layer 2):
   ```bash
   export GEMINI_API_KEY="your_key_here"
   # or on Windows PowerShell:
   $env:GEMINI_API_KEY="your_key_here"
   ```

## Usage

```bash
# Dry run (preview only)
python -m src.pdf_renamer.main /path/to/pdfs --dry-run

# Run with Gemini fallback
python -m src.pdf_renamer.main /path/to/pdfs --provider gemini

# Change naming style and use custom DB
python -m src.pdf_renamer.main /path/to/pdfs --style snake_case --db my_cache.sqlite
```
