# SPEC.md — Repository Specification Document

<!--
  TEMPLATE VERSION: 1.0.0
  LAST UPDATED: 2026-03-30

  This is the canonical specification template for all repositories in the
  D-sorganization fleet. Every repo MUST have a SPEC.md at its root.

  INSTRUCTIONS:
  1. Copy this template to the root of your repository as SPEC.md
  2. Fill in every section — leave nothing as "[TODO]"
  3. Keep this document updated with every PR that changes functionality
  4. CI will block merges if SPEC.md is stale (source changed but spec didn't)

  AUDIENCE: This document is designed for both human developers AND AI agents.
  Write clearly, use concrete examples, and avoid ambiguity.
-->

## 1. Identity

| Field                   | Value                                           |
| ----------------------- | ----------------------------------------------- |
| **Repository Name**     | `Playground`                                    |
| **GitHub URL**          | `https://github.com/D-sorganization/Playground` |
| **Owner**               | D-sorganization                                 |
| **Primary Language(s)** | Python 3.11+                                    |
| **License**             | MIT                                             |
| **Current Version**     | 1.0.1                                           |
| **Spec Version**        | 1.1.16                                          |
| **Last Spec Update**    | 2026-05-05                                      |

## 2. Purpose & Mission

The Playground is a fleet-wide sandbox for testing, experimentation, and learning. It serves as the hub for demo projects, experimental code, and Project GROOT (simulation, evaluation, and training framework). The repository enforces A-tier fleet protocol compliance while providing a safe environment for new ideas without production code constraints. Historical experiments can remain under `archive/`, but they are explicitly out of the maintained source surface.

## 3. Goals & Non-Goals

### Goals

- Sandbox for testing new ideas and experimental implementations
- Host maintained demo projects and experimental sandboxes without confusing archived snapshots for live code
- Implement and validate Project GROOT simulation, training, and evaluation pipelines
- Enforce fleet CI standards and provide compliant CI templates for other repositories
- Maintain clean dependency slate and minimal external requirements

### Non-Goals

- Not for production code or mission-critical applications
- Not a library consumed or depended upon by other fleet repositories
- Not a general-purpose framework or foundational platform

## 4. Architecture Overview

### System Context

The Playground is an independent repository with no fleet dependencies. It may serve as a reference or template for CI/CD practices but does not depend on or expose interfaces to other fleet repositories. The repository is self-contained and designed for internal experimentation.

Contributor-facing repository architecture guidance is maintained in `docs/architecture/REPOSITORY_ARCHITECTURE.md`. That document describes project boundaries, active source ownership, runtime data flow, and the checklist for adding or changing maintained experiments.

### Module Map

```
Playground/
├── src/
│   ├── asteroid_jumper/        # Asteroid Field Navigator demo
│   ├── workout_tracker/        # Notes-based gym tracker (Flask + SQLite PWA)
│   │   ├── static/             # Frontend (vanilla JS, CSS, manifest)
│   │   ├── templates/          # Jinja templates (SPA shell)
│   │   ├── schema.sql          # SQLite schema
│   │   ├── models.py           # Exercise / Workout / WorkoutSet dataclasses
│   │   ├── db.py               # WorkoutRepository (repository pattern, LoD)
│   │   ├── parser.py           # Free-text notes -> structured sets
│   │   ├── autocomplete.py     # Fuzzy suggest (trigram + Damerau-Levenshtein)
│   │   ├── stats.py            # Volume / 1RM / PRs / timeseries / frequency
│   │   └── app.py              # Flask app factory + /api routes
│   └── Project_GROOT/          # Simulation, evaluation, training framework
│       ├── sim/                # Simulation engine
│       ├── train/              # Training pipelines
│       ├── eval/               # Evaluation framework
│       ├── data/               # Datasets and data processing
│       ├── docs/               # Project documentation
│       └── tools/              # Utility scripts and tools
├── archive/                    # Historical snapshots excluded from active lint/test collection
├── tests/                       # Test suite (20+ test files, incl. workout_tracker)
├── tools/                       # MATLAB utilities and scripts
├── SECURITY.md                  # Supported-version and vulnerability reporting policy
├── .github/workflows/           # CI/CD pipelines (43 workflows)
└── .fleetrc                     # Fleet protocol compliance config
```

### Key Components

| Component                | Location                                | Purpose                                                                            |
| ------------------------ | --------------------------------------- | ---------------------------------------------------------------------------------- |
| Asteroid Field Navigator | `src/asteroid_jumper/`                  | Demo project: navigate through asteroid fields with collision detection            |
| AJ Camera                | `src/asteroid_jumper/camera.py`         | Viewport, pan, zoom, and world↔screen coordinate transforms                       |
| AJ Draw                  | `src/asteroid_jumper/draw.py`           | Sprite and primitive drawing helpers (background, asteroids, jumper)               |
| AJ Particles             | `src/asteroid_jumper/particles.py`      | TrailBuffer particle/trail system for position history management                  |
| Workout Tracker          | `src/workout_tracker/`                  | Notes-based gym tracking PWA: plan, execute, recall, and analyze workouts          |
| WT Models                | `src/workout_tracker/models.py`         | Exercise/Workout/WorkoutSet dataclasses with DbC-style validators                  |
| WT Repository            | `src/workout_tracker/db.py`             | SQLite repository (LoD): CRUD, merge, rename, cascade deletes, legacy FK migration |
| WT Parser                | `src/workout_tracker/parser.py`         | Parse notes like `Bench 3x5 @ 135` into structured sets                            |
| WT Autocomplete          | `src/workout_tracker/autocomplete.py`   | Trigram + Damerau-Levenshtein fuzzy ranking for exercise names                     |
| WT Stats                 | `src/workout_tracker/stats.py`          | Epley/Brzycki 1RM, PRs, per-exercise summary, timeseries, frequency                |
| WT App                   | `src/workout_tracker/app.py`            | Flask factory, `/api/*` JSON surface, `/api/health` diagnostic, PWA shell          |
| Project GROOT            | `src/Project_GROOT/`                    | Integrated simulation, training, evaluation, and data framework                    |
| GROOT Simulation         | `src/Project_GROOT/sim/`                | Core simulation engine for environment and agent interactions                      |
| GROOT Training           | `src/Project_GROOT/train/`              | Training pipelines and model optimization                                          |
| GROOT Evaluation         | `src/Project_GROOT/eval/`               | Evaluation and benchmarking framework                                              |
| GROOT Data               | `src/Project_GROOT/data/`               | Dataset management and preprocessing                                               |
| MATLAB Tools             | `tools/`                                | MATLAB utilities for analysis and visualization                                    |
| Archive Snapshots        | `archive/`                              | Historical references retained outside the maintained source surface               |
| Security Policy          | `SECURITY.md`                           | Supported-version and vulnerability disclosure guidance                            |
| Workflow Guard           | `scripts/check_local_only_workflows.py` | CI helper that rejects newly added GitHub-hosted runner routing in workflow diffs  |

## 5. Desired Functionality

### Core Features

| #   | Feature                        | Status | Description                                                                                                                                                                             |
| --- | ------------------------------ | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1  | Asteroid Field Navigator       | ✅     | Demo project with collision detection and navigation mechanics                                                                                                                          |
| F2  | Archived experiment quarantine | ✅     | Keeps historical snapshots available for reference without treating them as maintained code                                                                                             |
| F3  | Project GROOT Simulation       | 🔄     | Core simulation engine with environment and agent interactions                                                                                                                          |
| F4  | Fleet CI Compliance Template   | ✅     | Reference CI/CD configuration enforcing fleet standards                                                                                                                                 |
| F5  | Assessment aggregation tooling | ✅     | Builds per-category assessments and compiles `docs/assessments/Comprehensive_Assessment.md`                                                                                             |
| F6  | Workout Tracker (PWA)          | ✅     | Mobile-first Flask/SQLite app: fuzzy exercise autocomplete, notes-based plans, set-by-set execution, previous-session recall, auto 1RM/PR/volume/frequency analytics, typo rename+merge |

### API / Interface Contract

The Playground does not expose a public API or library interface. Maintained projects live under `src/` and `tests/`. Project GROOT provides internal interfaces for simulation, training, and evaluation workflows consumed within the repository only. Archived content under `archive/` is intentionally excluded from the normal maintained execution path.

Workout Tracker exposes a local HTTP JSON API (in-process, not an external service) when run via `python -m workout_tracker`:

| Method + Path                                                 | Purpose                                           |
| ------------------------------------------------------------- | ------------------------------------------------- |
| `GET /`                                                       | SPA shell (HTML)                                  |
| `GET /api/exercises`                                          | List exercises (catalog)                          |
| `GET /api/exercises/suggest?q=...`                            | Fuzzy autocomplete suggestions                    |
| `GET /api/exercises/last_session?q=...&exclude=...`           | Previous-session recall excluding current workout |
| `POST /api/exercises`                                         | Get-or-create an exercise by name                 |
| `PUT /api/exercises/{id}`                                     | Rename (fix typos)                                |
| `POST /api/exercises/{src}/merge_into/{target}`               | Merge duplicates, move all sets                   |
| `DELETE /api/exercises/{id}`                                  | Delete exercise and its set history               |
| `GET/POST /api/workouts`, `GET/PUT/DELETE /api/workouts/{id}` | Workout CRUD (date, title, status, notes)         |
| `POST /api/workouts/{id}/sets`                                | Add a planned or executed set                     |
| `PUT/DELETE /api/sets/{id}`                                   | Update/execute/delete a set                       |
| `POST /api/parse`                                             | Parse notes text into structured sets             |
| `POST /api/workouts/{id}/import`                              | Parse + append sets to a workout                  |
| `GET /api/stats/overview`                                     | Totals, PRs, per-exercise summary, freq.          |
| `GET /api/stats/exercise/{id}`                                | Per-exercise timeseries + PRs                     |

## 6. Data & Configuration

### Input Data

| Input                           | Format  | Source              | Schema                                                                     |
| ------------------------------- | ------- | ------------------- | -------------------------------------------------------------------------- |
| Asteroid field parameters       | JSON    | Demo configuration  | Defined in asteroid_jumper config files                                    |
| Solar system initial conditions | JSON    | Demo configuration  | Defined in solar system model config                                       |
| GROOT simulation parameters     | YAML    | Experiment specs    | Schema defined in GROOT docs                                               |
| Training datasets               | CSV/NPZ | GROOT data pipeline | Varies by experiment                                                       |
| Workout notes text              | Text    | User input (Plans)  | Lines like `Bench 3x5 @ 135`, `135x5`                                      |
| Workout set entries             | JSON    | Workout Tracker API | `exercise_name`, `actual_reps`, `actual_weight`, `rpe`, `unit`, `executed` |

### Output Data

| Output                  | Format   | Destination                            | Description                               |
| ----------------------- | -------- | -------------------------------------- | ----------------------------------------- |
| Simulation trajectories | JSON     | Memory/file                            | Asteroid navigator and solar system paths |
| Model checkpoints       | PKL/PT   | `data/checkpoints/`                    | GROOT training model states               |
| Evaluation metrics      | CSV/JSON | `eval/results/`                        | Performance reports and benchmarks        |
| Training logs           | TXT/CSV  | `logs/`                                | Training progress and diagnostics         |
| Workout tracker DB      | SQLite   | `~/.workout_tracker.db` (configurable) | Exercises, workouts, sets schema          |

### Configuration

Configuration is managed via:

- **Environment variables**: `GROOT_SEED`, `GROOT_DEBUG`, `GROOT_DATA_PATH`, `WORKOUT_DB_PATH` (SQLite path for Workout Tracker), `HOST`/`PORT`/`DEBUG` (Workout Tracker dev server)
- **Config files**: YAML specifications in `src/Project_GROOT/conf/`
- **CLI arguments**: Scripts in `src/Project_GROOT/tools/` accept configuration overrides
- **.fleetrc**: Fleet protocol compliance configuration at repository root
- **Assessment tooling**: `make_comprehensive.py` compiles the generated category assessments into the repository-wide comprehensive report

## 7. Testing Specification

### Testing Strategy

Test pyramid approach with emphasis on unit tests covering individual components, integration tests validating workflows, and live simulation markers for long-running experiments. Coverage is tracked via Codecov and enforced at CI time. Tests use pytest with custom markers for selective execution.

Coverage collection omits `archive/*` so historical snapshots do not affect maintained-source coverage metrics.

### Test Organization

| Category        | Location                | Framework        | Markers                        |
| --------------- | ----------------------- | ---------------- | ------------------------------ |
| Unit            | `tests/unit/`           | pytest           | `@pytest.mark.unit`            |
| Integration     | `tests/integration/`    | pytest           | `@pytest.mark.integration`     |
| Live Simulation | `tests/live_sim/`       | pytest           | `@pytest.mark.live_simulation` |
| Benchmarks      | `tests/test_bench_*.py` | pytest-benchmark | `@pytest.mark.benchmark`       |

### Coverage Requirements

| Scope                                         | Minimum | Current | Enforced By                |
| --------------------------------------------- | ------- | ------- | -------------------------- |
| Overall                                       | 60%     | 76%     | CI (`--cov-fail-under=60`) |
| Critical modules (asteroid_jumper, GROOT sim) | 75%     | 80%+    | CI linting checks          |

### Required Test Scenarios

- [ ] Unit tests for asteroid collision detection algorithms pass with 100% pass rate
- [ ] GROOT simulation environment initializes correctly with parametric configurations
- [ ] Archived snapshots remain excluded from normal lint/test collection unless explicitly restored
- [ ] Live simulation markers correctly skip in fast CI runs
- [ ] All maintained test files execute without errors on Python 3.11+3.12
- [ ] CI workflows are checked by `scripts/check_local_only_workflows.py` so `ubuntu-latest`, `windows-latest`, or `macos-latest` routing is rejected
- [x] Workout Tracker: 137 tests across models, parser, autocomplete, stats, db, routes pass (expanded utilities coverage in PR #414)
- [x] Workout Tracker: fuzzy autocomplete recovers from typos (e.g. `bnech` → `Bench Press`)
- [x] Workout Tracker: parser handles `3x5 @ 135`, `135x5`, header-then-sets, comma-separated, bodyweight
- [x] Workout Tracker: Flask startup and request-scoped SQLite connections release file handles on Windows before temporary database cleanup
- [x] Workout Tracker: upgraded databases rebuild legacy exercise foreign keys so deleting an exercise cascades existing sets
- [x] Workout Tracker: benchmark suite covers parser, autocomplete, and stats hot paths with pytest-benchmark JSON snapshots stored under `.benchmarks/`
- [x] Workout Tracker: design-by-contract coverage with precondition, postcondition, invariant, and edge-case tests for utilities (PR #414)

## 8. Quality Standards

### Code Quality Tools

| Tool      | Version       | Purpose                                                                             | Blocking? |
| --------- | ------------- | ----------------------------------------------------------------------------------- | --------- |
| ruff      | Latest        | Linting + formatting                                                                | Yes       |
| black     | Latest        | Code formatting                                                                     | Yes       |
| mypy      | Latest        | Type checking                                                                       | Yes       |
| bandit    | Latest        | Security scanning                                                                   | Yes       |
| pip-audit | Latest        | Dependency auditing                                                                 | Yes       |
| CodeQL    | GitHub-hosted | Multi-language SAST for Python and JavaScript/TypeScript with SARIF artifact upload | Yes       |
| Semgrep   | Latest        | GitHub Actions workflow and secret-pattern scanning with SARIF artifact upload      | No        |

### Design Principles

- **TDD**: Enforced — test files exist for all new features before implementation is merged
- **Design by Contract (DbC)**: Yes — preconditions and postconditions documented in GROOT framework
- **DRY**: Yes — utility functions centralized in `src/Project_GROOT/tools/`
- **Orthogonality**: Yes — simulation, training, and evaluation modules are decoupled and independently testable

### CI/CD Pipeline

| Workflow                | Trigger         | Purpose                                                                                                                                                   | Blocking? |
| ----------------------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| `ci-standard.yml`       | Push/PR         | Quality gates, linting, type checking, tests (with venv bootstrap for pytest PATH resolution)                                                             | Yes       |
| `codeql.yml`            | Push/PR/Weekly  | CodeQL SAST analysis for maintained Python and JavaScript/TypeScript source; uploads SARIF artifacts without requiring GitHub code scanning to be enabled | Yes       |
| `semgrep-workflows.yml` | Push/PR/Weekly  | Semgrep scan of GitHub Actions workflows and secret patterns; uploads SARIF artifacts for triage                                                          | No        |
| `benchmarks.yml`        | Weekly/manual   | Runs Workout Tracker pytest-benchmark suite and uploads JSON benchmark snapshots                                                                          | No        |
| `jules-agent-*.yml`     | Schedule/Manual | Jules agent integration and automation                                                                                                                    | No        |
| Fleet compliance checks | Push/PR         | Enforce .fleetrc protocol standards                                                                                                                       | Yes       |

## 9. Dependencies

### Runtime Dependencies

| Package | Version | Purpose                                                         |
| ------- | ------- | --------------------------------------------------------------- |
| PyYAML  | >=6.0   | YAML configuration parsing for maintained Project GROOT tools   |
| Flask   | >=3.0   | Workout Tracker HTTP server (optional; only if running the app) |

### Development Dependencies

| Package          | Version | Purpose                |
| ---------------- | ------- | ---------------------- |
| pytest           | >=7.0   | Testing framework      |
| pytest-benchmark | Latest  | Performance benchmarks |
| pytest-cov       | >=4.0   | Coverage reporting     |
| ruff             | Latest  | Linting and formatting |
| black            | Latest  | Code formatting        |
| mypy             | >=1.0   | Static type checking   |
| bandit           | >=1.7   | Security scanning      |
| pip-audit        | >=2.4   | Dependency auditing    |

### Fleet Dependencies

| Repo | Relationship | Description                                                |
| ---- | ------------ | ---------------------------------------------------------- |
| None | —            | Playground has no dependencies on other fleet repositories |

## 10. Deployment & Operations

### How to Run

```bash
# Prerequisites
- Python 3.11 or 3.12
- pip and venv

# Installation
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
pip install -r requirements-dev.txt

# Running demos
python src/asteroid_jumper/demo.py
python src/solar_system_model/demo.py

# Running Project GROOT
python -m src.Project_GROOT.sim --config conf/default_sim.yaml
python -m src.Project_GROOT.train --config conf/default_train.yaml
python -m src.Project_GROOT.eval --results data/checkpoints/model.pt

# Running the Workout Tracker (Flask + SQLite PWA)
pip install flask
python -m workout_tracker   # -> http://127.0.0.1:5000
# Override SQLite path: WORKOUT_DB_PATH=/tmp/wt.db python -m workout_tracker
# Health check: GET /api/health returns database reachability and logs diagnostics

# Running tests
pytest                          # All tests
pytest -m unit                  # Unit tests only
pytest -m live_simulation       # Live simulation tests only
pytest --cov=src --cov-fail-under=60
```

### Build Artifacts

| Artifact           | Format   | Destination              |
| ------------------ | -------- | ------------------------ |
| Coverage reports   | HTML/XML | `.coverage/` and Codecov |
| Test results       | XML      | `.pytest_cache/`         |
| Model checkpoints  | PKL/PT   | `data/checkpoints/`      |
| Evaluation reports | CSV/JSON | `eval/results/`          |

## 11. Roadmap & Open Issues

### Current Phase

Active development with focus on Project GROOT implementation. Demos (Asteroid Field, Calculator, Solar System) are complete and stable. Flask CI infrastructure (41 workflows) is fully operational.

### Planned Work

| Priority | Item                               | Issue/PR | Target Date |
| -------- | ---------------------------------- | -------- | ----------- |
| P0       | Complete GROOT simulation engine   | TBD      | 2026-04-30  |
| P1       | Implement GROOT training pipelines | TBD      | 2026-05-15  |
| P2       | Add GROOT evaluation framework     | TBD      | 2026-05-30  |
| P3       | Document GROOT data pipeline       | TBD      | 2026-06-15  |

### Known Limitations

- Project GROOT simulation engine is in progress — training and evaluation pipelines not yet integrated
- MATLAB tools require MATLAB runtime; Python-only environments cannot use these utilities
- Solar System demo uses simplified physics (no relativistic effects, limited to 2D/3D visualization)
- Asteroid Field demo uses simple collision detection — not optimized for thousands of objects

## 12. Change Log

| Date       | Version | Changes                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ---------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-05-11 | 1.1.17  | Format formatting violations in `scripts/` and `src/Project_GROOT/` to pass Ruff lint checks in CI, and ensure `test_archive_quarantine.py` passes by adding `norecursedirs = ["archive"]` to `pyproject.toml`.                                                                                                                                                                                                            |
| 2026-05-05 | 1.1.16  | Fix(#418): restore the legacy helper exports from `scripts/analyze_completist_data.py` after the completist tooling split so the maintained script tests still collect and exercise the decomposed helper modules without changing repository behavior.                                                                                                                                                                  |
| 2026-05-05 | 1.1.15  | Fix(#418): apply Ruff formatting to the five maintained Python files that were causing `quality-gate` to fail on `main`, and tighten `asteroid_jumper.renderer_draw.draw_hud_lines()` typing so the subsequent mypy step stays green; repository behavior and interfaces are unchanged.                                                                                                                                   |
| 2026-04-28 | 1.1.12  | CI(#363): add a local-only workflow guard with unit coverage so GitHub Actions workflows cannot introduce GitHub-hosted runner routing; document that dependency vulnerabilities found by blocking `pip-audit` require remediation or a documented allowlist exception.                                                                                                                                                    |
| 2026-04-28 | 1.1.11  | Fix(#369): add Workout Tracker startup diagnostic logging with structured database metadata and expose `/api/health` as a lightweight database reachability check that also emits a structured health log record.                                                                                                                                                                                                          |
| 2026-04-28 | 1.1.10  | Fix(#367,#370): add CodeQL SAST for Python and JavaScript/TypeScript on push, pull request, and weekly schedule; add Semgrep workflow scanning for GitHub Actions and secret-pattern rules; upload SARIF artifacts so security scanning works even when GitHub code scanning is unavailable.                                                                                                                               |
| 2026-04-28 | 1.1.9   | Fix(#373): replace placeholder benchmark file with pytest-benchmark coverage for Workout Tracker parser, fuzzy autocomplete, and stats rollups; configure benchmark storage under `.benchmarks/`; add a weekly/manual benchmark workflow that uploads JSON results.                                                                                                                                                        |
| 2026-04-28 | 1.1.8   | Docs(#392): document the repository `SECURITY.md` supported-version and vulnerability reporting policy, and record that coverage omits archived snapshots from maintained-source metrics.                                                                                                                                                                                                                                  |
| 2026-04-28 | 1.1.7   | Docs(#365): add contributor-facing repository architecture guidance and link it from README/SPEC so project boundaries, runtime data flow, and new-experiment expectations are visible from top-level docs.                                                                                                                                                                                                                |
| 2026-04-28 | 1.1.6   | Chore(#364): remove stale tracked `archive/` snapshots while preserving the documented quarantine contract that archived material stays outside normal lint and test collection.                                                                                                                                                                                                                                           |
| 2026-04-27 | 1.1.5   | Fix(#botched): added trailing newline to bench_basic.py and resolved git merge conflicts in SPEC.md, app.py, and test_workout_tracker_app.py                                                                                                                                                                                                                                                                               |
| 2026-04-22 | 1.1.4   | Fix(#354): add a Workout Tracker migration that rebuilds legacy `sets` tables so `exercise_id` uses `ON DELETE CASCADE`, keeping upgraded SQLite databases aligned with fresh installs and preserving existing workout-set history during deletes.                                                                                                                                                                         |
| 2026-04-22 | 1.1.3   | Fix(#330,#332,#336): harden Workout Tracker entry parsing and execution semantics by preserving entered set order, splitting comma-separated set shorthand into independent sets, and capping per-session autocomplete search results to keep response behavior deterministic and stable under large exercise histories.                                                                                                   |
| 2026-04-21 | 1.0.25  | Fix(#343): key Workout Tracker previous-session recall cache entries by active workout context as well as exercise name, so recall results fetched while editing one workout are not reused after switching to another workout.                                                                                                                                                                                            |
| 2026-04-21 | 1.0.24  | Fix(#342): make Workout Tracker previous-session recall select from all candidate workouts instead of the 500 most recent workouts; add a route regression for older exercise history hidden behind newer unrelated workouts.                                                                                                                                                                                              |
| 2026-04-20 | 1.0.23  | Test coverage(#nightly): close Workout Tracker startup schema connection after initialization; add route regressions for exercise rename/merge/delete, workout deletion, set validation/delete, executed imports, per-exercise stats, and Windows SQLite file-handle cleanup; set pytest `pythonpath` to `src` for targeted package tests.                                                                                 |
| 2026-04-14 | 1.0.22  | docs(#256): document independent-experiments convention in README; add project maturity table; clarify per-project quality scope.                                                                                                                                                                                                                                                                                          |
| 2026-04-14 | 1.0.21  | Refactor(#246): decompose `asteroid_jumper/renderer.py` into `camera.py` (Camera viewport class), `draw.py` (sprite/primitive drawing helpers), and `particles.py` (TrailBuffer particle system); `draw_helpers.py` retained as backward-compat re-export shim; 18 camera tests + 9 draw tests + 17 particle tests added.                                                                                                  |
| 2026-04-14 | 1.0.20  | Refactor(#259): split 3 monolithic scripts; extracted `eval_plots.py`, `eval_report.py`, `renderer_draw.py`, `mypy_agent_types.py`, and `mypy_fix_strategies.py` into focused companion modules.                                                                                                                                                                                                                           |
| 2026-04-14 | 1.0.18  | ci: retrigger CI for #261 — bump SPEC version above main (1.0.17)                                                                                                                                                                                                                                                                                                                                                          |
| 2026-04-14 | 1.0.17  | Umbrella(#261): confirmed all P1 A-N refresh remediations complete — #258 (function decomposition ≤30 LOC) and #259 (monolithic script splitting ≤300 LOC) fully addressed; spec version timeline reconciled.                                                                                                                                                                                                              |
| 2026-04-14 | 1.0.18  | Refactor(#258): decomposed top-5 oversized functions to ≤30 LOC each in `retarget_to_sim.py`, `club_track.py`, `video_ingest.py`, `run_assessment.py`, and `analyze_completist_data.py`; extracted landmark constants, arm-joint helpers, frame-clamping, clip/smooth/derivative methods, and markdown-template builders.                                                                                                  |
| 2026-04-14 | 1.0.16  | Fix(#275): added DbC precondition validation to `PoseRetargeter.retarget()` for skeleton shape, joint count, frame count, club_head length, and configuration parameters; added behavioral tests for the precondition guards.                                                                                                                                                                                              |
| 2026-04-14 | 1.0.15  | Fix(#274): replaced import/hasattr smoke tests in `test_Project_GROOT_train_imitation_train.py` with behavioral tests for `SwingDemonstrationDataset.__getitem__` (truncate, pad, tensor types, `__len__`, empty dir) and `PolicyNetwork.forward` (shape, batch independence, finite outputs); added `_validate_imitation_config` precondition validator to `imitation_train.py`; guarded optional `SummaryWriter` import. |
| 2026-04-14 | 1.0.14  | Fix(DbC,#249,#252): added NotImplementedError guards to placeholder functions in rollout_eval.py, video_ingest.py, rl_finetune.py and added DbC input validation; added behavioral tests for GROOT training and eval scripts.                                                                                                                                                                                              |
| 2026-04-14 | 1.0.13  | Decomposed oversized functions in Project GROOT: `rollout_eval.py`, `club_track.py`, `imitation_train.py`, `pose_convert.py`, `retarget_to_sim.py`, and `run_assessment.py`; extracted focused helper functions and expanded behavioral test coverage across 8 files.                                                                                                                                                      |
| 2026-04-13 | 1.0.12  | Added Jules code quality review scripts, reports, workflows and fixed CI environment for Pytest tests.                                                                                                                                                                                                                                                                                                                     |
| 2026-04-13 | 1.0.11  | Added Jules code quality review scripts, reports, workflows and fixed CI environment for Pytest tests.                                                                                                                                                                                                                                                                                                                     |
| 2026-04-11 | 1.0.10  | Improved Design-by-Contract error messages in `asteroid_jumper/physics.py` (issue #255) — replaced generic `"DbC Blocked: Precondition failed."` strings in `moment_of_inertia_ellipse`, `moment_of_inertia_disk`, `moment_of_inertia_rod`, `SpringLaunch.__post_init__`, `SpringLaunch.step`, and `step_simulation` with descriptive messages identifying the offending argument, its value, and the valid constraint.    |
| 2026-04-11 | 1.0.9   | Issue #250: replaced sham tests in `tests/test_architecture_dbc.py` and `tests/test_asteroid_jumper_physics.py` with real Design-by-Contract precondition tests and physics assertions (kinematics, impulse, momentum conservation, analytical moment-of-inertia formulas, and half-sine spring launch total impulse).                                                                                                     |
| 2026-04-11 | 1.0.8   | Removed duplicate `logger = logging.getLogger(__name__)` declarations in `club_track.py`, `pose_convert.py`, and `imitation_train.py` (issue #251) to enforce DRY.                                                                                                                                                                                                                                                         |
| 2026-04-06 | 1.0.7   | Updated `run_assessment.py` and `make_comprehensive.py` scripts to auto-fix logging issues, output correct file structures, and ignore print false positives.                                                                                                                                                                                                                                                              |
| 2026-04-06 | 1.0.6   | Declared `PyYAML` as a runtime dependency because maintained Project GROOT tooling imports `yaml` during normal module loading in CI.                                                                                                                                                                                                                                                                                      |
| 2026-04-06 | 1.0.5   | Quarantined historical archive content from the maintained source surface by documenting `archive/` as reference-only material and excluding it from standard lint/test traversal.                                                                                                                                                                                                                                         |
| 2026-03-30 | 1.0.1   | A-N Assessment remediation (issue #200): auto-formatted 30 files to comply with black 100-char line limit; ruff checks pass with zero violations                                                                                                                                                                                                                                                                           |
| 2026-03-31 | 1.0.2   | CI maintenance: hardened the review-comment archiver against empty tracking JSON, narrowed the blocking mypy invocation to `src/` so self-hosted quality-gate runs no longer fail on duplicate `src.*` module discovery, and added explicit typing to the contract decorators used by the checked source tree.                                                                                                             |
| 2026-03-31 | 1.0.3   | Self-hosted CI follow-up: updated the generated Project GROOT and Asteroid Jumper import-smoke tests to skip cleanly when optional runtime dependencies like `torch`, `gymnasium`, or `PyQt6` are intentionally absent from the blocking CI runner image.                                                                                                                                                                  |
| 2026-03-31 | 1.0.4   | Self-hosted CI stabilization: aligned the Asteroid Jumper test suite with the current contract-enforced `ValueError` behavior so the blocking Linux test job validates the actual runtime invariants rather than outdated `AssertionError` expectations.                                                                                                                                                                   |
| 2026-03-28 | 1.0.0   | Initial specification                                                                                                                                                                                                                                                                                                                                                                                                      |

---

<!--
  SPEC MAINTENANCE RULES:

  1. WHEN TO UPDATE: Any PR that adds, removes, or changes functionality
     described in this spec MUST include a corresponding spec update.

  2. WHO UPDATES: The PR author (human or agent) is responsible.

  3. CI ENFORCEMENT: The spec-check workflow will flag PRs where source
     files changed but SPEC.md did not. This is a blocking check.

  4. REVIEW: Spec changes should be reviewed with the same rigor as code.

  5. VERSION: Bump the Spec Version field when making substantive changes.
     Use semver: major (structure change), minor (new features), patch (corrections).
-->
