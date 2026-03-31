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

| Field | Value |
|-------|-------|
| **Repository Name** | `Playground` |
| **GitHub URL** | `https://github.com/D-sorganization/Playground` |
| **Owner** | D-sorganization |
| **Primary Language(s)** | Python 3.11+ |
| **License** | MIT |
| **Current Version** | 1.0.1 |
| **Spec Version** | 1.0.2 |
| **Last Spec Update** | 2026-03-30 |

## 2. Purpose & Mission

The Playground is a fleet-wide sandbox for testing, experimentation, and learning. It serves as the hub for demo projects, experimental code, and Project GROOT (simulation, evaluation, and training framework). The repository enforces A-tier fleet protocol compliance while providing a safe environment for new ideas without production code constraints.

## 3. Goals & Non-Goals

### Goals

- Sandbox for testing new ideas and experimental implementations
- Host demo projects (Asteroid Field Navigator, Calculator, Solar System Model)
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

### Module Map

```
Playground/
├── src/
│   ├── asteroid_jumper/        # Asteroid Field Navigator demo
│   └── Project_GROOT/          # Simulation, evaluation, training framework
│       ├── sim/                # Simulation engine
│       ├── train/              # Training pipelines
│       ├── eval/               # Evaluation framework
│       ├── data/               # Datasets and data processing
│       ├── docs/               # Project documentation
│       └── tools/              # Utility scripts and tools
├── tests/                       # Test suite (20 test files)
├── tools/                       # MATLAB utilities and scripts
├── .github/workflows/           # CI/CD pipelines (41 workflows)
└── .fleetrc                     # Fleet protocol compliance config
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Asteroid Field Navigator | `src/asteroid_jumper/` | Demo project: navigate through asteroid fields with collision detection |
| Project GROOT | `src/Project_GROOT/` | Integrated simulation, training, evaluation, and data framework |
| GROOT Simulation | `src/Project_GROOT/sim/` | Core simulation engine for environment and agent interactions |
| GROOT Training | `src/Project_GROOT/train/` | Training pipelines and model optimization |
| GROOT Evaluation | `src/Project_GROOT/eval/` | Evaluation and benchmarking framework |
| GROOT Data | `src/Project_GROOT/data/` | Dataset management and preprocessing |
| Calculator Demo | `src/` | Simple calculator implementation demo |
| Solar System Model | `src/` | Orbital mechanics and celestial body simulation demo |
| MATLAB Tools | `tools/` | MATLAB utilities for analysis and visualization |

## 5. Desired Functionality

### Core Features

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| F1 | Asteroid Field Navigator | ✅ | Demo project with collision detection and navigation mechanics |
| F2 | Calculator Demo | ✅ | Simple calculator implementation showcase |
| F3 | Solar System Model | ✅ | Celestial mechanics and orbital simulation demo |
| F4 | Project GROOT Simulation | 🔄 | Core simulation engine with environment and agent interactions |
| F5 | Fleet CI Compliance Template | ✅ | Reference CI/CD configuration enforcing fleet standards |
| F6 | Assessment aggregation tooling | ✅ | Builds per-category assessments and compiles `docs/assessments/Comprehensive_Assessment.md` |

### API / Interface Contract

The Playground does not expose a public API or library interface. Each demo project is self-contained and runnable independently. Project GROOT provides internal interfaces for simulation, training, and evaluation workflows consumed within the repository only.

## 6. Data & Configuration

### Input Data

| Input | Format | Source | Schema |
|-------|--------|--------|--------|
| Asteroid field parameters | JSON | Demo configuration | Defined in asteroid_jumper config files |
| Solar system initial conditions | JSON | Demo configuration | Defined in solar system model config |
| GROOT simulation parameters | YAML | Experiment specs | Schema defined in GROOT docs |
| Training datasets | CSV/NPZ | GROOT data pipeline | Varies by experiment |

### Output Data

| Output | Format | Destination | Description |
|--------|--------|-------------|-------------|
| Simulation trajectories | JSON | Memory/file | Asteroid navigator and solar system paths |
| Model checkpoints | PKL/PT | `data/checkpoints/` | GROOT training model states |
| Evaluation metrics | CSV/JSON | `eval/results/` | Performance reports and benchmarks |
| Training logs | TXT/CSV | `logs/` | Training progress and diagnostics |

### Configuration

Configuration is managed via:
- **Environment variables**: `GROOT_SEED`, `GROOT_DEBUG`, `GROOT_DATA_PATH`
- **Config files**: YAML specifications in `src/Project_GROOT/conf/`
- **CLI arguments**: Scripts in `src/Project_GROOT/tools/` accept configuration overrides
- **.fleetrc**: Fleet protocol compliance configuration at repository root
- **Assessment tooling**: `make_comprehensive.py` compiles the generated category assessments into the repository-wide comprehensive report

## 7. Testing Specification

### Testing Strategy

Test pyramid approach with emphasis on unit tests covering individual components, integration tests validating workflows, and live simulation markers for long-running experiments. Coverage is tracked via Codecov and enforced at CI time. Tests use pytest with custom markers for selective execution.

### Test Organization

| Category | Location | Framework | Markers |
|----------|----------|-----------|---------|
| Unit | `tests/unit/` | pytest | `@pytest.mark.unit` |
| Integration | `tests/integration/` | pytest | `@pytest.mark.integration` |
| Live Simulation | `tests/live_sim/` | pytest | `@pytest.mark.live_simulation` |

### Coverage Requirements

| Scope | Minimum | Current | Enforced By |
|-------|---------|---------|-------------|
| Overall | 60% | 70%+ | CI (`--cov-fail-under=60`) |
| Critical modules (asteroid_jumper, GROOT sim) | 75% | 80%+ | CI linting checks |

### Required Test Scenarios

- [ ] Unit tests for asteroid collision detection algorithms pass with 100% pass rate
- [ ] GROOT simulation environment initializes correctly with parametric configurations
- [ ] Calculator demo handles edge cases (division by zero, large numbers, type errors)
- [ ] Solar system model produces physically plausible orbital trajectories
- [ ] Live simulation markers correctly skip in fast CI runs
- [ ] All 20 test files execute without errors on Python 3.11+3.12

## 8. Quality Standards

### Code Quality Tools

| Tool | Version | Purpose | Blocking? |
|------|---------|---------|-----------|
| ruff | Latest | Linting + formatting | Yes |
| black | Latest | Code formatting | Yes |
| mypy | Latest | Type checking | Yes |
| bandit | Latest | Security scanning | Yes |
| pip-audit | Latest | Dependency auditing | Yes |

### Design Principles

- **TDD**: Enforced — test files exist for all new features before implementation is merged
- **Design by Contract (DbC)**: Yes — preconditions and postconditions documented in GROOT framework
- **DRY**: Yes — utility functions centralized in `src/Project_GROOT/tools/`
- **Orthogonality**: Yes — simulation, training, and evaluation modules are decoupled and independently testable

### CI/CD Pipeline

| Workflow | Trigger | Purpose | Blocking? |
|----------|---------|---------|-----------|
| `ci-standard.yml` | Push/PR | Quality gates, linting, type checking, tests | Yes |
| `jules-agent-*.yml` | Schedule/Manual | Jules agent integration and automation | No |
| Fleet compliance checks | Push/PR | Enforce .fleetrc protocol standards | Yes |

## 9. Dependencies

### Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| (None) | N/A | Clean slate — no external runtime dependencies |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=7.0 | Testing framework |
| pytest-cov | >=4.0 | Coverage reporting |
| ruff | Latest | Linting and formatting |
| black | Latest | Code formatting |
| mypy | >=1.0 | Static type checking |
| bandit | >=1.7 | Security scanning |
| pip-audit | >=2.4 | Dependency auditing |

### Fleet Dependencies

| Repo | Relationship | Description |
|------|-------------|-------------|
| None | — | Playground has no dependencies on other fleet repositories |

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

# Running tests
pytest                          # All tests
pytest -m unit                  # Unit tests only
pytest -m live_simulation       # Live simulation tests only
pytest --cov=src --cov-fail-under=60
```

