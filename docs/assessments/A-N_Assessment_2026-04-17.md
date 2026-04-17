# A-N Assessment - Playground - 2026-04-17

Run time: 2026-04-17T08:01:19.6221680Z UTC
Sync status: pull-blocked
Sync notes: ff-only pull failed: fatal: couldn't find remote ref codex/an-assessment-2026-04-14

Overall grade: C (77/100)

## Coverage Notes
- Reviewed tracked first-party files from git ls-files, excluding cache, build, vendor, virtualenv, temp, and generated output directories.
- Reviewed 269 tracked files, including 74 code files, 37 test files, 42 CI files, 9 config/build files, and 131 docs/onboarding files.
- This is a read-only static assessment of committed files. TDD history and confirmed Law of Demeter semantics require commit-history review and deeper call-graph analysis; this report distinguishes those limits from confirmed file evidence.

## Category Grades
### A. Architecture and Boundaries: B (82/100)
Assesses source organization and boundary clarity from tracked first-party layout.
- Evidence: `269 tracked first-party files`
- Evidence: `48 files under source-like directories`

### B. Build and Dependency Management: B (84/100)
Assesses committed build, dependency, and tool configuration.
- Evidence: `Dockerfile.heavy_test`
- Evidence: `pyproject.toml`
- Evidence: `requirements-lock.txt`
- Evidence: `requirements.txt`
- Evidence: `ruff.toml`
- Evidence: `src/Project_GROOT/.devcontainer/Dockerfile`
- Evidence: `src/Project_GROOT/docker-compose.yml`
- Evidence: `src/Project_GROOT/requirements.txt`
- Evidence: `src/Project_GROOT/setup.py`

### C. Configuration and Environment Hygiene: C (78/100)
Checks whether runtime and developer configuration is explicit.
- Evidence: `Dockerfile.heavy_test`
- Evidence: `pyproject.toml`
- Evidence: `requirements-lock.txt`
- Evidence: `requirements.txt`
- Evidence: `ruff.toml`
- Evidence: `src/Project_GROOT/.devcontainer/Dockerfile`
- Evidence: `src/Project_GROOT/docker-compose.yml`
- Evidence: `src/Project_GROOT/requirements.txt`
- Evidence: `src/Project_GROOT/setup.py`

### D. Contracts, Types, and Domain Modeling: B (82/100)
Design by Contract evidence includes validation, assertions, typed models, explicit raised errors, and invariants.
- Evidence: `archive/Calculator/calculator.py`
- Evidence: `archive/Calculator/tests/test_exception_handling.py`
- Evidence: `archive/Calculator/tests/test_ti89_calculator.py`
- Evidence: `archive/Calculator/webapp.py`
- Evidence: `scripts/analyze_completist_data.py`
- Evidence: `scripts/mypy_autofix_agent.py`
- Evidence: `scripts/setup_hooks.py`
- Evidence: `src/Project_GROOT/tools/club_track.py`
- Evidence: `src/Project_GROOT/tools/pose_convert.py`
- Evidence: `src/Project_GROOT/tools/retarget_to_sim.py`

### E. Reliability and Error Handling: C (76/100)
Reliability is graded from test presence plus explicit validation/error-handling signals.
- Evidence: `.agent/skills/tests/SKILL.md`
- Evidence: `.claude/skills/tests/SKILL.md`
- Evidence: `archive/Calculator/tests/test_calculator.py`
- Evidence: `archive/Calculator/tests/test_exception_handling.py`
- Evidence: `archive/Calculator/tests/test_limiter.py`
- Evidence: `archive/Calculator/calculator.py`
- Evidence: `archive/Calculator/tests/test_exception_handling.py`
- Evidence: `archive/Calculator/tests/test_ti89_calculator.py`
- Evidence: `archive/Calculator/webapp.py`
- Evidence: `scripts/analyze_completist_data.py`

### F. Function, Module Size, and SRP: C (70/100)
Evaluates function size, script/module size, and single responsibility using static size signals.
- Evidence: `scripts/mypy_autofix_agent.py (709 lines)`
- Evidence: `src/asteroid_jumper/renderer.py (554 lines)`
- Evidence: `scripts/generate_assessment_summary.py (coarse avg 80 lines/definition)`

### G. Testing and TDD Posture: B (82/100)
TDD history cannot be confirmed statically; grade reflects committed automated test posture.
- Evidence: `.agent/skills/tests/SKILL.md`
- Evidence: `.claude/skills/tests/SKILL.md`
- Evidence: `archive/Calculator/tests/test_calculator.py`
- Evidence: `archive/Calculator/tests/test_exception_handling.py`
- Evidence: `archive/Calculator/tests/test_limiter.py`
- Evidence: `archive/Calculator/tests/test_rate_limit_enforcement.py`
- Evidence: `archive/Calculator/tests/test_security.py`
- Evidence: `archive/Calculator/tests/test_ti89_calculator.py`
- Evidence: `archive/Calculator/tests/test_webapp.py`
- Evidence: `archive/tools/tests/test_tools.py`
- Evidence: `docs/assessments/Assessment_C_Test_Coverage.md`
- Evidence: `pytest_errors.txt`

### H. CI/CD and Automation: C (78/100)
Checks for tracked CI/CD workflow files.
- Evidence: `.github/workflows/Comment-to-Issue-Converter.yml`
- Evidence: `.github/workflows/Jules-Archivist.yml`
- Evidence: `.github/workflows/Jules-Assessment-AutoFix.yml`
- Evidence: `.github/workflows/Jules-Assessment-Generator.yml`
- Evidence: `.github/workflows/Jules-Auto-Assign-Issues.yml`
- Evidence: `.github/workflows/Jules-Auto-Rebase.yml`
- Evidence: `.github/workflows/Jules-Auto-Refactor.yml`
- Evidence: `.github/workflows/Jules-Auto-Repair.yml`
- Evidence: `.github/workflows/Jules-Cleaner.yml`
- Evidence: `.github/workflows/Jules-Code-Quality-Fixer.yml`

