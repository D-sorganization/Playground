# Playground

A fleet-wide monorepo for independent experiments and simulation projects. Each project is self-contained with its own domain, dependencies, and maturity level. The monorepo provides shared CI infrastructure, tooling, and quality gates, but individual projects are **orthogonal** — they share no domain logic and are evaluated independently.

## Projects

| Project                      | Status           | Description                                                                                                                                                                  |
| ---------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Asteroid Jumper**          | Production-ready | A PyQt6 desktop application for navigating and jumping between asteroids with real-time physics simulation. Full DbC, TDD, and LoD compliance.                               |
| **Asteroid Field Navigator** | Stable           | RRT-based path planning through procedurally generated asteroid fields.                                                                                                      |
| **Calculator**               | Stable           | A TI-89-style calculator with a Flask web interface and SymPy-powered symbolic math.                                                                                         |
| **Solar System Model**       | Stable           | A solar system simulation and visualization tool.                                                                                                                            |
| **Project GROOT**            | Experimental     | Golf swing imitation-learning pipeline: video ingestion, pose conversion, MuJoCo simulation, RL fine-tuning, and evaluation. Active development; quality uplift in progress. |

### Monorepo Convention

This repository intentionally hosts **independent experiments** at different maturity levels:

- Projects do not share domain code or business logic.
- Each project has its own `src/<project>/` subtree.
- Quality assessments should be interpreted per-project, not for the repository as a whole.
- Experimental projects (e.g., Project GROOT) are explicitly marked and do not affect the stability of production-ready projects.

Adding a new experiment: create `src/<experiment>/`, add tests under `tests/test_<experiment>_*.py`, and update this table.

## Architecture

Playground is organized around orthogonal project packages under `src/`. The repository-level
architecture is intentionally thin: shared tooling, CI, and documentation wrap independent
experiments without creating shared domain dependencies between them.

| Layer                | Location              | Notes                                                             |
| -------------------- | --------------------- | ----------------------------------------------------------------- |
| Maintained projects  | `src/<project>/`      | Self-contained runtime code for each experiment                   |
| Shared contracts     | `src/contracts.py`    | Small design-by-contract helpers available to maintained modules  |
| Tests                | `tests/`              | Pytest coverage grouped by project or workflow                    |
| Project docs         | `src/<project>/docs/` | Deep documentation for a single experiment                        |
| Repository docs      | `docs/`               | Architecture, workflow, development, and assessment documentation |
| Historical snapshots | `archive/`            | Reference-only material excluded from active lint/test collection |

For contributor-facing architecture details, project boundaries, and guidance for adding new
experiments, see [docs/architecture/REPOSITORY_ARCHITECTURE.md](docs/architecture/REPOSITORY_ARCHITECTURE.md).

## Prerequisites

- Python 3.11 or higher
- pip

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/D-sorganization/Playground.git
   cd Playground
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. (Optional) Copy the environment template and fill in your values:

   ```bash
   cp .env.example .env
   ```

## Usage

### Calculator Web App

```bash
python -m calculator.webapp
```

The Flask server starts on `http://localhost:5000`.

### Asteroid Jumper (requires PyQt6)

```bash
python -m asteroid_jumper.app
```

### Running Scripts

Utility and analysis scripts live in the `scripts/` directory:

```bash
python scripts/run_assessment.py
python scripts/analyze_completist_data.py
```

## Testing

Run the full test suite with pytest:

```bash
pytest
```

Run tests with coverage reporting:

```bash
pytest --cov=src --cov-report=term-missing
```

Run a specific test file:

```bash
pytest tests/test_ti89_calculator.py
```

Skip heavy simulation tests:

```bash
pytest -m "not live_simulation"
```

## Code Quality

The repository enforces quality through Ruff, Black, Mypy, and Pip-Audit. Linting and formatting run automatically in CI and via pre-commit hooks.

```bash
# Lint
ruff check src/ tests/

# Format
black src/ tests/

# Type check
mypy src/
```

## CI/CD

GitHub Actions workflows handle continuous integration on every push and pull request to `main`. The standard pipeline (`ci-standard.yml`) runs linting, type checking, and the test suite. Additional workflows cover heavy integration tests, documentation auditing, and automated code quality fixes.

## Project Structure

```
Playground/
  src/
    Project_GROOT/    # Golf swing imitation-learning pipeline
    asteroid_jumper/  # PyQt6 asteroid navigation game
    mypy_agent/       # Experimental type-analysis utilities
    workout_tracker/  # Flask/SQLite workout planning PWA
    contracts.py      # Shared DbC helpers
  tests/              # Pytest test suite
  scripts/            # Utility and analysis scripts
  docs/               # Documentation
  .github/workflows/  # CI/CD pipelines
```

## License

See individual project directories for licensing information.
