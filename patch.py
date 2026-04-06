with open("SPEC.md", "r") as f:
    text = f.read()

target = "| 2026-04-06 | 1.0.6 | Declared `PyYAML`"
replacement = "| 2026-04-06 | 1.0.7 | Updated `run_assessment.py` and `make_comprehensive.py` scripts to auto-fix logging issues, output correct file structures, and ignore print false positives. |\n" + target

text = text.replace(target, replacement)
text = text.replace("| **Spec Version** | 1.0.6 |", "| **Spec Version** | 1.0.7 |")

with open("SPEC.md", "w") as f:
    f.write(text)
