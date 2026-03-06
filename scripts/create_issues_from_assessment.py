#!/usr/bin/env python3
"""
Create GitHub issues from assessment findings.

This script reads the assessment summary JSON and creates GitHub issues
for categories with low scores and critical findings.
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def create_github_issue(
    title: str,
    body: str,
    labels: list[str],
    dry_run: bool = False,
) -> bool:
    """
    Create a GitHub issue.

    Args:
        title: Issue title
        body: Issue body
        labels: List of label names
        dry_run: If True, log instead of creating

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would create issue: {title}")
        logger.info(f"          Labels: {labels}")
        return True

    try:
        cmd = ["gh", "issue", "create", "--title", title, "--body", body]

        # Add labels (only if they exist in the repo)
        if labels:
            cmd.extend(["--label", ",".join(labels)])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            issue_url = result.stdout.strip()
            logger.info(f"✓ Created issue: {issue_url}")
            return True
        else:
            logger.error(f"✗ Failed to create issue '{title}': {result.stderr}")
            return False

    except FileNotFoundError:
        logger.error("✗ 'gh' CLI not found. Cannot create issues.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed to create issue '{title}': {e.stderr}")
        return False


def process_assessment_findings(
    summary_file: Path,
    dry_run: bool = False,
    output_file: Path | None = None,
) -> int:
    """
    Process assessment findings and create issues.

    Args:
        summary_file: Path to assessment_summary.json
        dry_run: If True, don't actually create issues
        output_file: Path to save list of issues to create

    Returns:
        Number of issues created/planned
    """
    if not summary_file.exists():
        logger.warning(f"Summary file not found: {summary_file}")
        return 0

    try:
        with open(summary_file) as f:
            summary = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {summary_file}: {e}")
        return 0

    issues_to_create = []

    # 1. Check for Category Scores < 5
    category_scores = summary.get("category_scores", {})
    for cat_id, data in category_scores.items():
        score = data.get("score", 0)
        name = data.get("name", "Unknown")

        if score < 5:
            issues_to_create.append(
                {
                    "title": f"Improve {name} (Category {cat_id})",
                    "body": f"""## Low Assessment Score

**Category**: {cat_id} - {name}
**Score**: {score}/10
**Threshold**: 5/10

The assessment for this category falls below the acceptable threshold.

### Recommendations

- Review the detailed assessment report: `docs/assessments/Assessment_{cat_id}_*.md`
- Address identified findings.
- Re-run assessment to verify improvements.
""",
                    "labels": ["jules:assessment", "needs-attention"],
                }
            )

    # 2. Check for Critical Issues (legacy check)
    critical_issues = summary.get("critical_issues", [])
    for issue in critical_issues:
        title = f"[Assessment] {issue.get('description', 'Critical Issue')}"
        issues_to_create.append(
            {
                "title": title,
                "body": f"""## Critical Assessment Finding

**Severity**: {issue.get("severity")}
**Source**: {issue.get("source")}

{issue.get("description")}

Please address this issue immediately.
""",
                "labels": ["jules:assessment", "critical"],
            }
        )

    # Create Issues or Log
    count = 0
    file_content = "# Issues to Create\n\n"

    for issue in issues_to_create:
        success = create_github_issue(
            issue["title"], issue["body"], issue["labels"], dry_run=dry_run
        )
        if success:
            count += 1
            file_content += (
                f"## {issue['title']}\n\n"
                f"Labels: {', '.join(issue['labels'])}\n\n"
                f"{issue['body']}\n\n---\n\n"
            )

    if output_file:
        with open(output_file, "w") as f:
            f.write(file_content)
        logger.info(f"✓ Issues list saved to {output_file}")

    return count


def main() -> None:
    """Create GitHub issues from assessment findings."""
    parser = argparse.ArgumentParser(
        description="Create GitHub issues from assessment findings"
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to assessment_summary.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would happen without creating issues",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Output file to save issue list",
    )

    args = parser.parse_args()

    logger.info(f"Processing assessment findings from: {args.input}")

    issues_created = process_assessment_findings(
        args.input,
        dry_run=args.dry_run,
        output_file=args.output_file,
    )

    logger.info(f"✓ Processed {issues_created} issues")
    sys.exit(0)


if __name__ == "__main__":
    main()
