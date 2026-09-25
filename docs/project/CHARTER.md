# Project Charter

> Drafted 2026-09-25 by the fleet charter sweep (Gemini) from README, git history, and open issues/PRs.
> The project-steward role keeps this current; owners should correct feature statuses.

## End Goal

Playground is the fleet-wide monorepo for hosting independent, orthogonal experimental projects and simulation prototypes—primarily the Asteroid Jumper arcade navigation game, the notes-based Workout Tracker PWA, and the Project GROOT golf swing imitation-learning pipeline—while providing standardized CI/CD infrastructure, testing frameworks, and quality gates. "Done" looks like a suite of well-tested, isolated experimental sandboxes that comply with fleet quality standards (Design by Contract, Test-Driven Development, strict typing, and security scanning) with zero cross-project domain coupling, where mature experiments can cleanly graduate into dedicated repositories and retired experiments remain safely isolated without destabilizing active projects.

## Non-Goals

- Hosting mission-critical production services or applications requiring production SLAs.
- Providing shared domain libraries or reusable domain business logic to external fleet repositories.
- Coupling independent experiments through shared domain dependencies or unified data models.
- Maintaining legacy or unmaintained prototypes within the active source and test tree.

## Features

| ID | Feature | Status | Tracking | Notes |
| --- | --- | --- | --- | --- |
| F1 | Asteroid Jumper Physics Simulation | shipped | #255 | Real-time asteroid navigation and orbital mechanics engine |
| F2 | Asteroid Jumper GUI and Controls | shipped | #421 | PyQt6 user interface with wheel-event guards and metrics panels |
| F3 | Workout Tracker Free-Text Parser | shipped | #331 | Natural language workout notes parsing for sets reps and loads |
| F4 | Workout Tracker SQLite Storage | shipped | #354 | Repository layer with soft deletes and foreign key migrations |
| F5 | Workout Tracker Fuzzy Autocomplete | shipped | #300 | Trigram and Damerau-Levenshtein exercise name search |
| F6 | Workout Tracker Analytics and 1RM | shipped | #298 | Epley and Brzycki 1RM calculators volume tracking and PR records |
| F7 | Workout Tracker Web App and PWA | shipped | #402 | Flask web UI mobile-first PWA shell and health diagnostics |
| F8 | Workout Tracker Templates and Planning | shipped | #297 | Session templates repeat set ordering and weekly scheduling |
| F9 | Workout Tracker Data Management | shipped | #299 | Export and import tools with trash and bulk editing features |
| F10 | Workout Tracker Third-Party Sync | parked | #303 | Deferred third-party service sync and external integrations |
| F11 | Project GROOT MuJoCo Simulation | shipped | #252 | Golf swing physics simulation environment with DbC contracts |
| F12 | Project GROOT Video and Pose Pipeline | shipped | #275 | Video ingestion pose estimation and sim retargeting tools |
| F13 | Project GROOT Training and Evaluation | shipped | #274 | Imitation learning RL fine-tuning and policy rollout eval |
| F14 | Mypy Autofix Agent Tooling | shipped | #247 | Automated Python static type analysis and AST-based patching |
| F15 | Assessment and Completist Engine | shipped | #470 | Automated repository health assessment and completist reporting |
| F16 | Fleet CI/CD and Security Gates | shipped | #467 | Standardized pipelines with CodeQL Semgrep and pip-audit |

## Links

- Status (generated): [`STATUS.md`](STATUS.md)
- Steward playbook: Repository_Management `docs/fleet-project-steward.md`
