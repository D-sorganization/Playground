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

## Hook bypass policy

**Never use `git commit --no-verify` or `git push --no-verify` unless the hook itself is broken** (tooling not installed, hook script crashes). It is _not_ an acceptable workaround for a hook that flags real issues.

### When a hook fails on something you didn't touch

The hook is scoped to _your diff_. If `fleet-fast-guardrails` or any other guardrail reports a violation in a file you didn't change, that's a regression — file an issue against `Repository_Management`. Bypassing locally doesn't help: the same checks run in CI's `quality-gate` and will block the PR.

### When the hook is legitimately broken

Open an issue in `Repository_Management`. If you must bypass once to land an urgent fix, include the hook error in the commit body and link the tracking issue. **Do not normalize `--no-verify` as a workaround.**

### Enforcement

Branch protection requires the CI `quality-gate` check on every PR. That check runs the same lint, format, type, and security gates as the hooks. `--no-verify` only delays feedback — it cannot land code that would have failed the hook.

For the canonical hook contract, see [`Repository_Management/docs/FLEET_HOOK_STANDARDS.md`](https://github.com/D-sorganization/Repository_Management/blob/main/docs/FLEET_HOOK_STANDARDS.md).