### Build Artifacts

| Artifact | Format | Destination |
|----------|--------|-------------|
| Coverage reports | HTML/XML | `.coverage/` and Codecov |
| Test results | XML | `.pytest_cache/` |
| Model checkpoints | PKL/PT | `data/checkpoints/` |
| Evaluation reports | CSV/JSON | `eval/results/` |

## 11. Roadmap & Open Issues

### Current Phase

Active development with focus on Project GROOT implementation. Demos (Asteroid Field, Calculator, Solar System) are complete and stable. Flask CI infrastructure (41 workflows) is fully operational.

### Planned Work

| Priority | Item | Issue/PR | Target Date |
|----------|------|----------|-------------|
| P0 | Complete GROOT simulation engine | TBD | 2026-04-30 |
| P1 | Implement GROOT training pipelines | TBD | 2026-05-15 |
| P2 | Add GROOT evaluation framework | TBD | 2026-05-30 |
| P3 | Document GROOT data pipeline | TBD | 2026-06-15 |

### Known Limitations

- Project GROOT simulation engine is in progress — training and evaluation pipelines not yet integrated
- MATLAB tools require MATLAB runtime; Python-only environments cannot use these utilities
- Solar System demo uses simplified physics (no relativistic effects, limited to 2D/3D visualization)
- Asteroid Field demo uses simple collision detection — not optimized for thousands of objects

## 12. Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-30 | 1.0.1 | A-N Assessment remediation (issue #200): auto-formatted 30 files to comply with black 100-char line limit; ruff checks pass with zero violations |
| 2026-03-31 | 1.0.2 | CI maintenance: hardened the review-comment archiver against empty tracking JSON, narrowed the blocking mypy invocation to `src/` so self-hosted quality-gate runs no longer fail on duplicate `src.*` module discovery, and added explicit typing to the contract decorators used by the checked source tree. |
| 2026-03-28 | 1.0.0 | Initial specification |

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
