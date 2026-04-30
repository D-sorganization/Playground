# Claude Agent Instructions

## Branch Policy

All work on `main` branch. PRs target `main`.

## Quick Reference

### Build & Test Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
ruff check .
ruff format .
mypy .

# Type checking only
mypy src/ tests/
```

### Project Structure

```
workout_tracker/           # Main package
├── __init__.py
├── __main__.py           # Entry point: python -m workout_tracker
├── app.py                # Flask/FastAPI web application
├── db.py                 # Database models & connection
├── models.py             # Pydantic/dataclass models
├── parser.py             # Workout log parsing
├── stats.py              # Statistics calculations
├── autocomplete.py       # Exercise name autocomplete
├── schema.sql            # Database schema
├── static/               # CSS, JS, manifest
└── templates/            # HTML templates

tests/                   # Test suite
docs/                    # Documentation & assessments
assessments/             # A-O health assessment reports
```

### Agent Guidelines

- **TDD Required**: RED → GREEN → REFACTOR (see AGENTS.md §4)
- **No print()**: Use `logging` module exclusively
- **Type hints**: Required on all public functions
- **Max 400 lines per file**: Split if approaching limit
- **DRY**: Extract shared logic after 5+ line duplication
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`

### Technology Stack

- **Backend**: Python 3.10+, Flask/FastAPI
- **Frontend**: Vanilla JS, CSS, HTML templates
- **Database**: SQLite (production uses PostgreSQL via env config)
- **Testing**: pytest, hypothesis (optional)
- **Linting**: ruff, black, mypy

### Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
DATABASE_URL=sqlite:///workout_tracker.db
SECRET_KEY=your-secret-key
LOG_LEVEL=INFO
```

### CI/CD

- GitHub Actions: `.github/workflows/ci-standard.yml`
- Required checks: ruff, mypy, pytest
- PRs must pass all checks before merge

### Documentation Standards

- Update `README.md` for user-facing changes
- Update `CHANGELOG.md` under `## [Unreleased]`
- Update `SPEC.md` for architectural changes
- Add docstrings (Google style) for new modules/functions

### Security

- NEVER commit secrets (use `.env`)
- Validate all user inputs
- Use parameterized queries (no SQL injection)
- Sanitize HTML if rendering user content

### Emergency

If sensitive data is committed:

1. Stop immediately
2. Use BFG Repo-Cleaner or `git filter-branch`
3. Rotate exposed credentials
4. Force push after team coordination
