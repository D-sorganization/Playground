import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

CATEGORIES = {
    "A": ("Code Structure", "Code"),
    "B": ("Documentation", "Docs"),
    "C": ("Test Coverage", "Testing"),
    "D": ("Error Handling", "Code"),
    "E": ("Performance", "Perf"),
    "F": ("Security", "Security"),
    "G": ("Dependencies", "Ops"),
    "H": ("CI/CD", "Ops"),
    "I": ("Code Style", "Code"),
    "J": ("API Design", "Design"),
    "K": ("Data Handling", "Design"),
    "L": ("Logging", "Ops"),
    "M": ("Configuration", "Ops"),
    "N": ("Scalability", "Perf"),
    "O": ("Maintainability", "Code"),
}

GROUPS = {
    "Code": 0.25,
    "Testing": 0.15,
    "Docs": 0.10,
    "Security": 0.15,
    "Perf": 0.15,
    "Ops": 0.10,
    "Design": 0.10,
}

scores = {}
findings = []

for file in Path("docs/assessments").glob("Assessment_*_CATEGORY.md"):
    if file.name.count("_") < 2 and "CICD" not in file.name:
        continue
    if "Results" in file.name:
        continue

    # Extract ID
    match = re.search(r"Assessment_([A-O])_", file.name)
    if not match:
        continue
    cat = match.group(1)

    content = file.read_text()
    score_match = re.search(r"Score:\s*([\d\.]+)/10", content)
    if score_match:
        scores[cat] = float(score_match.group(1))

    # extract some findings
    for line in content.splitlines():
        if "MAJOR:" in line or "CRITICAL:" in line or "MINOR:" in line:
            findings.append(f"{cat}: {line.strip()}")

grouped_scores = {group: [] for group in GROUPS}
for cat, score in scores.items():
    grouped_scores[CATEGORIES[cat][1]].append(score)

grouped_averages = {
    group: sum(vals) / len(vals) if vals else 0
    for group, vals in grouped_scores.items()
}

weighted_average = sum(
    grouped_averages[group] * weight for group, weight in GROUPS.items()
)

report = """# Comprehensive Assessment

## Grade Table

| Category | Name | Score | Group |
|---|---|---|---|
"""

for cat in sorted(scores.keys()):
    name, group = CATEGORIES[cat]
    score = scores[cat]
    report += f"| {cat} | {name} | {score}/10 | {group} |\n"

report += """

## Grouped Scores

"""

for group, weight in GROUPS.items():
    report += f"- **{group}** ({weight * 100}%): {grouped_averages[group]:.2f}/10\n"

report += f"""
## Weighted Average

**Final Score: {weighted_average:.2f}/10**

## Top 5 Recommendations

"""

top_findings = findings[:5] if len(findings) >= 5 else findings
if not top_findings:
    report += "- No major issues found.\n"
else:
    for f in top_findings:
        report += f"- {f}\n"

Path("docs/assessments/Comprehensive_Assessment.md").write_text(report)
logger.info("Generated docs/assessments/Comprehensive_Assessment.md")
