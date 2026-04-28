# Repository Architecture

Playground is a monorepo for independent experiments. The repository provides
shared CI, dependency metadata, tests, and assessment tooling, but each
experiment owns its domain logic and runtime boundaries.

## Architectural Principles

- Keep experiments orthogonal. Code in one project should not import domain
  logic from another project.
- Keep maintained Python packages under `src/` and their validation under
  `tests/`.
- Treat `archive/` as historical reference material, not active source.
- Prefer explicit configuration through environment variables, config files, or
  CLI arguments instead of hard-coded local paths.
- Update README and SPEC when adding a maintained project or changing repository
  structure.

## Maintained Source Map

| Area                  | Location                                  | Responsibility                                                                            |
| --------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------- |
| Shared contracts      | `src/contracts.py`                        | Lightweight design-by-contract helpers used by maintained modules                         |
| Asteroid Jumper       | `src/asteroid_jumper/`                    | PyQt6 asteroid navigation demo, rendering helpers, camera transforms, and particle trails |
| Workout Tracker       | `src/workout_tracker/`                    | Flask/SQLite progressive web app for workout planning, parsing, execution, and analytics  |
| Project GROOT         | `src/Project_GROOT/`                      | Experimental golf biomechanics simulation, data, training, and evaluation workflows       |
| MyPy agent experiment | `src/mypy_agent/`                         | Experimental type-analysis utilities                                                      |
| Tests                 | `tests/`                                  | Pytest coverage for maintained source modules and selected integration flows              |
| Automation docs       | `docs/architecture/JULES_ARCHITECTURE.md` | Agent/workflow architecture for Jules automation                                          |

## Project Boundaries

Each maintained experiment is expected to be self-contained:

1. Runtime code lives in a dedicated `src/<project>/` package.
2. Tests live in `tests/` and use names that identify the project they cover.
3. Project-specific docs stay near the project when they are only useful to that
   project, such as `src/Project_GROOT/docs/`.
4. Repository-wide docs belong under `docs/`, with architecture material under
   `docs/architecture/`.

Cross-project imports should be limited to intentionally shared infrastructure,
such as `src/contracts.py`. If an experiment needs reusable functionality from
another experiment, extract a small shared helper first and document the new
boundary in README and SPEC.

## Runtime Data Flow

Most projects run independently from the command line:

- `python -m asteroid_jumper.app` starts the desktop asteroid navigator.
- `python -m workout_tracker` starts the local Workout Tracker Flask app and
  uses SQLite at `WORKOUT_DB_PATH` or the default user database path.
- Project GROOT tools run as experiment-specific scripts and read their own
  configuration, data, and model artifacts.

There is no shared service bus, database, or public package API across the
repository. CI is the primary integration surface: it installs dependencies,
runs lint/type checks, runs pytest, and publishes coverage.

## Adding Or Changing A Project

When adding a maintained experiment:

1. Create `src/<project>/` for source code.
2. Add focused tests under `tests/`.
3. Document usage in the README project table and command examples.
4. Update SPEC sections for architecture, interfaces, data/configuration, and
   testing impact.
5. Keep temporary implementation notes under `docs/development/`.

When changing an existing project boundary, update this document before the PR is
opened so reviewers can evaluate whether the monorepo remains orthogonal.