### I. Security and Secret Hygiene: B (82/100)
Secret scan is regex-based; findings require manual confirmation.
- Evidence: No direct tracked-file evidence found for this category.

### J. Documentation and Onboarding: B (82/100)
Checks docs, README, onboarding, and release documents.
- Evidence: `.agent/skills/issues-10-sequential/SKILL.md`
- Evidence: `.agent/skills/issues-5-combined/SKILL.md`
- Evidence: `.agent/skills/lint/SKILL.md`
- Evidence: `.agent/skills/tests/SKILL.md`
- Evidence: `.agent/skills/update-issues/SKILL.md`
- Evidence: `.agent/workflows/issues-10-sequential.md`
- Evidence: `.agent/workflows/issues-5-combined.md`
- Evidence: `.agent/workflows/lint.md`
- Evidence: `.agent/workflows/tests.md`
- Evidence: `.agent/workflows/update-issues.md`
- Evidence: `.claude/skills/issues-10-sequential/SKILL.md`
- Evidence: `.claude/skills/issues-5-combined/SKILL.md`

### K. Maintainability, DRY, and Duplication: B (80/100)
DRY is assessed through duplicate filename clusters and TODO/FIXME density as static heuristics.
- Evidence: `scripts/analyze_completist_data.py`
- Evidence: `scripts/pragmatic_programmer_review.py`
- Evidence: `scripts/setup_hooks.py`

### L. API Surface and Law of Demeter: F (58/100)
Law of Demeter is approximated with deep member-chain hints; confirmed violations require semantic review.
- Evidence: `archive/Calculator/tests/test_limiter.py`
- Evidence: `archive/Calculator/tests/test_rate_limit_enforcement.py`
- Evidence: `archive/Calculator/tests/test_security.py`
- Evidence: `archive/Calculator/tests/test_webapp.py`
- Evidence: `src/Project_GROOT/sim/golf_swing_env.py`
- Evidence: `src/Project_GROOT/tools/video_ingest.py`
- Evidence: `src/Project_GROOT/train/imitation_train.py`
- Evidence: `src/Project_GROOT/train/rl_finetune.py`
- Evidence: `src/asteroid_jumper/controller.py`
- Evidence: `src/asteroid_jumper/controls_panel.py`

### M. Observability and Operability: C (74/100)
Checks for logging, metrics, monitoring, and operational artifacts.
- Evidence: `.github/workflows/agent-metrics-dashboard.yml`
- Evidence: `docs/assessments/Assessment_L_Logging.md`
- Evidence: `src/asteroid_jumper/metrics_panel.py`
- Evidence: `tests/test_asteroid_jumper_metrics_panel.py`

### N. Governance, Licensing, and Release Hygiene: C (74/100)
Checks ownership, release, contribution, security, and license metadata.
- Evidence: `.github/CODEOWNERS`
- Evidence: `LICENSE`
- Evidence: `archive/Calculator/tests/test_security.py`
- Evidence: `docs/assessments/Assessment_F_Security.md`
- Evidence: `src/Project_GROOT/LICENSE`

## Explicit Engineering Practice Review
- TDD: Automated tests are present, but red-green-refactor history is not confirmable from static files.
- DRY: No repeated filename clusters met the static threshold.
- Design by Contract: Validation/contract signals were found in tracked code.
- Law of Demeter: Deep member-chain hints were found and should be semantically reviewed.
- Function size and SRP: Large modules or coarse long-definition signals were found.

## Key Risks
- Large modules/scripts reduce maintainability and SRP clarity.
- Deep member-chain usage may indicate Law of Demeter pressure points.

## Prioritized Remediation Recommendations
1. Split the largest modules by responsibility and add characterization tests before refactoring.
2. Review deep member chains and introduce boundary methods where object graph traversal leaks across modules.

## Actionable Issue Candidates
### Split oversized modules by responsibility
- Severity: medium
- Problem: Oversized files found: scripts/mypy_autofix_agent.py (709 lines); src/asteroid_jumper/renderer.py (554 lines)
- Evidence: Category F lists files over 500 lines or coarse long-definition signals.
- Impact: Large modules obscure ownership, complicate review, and weaken SRP.
- Proposed fix: Add characterization tests, then split cohesive responsibilities into smaller modules.
- Acceptance criteria: Largest files are reduced or justified; extracted modules have focused tests.
- Expectations: SRP, function size, module size, maintainability

### Review deep object traversal hotspots
- Severity: medium
- Problem: Deep member-chain hints found in: archive/Calculator/tests/test_limiter.py; archive/Calculator/tests/test_rate_limit_enforcement.py; archive/Calculator/tests/test_security.py; archive/Calculator/tests/test_webapp.py; src/Project_GROOT/sim/golf_swing_env.py; src/Project_GROOT/tools/video_ingest.py; src/Project_GROOT/train/imitation_train.py; src/Project_GROOT/train/rl_finetune.py
- Evidence: Category L found repeated chains with three or more member hops.
- Impact: Law of Demeter pressure can make APIs brittle and increase coupling.
- Proposed fix: Review hotspots and introduce boundary methods or DTOs where callers traverse object graphs.
- Acceptance criteria: Hotspots are documented, simplified, or justified; tests cover any API boundary changes.
- Expectations: Law of Demeter, SRP, maintainability

