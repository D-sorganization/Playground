# Contributing to Playground

Thank you for your interest in contributing to Playground! This document provides guidelines for contributing to the project.

## Ways to Contribute

1. **Report Issues**: Found a bug, typo, or broken link? [Open an issue](https://github.com/D-sorganization/Playground/issues)
2. **Suggest Features**: Have an idea for a new experiment or tool? Let us know!
3. **Improve Documentation**: Help make guides clearer for beginners
4. **Fix Bugs**: Submit pull requests for any issues you find
5. **Add New Experiments**: Contribute a self-contained simulation or utility

## Getting Started

### Prerequisites

- **Git** - Version control
- **Python 3.11+** - For all projects in the monorepo
- **pip** - Package installer

### Initial Setup

1. **Fork the repository** on GitHub

2. **Clone your fork**:

   ```bash
   git clone https://github.com/YOUR-USERNAME/Playground.git
   cd Playground
   ```

3. **Create and activate a virtual environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

4. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   pip install -e .[dev]
   ```

5. **Verify tests pass**:

   ```bash
   pytest
   ```

6. **Create a branch**:

   ```bash
   git checkout -b feat/issue-NNN-short-desc
   ```

## Branch Convention

Use the following prefixes for branch names:

- `feat/issue-NNN-short-desc` — New features or experiments
- `fix/issue-NNN-short-desc` — Bug fixes
- `chore/issue-NNN-short-desc` — Maintenance tasks, dependency updates
- `docs/issue-NNN-short-desc` — Documentation improvements
- `test/issue-NNN-short-desc` — Adding or updating tests
- `refactor/issue-NNN-short-desc` — Code refactoring without behavior changes

## Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature or experiment
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

## Development Workflow

### Monorepo Structure

Playground is a monorepo where each project under `src/` is **independent**:
- Projects share no domain logic
- Each project has its own tests under `tests/test_<project>_*.py`
- Add new experiments by creating `src/<experiment>/`

### Making Changes

1. **Edit code** in the relevant `src/<project>/` directory
2. **Add or update tests** in `tests/`
3. **Run quality checks**:

   ```bash
   ruff check .
   ruff format .
   mypy .
   pytest
   ```

## Pull Request Process

### Before Submitting

1. **Run all quality checks locally**:

   ```bash
   ruff check .
   ruff format .
   mypy .
   pytest
   ```

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] All linting checks pass (`ruff`, `mypy`)
- [ ] Tests added/updated and passing
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow conventional format
- [ ] PR description is clear and complete
- [ ] CI/CD pipeline passes

### Creating the Pull Request

1. **Push your branch**:

   ```bash
   git push origin feat/issue-NNN-short-desc
   ```

2. **Open PR on GitHub** with a clear title and description

3. **Link related issues** using `Fixes #123` or `Relates to #456`

## Code Review SLA and Reviewer Assignment

- **First review**: Within 48 hours of PR creation
- **Follow-up reviews**: Within 24 hours of subsequent pushes
- **Stale PRs**: PRs without activity for 7 days will be marked with a `stale` label

## Release Process

Playground follows semantic versioning. Releases are managed by maintainers.
See [CHANGELOG.md](CHANGELOG.md) for version history.

## Code Guidelines

### Python

Follow PEP 8 and project-specific standards in [AGENTS.md](AGENTS.md):

- **NO `print()` statements** — Use the `logging` module
- **Type hints** for all functions
- **Docstrings** (Google or NumPy style)
- **No wildcard imports** (`from module import *`)
- **Specific exception handling** (no bare `except:`)
- **Design by Contract** — Use preconditions and postconditions where appropriate

## Reporting Issues

When reporting issues, please include:
- **Description**: What's the problem?
- **Steps to reproduce**: How can we see the issue?
- **Expected behavior**: What should happen?
- **Actual behavior**: What actually happens?
- **Project affected**: Which `src/<project>/` is involved?
- **Environment**: Python version, OS, relevant dependencies

## Adding a New Experiment

1. Create `src/<experiment>/` with a clear, descriptive name
2. Add `tests/test_<experiment>_*.py` with unit tests
3. Update the project table in `README.md`
4. Add a `README.md` inside `src/<experiment>/` documenting the experiment
5. Ensure the experiment is self-contained (no cross-project imports)

## License

By contributing, you agree that your contributions will be licensed under the same terms as the project (MIT).