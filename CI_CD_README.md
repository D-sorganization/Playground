# CI/CD Setup for Playground Repository

This repository uses a comprehensive but flexible CI/CD pipeline designed for pet projects and experimental code. The checks are **informational and non-blocking** - you can merge PRs even if checks fail, allowing you to use your judgment on a case-by-case basis.

## Overview

The CI/CD pipeline runs automatically on:
- Pull requests to `main` or `master`
- Pushes to `main` or `master`

## What Gets Checked

### Python Projects

The pipeline automatically detects and checks Python code:

1. **Code Quality** - Checks for placeholders, magic numbers, and code quality issues
2. **Linting** - Runs `ruff` to check for code style issues
3. **Formatting** - Checks code formatting with `black`
4. **Type Checking** - Runs `mypy` for type safety (lenient settings)
5. **Testing** - Runs `pytest` if tests are found
6. **Dependencies** - Automatically installs from `requirements.txt` files

### JavaScript/TypeScript Projects

The pipeline automatically detects and checks JavaScript/TypeScript code:

1. **Linting** - Runs `ESLint` if configured
2. **Formatting** - Checks code formatting with `Prettier` if configured
3. **Type Checking** - Runs `tsc` for TypeScript projects
4. **Testing** - Runs `npm test` if configured

### MATLAB Projects

MATLAB checks are available but disabled by default (requires MATLAB runner). To enable, edit `.github/workflows/ci.yml` and set `if: false` to `if: true` for the `matlab-checks` job.

## Configuration Files

### Python Configuration

- **`ruff.toml`** - Ruff linter configuration (lenient for playground projects)
- **`mypy.ini`** - MyPy type checker configuration (flexible settings)
- **`.pre-commit-config.yaml`** - Pre-commit hooks configuration

### JavaScript/TypeScript Configuration

Add these files to your JavaScript/TypeScript projects as needed:

- **`.eslintrc.json`** or **`eslint.config.js`** - ESLint configuration
- **`.prettierrc`** or **`prettier.config.js`** - Prettier configuration
- **`tsconfig.json`** - TypeScript configuration
- **`package.json`** - Should include `lint`, `format`, and `test` scripts

## How to Use

### For New Projects

1. **Python Projects**: Just add your code! The CI will automatically:
   - Find and install from `requirements.txt` files
   - Run linting and type checking
   - Run tests if you have a `tests/` directory

2. **JavaScript/TypeScript Projects**: 
   - Add a `package.json` with appropriate scripts
   - Optionally add ESLint, Prettier, and TypeScript configs
   - The CI will automatically detect and run checks

3. **Mixed Projects**: The CI handles multiple languages automatically!

### Understanding CI Results

- ✅ **All checks passed**: Great! Your code follows best practices.
- ⚠️ **Some checks failed**: Review the output to see what could be improved, but feel free to merge if it's a pet project.
- ❌ **All checks failed**: Consider fixing critical issues, but merging is still allowed for experimental code.

### Ignoring CI Results

Since this is a playground repository, **all CI checks are non-blocking**. You can:

1. **Merge anyway**: GitHub will show a warning but won't block the merge
2. **Review and fix**: Use the CI output to identify issues and fix them
3. **Skip checks**: If a project is truly experimental, you can ignore the results

## Customizing for Your Project

### Making Checks Stricter

If you want stricter checks for a specific project:

1. Create a project-specific `ruff.toml` or `mypy.ini` in your project directory
2. Add a `scripts/quality_check.py` script for custom quality checks
3. The CI will automatically use these configurations

### Making Checks More Lenient

The default configuration is already lenient, but you can:

1. Add files/directories to the `exclude` sections in `ruff.toml` and `mypy.ini`
2. Skip pre-commit hooks: `git commit --no-verify`
3. The CI will still run but won't block merges

## Best Practices (Optional)

While the CI is non-blocking, here are some best practices you might want to follow:

1. **Use type hints** - Makes code more maintainable
2. **Write tests** - Even simple tests help catch bugs
3. **Format code** - Run `black .` and `ruff check --fix .` before committing
4. **Document constants** - If using physical constants, document their units and sources
5. **Seed randomness** - Use `np.random.seed()` or `random.seed()` for reproducibility

## Local Development

### Running Checks Locally

```bash
# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Run all checks manually
pre-commit run --all-files

# Run specific checks
ruff check .
black --check .
mypy .
pytest
```

### For JavaScript/TypeScript Projects

```bash
# Install dependencies
npm install

# Run checks
npm run lint      # If configured
npm run format    # If configured
npm test          # If configured
```

## Troubleshooting

### CI Fails but I Want to Merge

That's fine! The CI is informational. You can merge anyway. The checks use `continue-on-error: true` so they won't block your PR.

### CI Can't Find My Dependencies

Make sure your `requirements.txt` or `package.json` is in a discoverable location. The CI searches recursively for these files.

### CI Runs Too Long

The timeout is set to 15 minutes for Python checks and 10 minutes for JavaScript checks. If your project needs more time, you can adjust the `timeout-minutes` in `.github/workflows/ci.yml`.

### I Don't Want CI for My Project

You can disable CI for specific projects by:
1. Adding them to the `exclude` patterns in the workflow
2. Or simply ignoring the CI results when merging

## Questions?

This is a playground - experiment freely! The CI is here to help you see code quality metrics, not to block your work.

