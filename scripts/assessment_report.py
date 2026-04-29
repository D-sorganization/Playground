"""Assessment Report Generators."""

import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Assessment definitions matched to prompt


def _assessment_header(assessment_id: str, assessment: dict, score: int) -> str:
    """Return the YAML-front-matter and score header lines for the report."""
    name = assessment["name"]
    description = assessment["description"]
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"# Assessment {assessment_id}: {name}\n\n"
        f"**Date**: {date_str}\n"
        f"**Assessment**: {assessment_id} - {name}\n"
        f"**Description**: {description}\n"
        "**Generated**: Automated via Jules Assessment Auto-Fix workflow\n\n"
        f"## Score: {score}/10\n"
    )


def _assessment_footer() -> str:
    """Return the Recommendations and Automation Notes sections."""
    return (
        "\n## Recommendations\n\n"
        "- Review findings above\n"
        "- Address any x items\n"
        "- Re-run assessment after fixes\n\n"
        "## Automation Notes\n\n"
        "This assessment was generated automatically. For detailed analysis:\n"
        "1. Run specific tools (ruff, black, pytest, etc.)\n"
        "2. Review code manually for context-specific issues\n"
        "3. Create GitHub issues for actionable items\n"
    )


def _build_assessment_markdown(
    assessment_id: str, assessment: dict, score: int, findings: list[str]
) -> str:
    """Return the complete markdown report string for an assessment."""
    findings_block = "\n## Findings\n\n" + chr(10).join(findings)
    return (
        _assessment_header(assessment_id, assessment, score)
        + findings_block
        + _assessment_footer()
    )


def _write_assessment_report(
    assessment_id: str,
    assessment: dict,
    score: int,
    findings: list[str],
    output_path: Path,
) -> None:
    """Build markdown report and write to output_path."""
    report_content = _build_assessment_markdown(
        assessment_id, assessment, score, findings
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as output_file:
        output_file.write(report_content)
