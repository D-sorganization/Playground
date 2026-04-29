#!/usr/bin/env python3
"""
Run a specific assessment (A-O) on the repository.

This script executes an individual assessment and generates a detailed report
based on actual code analysis.
"""

import argparse
import logging
import sys
from pathlib import Path

from assessment_collectors import _collect_assessment_metrics
from assessment_report import _write_assessment_report
from assessment_utils import find_python_files

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Assessment definitions matched to prompt
ASSESSMENTS = {
    "A": {"name": "Code Structure", "description": "Project organization and layout"},
    "B": {"name": "Documentation", "description": "Documentation quality and presence"},
    "C": {"name": "Test Coverage", "description": "Test quantity and coverage"},
    "D": {
        "name": "Error Handling",
        "description": "Exception management and robustness",
    },
    "E": {"name": "Performance", "description": "Efficiency and optimization"},
    "F": {"name": "Security", "description": "Security practices and vulnerabilities"},
    "G": {"name": "Dependencies", "description": "Dependency management"},
    "H": {"name": "CI/CD", "description": "Continuous Integration/Deployment"},
    "I": {"name": "Code Style", "description": "Linting and formatting compliance"},
    "J": {"name": "API Design", "description": "Interface clarity and consistency"},
    "K": {"name": "Data Handling", "description": "Data processing and storage"},
    "L": {"name": "Logging", "description": "Logging implementation"},
    "M": {"name": "Configuration", "description": "Configuration management"},
    "N": {"name": "Scalability", "description": "Ability to scale"},
    "O": {"name": "Maintainability", "description": "Ease of maintenance"},
}


def run_assessment(assessment_id: str, output_path: Path) -> int:
    """
    Run a specific assessment and generate report.

    Args:
        assessment_id: Assessment ID (A-O)
        output_path: Path to save the assessment report

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    assessment = ASSESSMENTS.get(assessment_id)
    if not assessment:
        logger.error("Unknown assessment: %s", assessment_id)
        return 1

    logger.info("Running Assessment %s: %s...", assessment_id, assessment["name"])

    python_files = find_python_files()
    findings, score = _collect_assessment_metrics(assessment_id, python_files)
    score = max(0, min(10, round(score, 1)))

    _write_assessment_report(assessment_id, assessment, score, findings, output_path)

    logger.info("+ Assessment %s report saved to %s", assessment_id, output_path)
    logger.info("  Score: %s/10", score)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repository assessment")
    parser.add_argument(
        "--assessment",
        required=True,
        choices=list("ABCDEFGHIJKLMNO"),
        help="Assessment ID (A-O)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output file path for assessment report",
    )

    args = parser.parse_args()

    exit_code = run_assessment(args.assessment, args.output)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
