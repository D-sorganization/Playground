# Playground

A fleet-wide monorepo for testing, experimentation, and simulation projects. Built with Python 3.11+ and enforced to A-tier standards via automated CI/CD.

## Projects

| Project | Description |
|---------|-------------|
| **Asteroid Jumper** | A PyQt6 desktop application for navigating and jumping between asteroids with real-time physics simulation. |
| **Asteroid Field Navigator** | RRT-based path planning through procedurally generated asteroid fields. |
| **Calculator** | A TI-89-style calculator with a Flask web interface and SymPy-powered symbolic math. |
| **Solar System Model** | A solar system simulation and visualization tool. |
| **Project GROOT** | Golf swing imitation-learning pipeline: video ingestion, pose conversion, MuJoCo simulation, RL fine-tuning, and evaluation. |

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
  Calculator/         # TI-89 calculator with Flask web UI
  Solar System Model/ # Solar system simulation
  Asteroid Field Navigator/ # RRT path planner
  tests/              # Pytest test suite
  scripts/            # Utility and analysis scripts
  tools/              # Code quality tooling
  docs/               # Documentation
  .github/workflows/  # CI/CD pipelines
```

## License

See individual project directories for licensing information.
